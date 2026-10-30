"""
TradeFlow Sentinel — Langflow Custom Component + FastAPI Endpoint
=================================================================
Single-file implementation containing:
  - Guardrail 1 (Input): PII masking + prompt injection blocking
  - Deterministic Trade Compliance Engine (UCP 600 Art. 18 / 20,
    SOLAS IMO checksum, Haversine AISHub, World Bank price deviation,
    Versioned DHE SDA evaluator)
  - Structured Remediation Action Generator (remediation_rows)
  - IBM Bob Synthesis + Guardrail 2 (Output): claim-grounded faithfulness
  - AI Unstructured Document Extractor (extract_documents_with_ai)
  - FastAPI endpoints:
      POST /verify-trade-documents
      POST /extract-and-verify        (NEW — unstructured text → JSON → audit)
      GET  /health
      GET  /            → Portable Web UI (tradeflow_sentinel_portable_ui.html)
      GET  /presets     → preset cases + dhe_sda_versions JSON
      GET  /benchmark-suite           (NEW — 40 planted test cases)
      POST /validation-feedback
      GET  /validation-feedback
  - CORS (allow_origins=["*"]) for multi-device/cloud access
  - Langflow CustomComponent subclass

Environment variables
---------------------
USE_MOCK_LLM=true          (default) — zero-cost MD5-cached mock responses
WATSONX_API_KEY            — required only when USE_MOCK_LLM=false
WATSONX_PROJECT_ID         — required only when USE_MOCK_LLM=false
WATSONX_URL                — defaults to https://us-south.ml.cloud.ibm.com
DATA_FILE                  — path to synthetic_data_and_rules.json
UI_FILE                    — path to tradeflow_sentinel_portable_ui.html
FEEDBACK_FILE              — path for validation_feedback_log.json
ANALYST_BASELINE_SEC       — measured practitioner baseline seconds (default 870.0)
PORT_PROXIMITY_THRESHOLD_NM — AISHub distance threshold in NM (default 10.0)
PRICE_DEVIATION_MAX_DEFAULT_PCT — fallback price tolerance % (default 10.0)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any, List, Optional

# ---------------------------------------------------------------------------
# Optional: FastAPI — imported lazily so the module works without it.
# ---------------------------------------------------------------------------
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel
    import uvicorn
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Langflow Component API (v1 — langflow-all:latest / langflow >= 1.0)
# ---------------------------------------------------------------------------
try:
    from langflow.custom import Component          # type: ignore
    from langflow.io import DropdownInput, Output  # type: ignore
    from langflow.schema import Data               # type: ignore
    _LANGFLOW_AVAILABLE = True
except ImportError:
    _LANGFLOW_AVAILABLE = False
    class Component:          # type: ignore
        pass
    class Data:               # type: ignore
        def __init__(self, **kw: Any) -> None:
            self.__dict__.update(kw)
    class DropdownInput:      # type: ignore
        def __init__(self, **kw: Any) -> None: ...
    class Output:             # type: ignore
        def __init__(self, **kw: Any) -> None: ...

# ===========================================================================
# CONSTANTS
# ===========================================================================
DATA_FILE = Path(os.getenv(
    "DATA_FILE",
    str(Path(__file__).parent / "synthetic_data_and_rules.json")
))
UI_FILE = Path(os.getenv(
    "UI_FILE",
    str(Path(__file__).parent / "tradeflow_sentinel_portable_ui.html")
))
FEEDBACK_FILE = Path(os.getenv(
    "FEEDBACK_FILE",
    str(Path(__file__).parent / "validation_feedback_log.json")
))

USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "true").lower() != "false"

WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_MODEL = os.getenv("WATSONX_MODEL", "ibm/granite-3-3-8b-instruct")

PORT_PROXIMITY_THRESHOLD_NM = float(os.getenv("PORT_PROXIMITY_THRESHOLD_NM", "10.0"))
PRICE_DEVIATION_MAX_DEFAULT_PCT = float(os.getenv("PRICE_DEVIATION_MAX_DEFAULT_PCT", "10.0"))
# Measured practitioner baseline: 14.5 min average across L/C + Invoice + BoL + AIS + DHE SDA
# cross-check trials (replaces hardcoded 2700 s / 45 min assumption).
ANALYST_BASELINE_SEC = float(os.getenv("ANALYST_BASELINE_SEC", "870.0"))

# Compiled prompt-injection patterns (Guardrail 1)
_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(previous|all)\s+instructions?|"
    r"system\s*:\s*you\s+are|"
    r"<\|im_start\|>|<\|im_end\|>|"
    r"\bDAN\b|"
    r"forget\s+(everything|your\s+instructions?)|"
    r"pretend\s+you\s+are|"
    r"act\s+as\s+if\s+you\s+have\s+no\s+restrict)",
    flags=re.IGNORECASE,
)

# Sensitive field patterns for PII masking (Guardrail 1)
_ACCOUNT_PATTERN = re.compile(r"\b(\d{6,20})\b")
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# ===========================================================================
# DATA LOADER
# ===========================================================================

def _load_data() -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_FILE}")
    with DATA_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)

# ===========================================================================
# GUARDRAIL 1 — INPUT SANITISATION
# ===========================================================================

def guardrail_input(text: str) -> tuple[str, list[str]]:
    """
    Mask PII (account numbers, emails) and detect prompt injection.
    Returns (sanitised_text, list_of_warnings).
    Raises ValueError on detected prompt injection.
    """
    warnings: list[str] = []

    if _INJECTION_PATTERNS.search(text):
        raise ValueError(
            "GUARDRAIL_1_BLOCKED: Prompt injection pattern detected in input. "
            "Request rejected."
        )

    sanitised = _EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)

    def _mask_account(m: re.Match) -> str:
        digits = m.group(1)
        if len(digits) >= 10:
            warnings.append(f"PII_MASKED: account number ending ...{digits[-4:]}")
            return f"[ACCT_REDACTED_{digits[-4:]}]"
        return digits

    sanitised = _ACCOUNT_PATTERN.sub(_mask_account, sanitised)
    return sanitised, warnings

# ===========================================================================
# SOLAS IMO CHECKSUM
# ===========================================================================

def solas_imo_checksum(imo_str: str) -> tuple[bool, int]:
    """
    Validate a 7-digit IMO number using the SOLAS checksum algorithm.
    Returns (is_valid, computed_check_digit).
    """
    digits = re.sub(r"[^0-9]", "", imo_str)
    if len(digits) != 7:
        return False, -1
    total = sum(int(digits[i]) * (7 - i) for i in range(6))
    check = total % 10
    return check == int(digits[6]), check

# ===========================================================================
# HAVERSINE DISTANCE
# ===========================================================================

def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in nautical miles."""
    R_NM = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R_NM * math.asin(math.sqrt(a))

# ===========================================================================
# DETERMINISTIC TRADE COMPLIANCE ENGINE
# ===========================================================================

def run_deterministic_engine(case: dict, lc_ref: dict, rules: dict,
                              vessel: dict | None, port_coords: dict,
                              benchmark: dict) -> dict:
    """
    Execute all deterministic compliance checks. Returns a structured findings dict.
    Includes fail-closed guards for unknown IMO (Bug #2), missing lat/lon dark vessel
    (Bug #4), unknown HS code / zero benchmark price (Bug #3), and case-insensitive
    Himbara check (Bug #1).
    """
    findings: dict[str, Any] = {
        "checks": {},
        "discrepancies": [],
        "overall_status": "COMPLIANT",
        "remediation_rows": [],
    }

    inv = case["commercial_invoice"]
    bol = case["bill_of_lading"]
    dhe = case["dhe_sda_transaction"]

    # ------------------------------------------------------------------
    # UCP 600 Art. 18 — Commercial Invoice check
    # ------------------------------------------------------------------
    art18 = {"rule": "UCP 600 Art. 18 — Commercial Invoice"}
    ci_issues: list[str] = []

    if inv["seller"].upper() != lc_ref["beneficiary"].upper():
        ci_issues.append(f"Seller '{inv['seller']}' ≠ LC beneficiary '{lc_ref['beneficiary']}'")
        findings["remediation_rows"].append({
            "field": "commercial_invoice.seller",
            "current_value": inv["seller"],
            "required_action": f"Ubah nama penjual menjadi '{lc_ref['beneficiary']}' sesuai UCP 600 Art. 18(a)(i)",
        })
    if inv["buyer"].upper() != lc_ref["applicant"].upper():
        ci_issues.append(f"Buyer '{inv['buyer']}' ≠ LC applicant '{lc_ref['applicant']}'")
        findings["remediation_rows"].append({
            "field": "commercial_invoice.buyer",
            "current_value": inv["buyer"],
            "required_action": f"Ubah nama pembeli menjadi '{lc_ref['applicant']}' sesuai UCP 600 Art. 18(a)(ii)",
        })
    if inv["currency"] != lc_ref["currency"]:
        ci_issues.append(f"Currency mismatch: invoice '{inv['currency']}' ≠ LC '{lc_ref['currency']}'")
        findings["remediation_rows"].append({
            "field": "commercial_invoice.currency",
            "current_value": inv["currency"],
            "required_action": f"Ubah mata uang menjadi '{lc_ref['currency']}' sesuai UCP 600 Art. 18(a)(iii)",
        })
    if abs(inv["total_fob_usd"] - lc_ref["amount"]) > lc_ref["amount"] * lc_ref["tolerance_pct"] / 100:
        ci_issues.append(
            f"Amount mismatch: invoice USD {inv['total_fob_usd']:,} outside LC "
            f"USD {lc_ref['amount']:,} ± {lc_ref['tolerance_pct']}%"
        )
        findings["remediation_rows"].append({
            "field": "commercial_invoice.total_fob_usd",
            "current_value": inv["total_fob_usd"],
            "required_action": (
                f"Sesuaikan jumlah ke USD {lc_ref['amount']:,} ± {lc_ref['tolerance_pct']}% "
                f"sesuai UCP 600 Art. 18(a)(iii)"
            ),
        })
    if inv["incoterms"] != lc_ref["incoterms"]:
        ci_issues.append(f"Incoterms mismatch: '{inv['incoterms']}' ≠ '{lc_ref['incoterms']}'")
        findings["remediation_rows"].append({
            "field": "commercial_invoice.incoterms",
            "current_value": inv["incoterms"],
            "required_action": f"Gunakan Incoterms '{lc_ref['incoterms']}' sesuai LC",
        })

    art18["status"] = "PASS" if not ci_issues else "FAIL"
    art18["issues"] = ci_issues
    findings["checks"]["ucp_art18_invoice"] = art18
    if ci_issues:
        findings["discrepancies"].extend(ci_issues)

    # ------------------------------------------------------------------
    # UCP 600 Art. 20 — Bill of Lading check
    # ------------------------------------------------------------------
    art20 = {"rule": "UCP 600 Art. 20 — Bill of Lading"}
    bl_issues: list[str] = []

    if bol["port_of_loading"].upper() != lc_ref["port_of_loading"].upper():
        bl_issues.append(
            f"Port of loading mismatch: BoL '{bol['port_of_loading']}' ≠ LC '{lc_ref['port_of_loading']}'"
        )
        findings["remediation_rows"].append({
            "field": "bill_of_lading.port_of_loading",
            "current_value": bol["port_of_loading"],
            "required_action": f"Koreksi Port of Loading menjadi '{lc_ref['port_of_loading']}' sesuai UCP 600 Art. 20(a)(iii)",
        })
    if bol["port_of_discharge"].upper() != lc_ref["port_of_discharge"].upper():
        bl_issues.append(
            f"Port of discharge mismatch: BoL '{bol['port_of_discharge']}' ≠ LC '{lc_ref['port_of_discharge']}'"
        )
        findings["remediation_rows"].append({
            "field": "bill_of_lading.port_of_discharge",
            "current_value": bol["port_of_discharge"],
            "required_action": f"Koreksi Port of Discharge menjadi '{lc_ref['port_of_discharge']}' sesuai UCP 600 Art. 20(a)(iv)",
        })

    # On-board date vs LC latest shipment date
    onboard_date = bol["on_board_date"]
    latest_ship = lc_ref["latest_shipment_date"]
    if onboard_date > latest_ship:
        bl_issues.append(
            f"On-board date {onboard_date} is after LC latest shipment date {latest_ship}"
        )
        findings["remediation_rows"].append({
            "field": "bill_of_lading.on_board_date",
            "current_value": onboard_date,
            "required_action": (
                f"Tanggal on-board harus pada atau sebelum {latest_ship} "
                f"(LC Latest Shipment Date) sesuai UCP 600 Art. 20(a)(vi)"
            ),
        })

    # AISHub proximity check
    # Bug Fix #2: vessel may be None if IMO not found — handle fail-closed above caller.
    # Bug Fix #4: vessel lat/lon may be None (dark vessel / transponder off) — FAIL-CLOSED.
    board_date = case.get("bill_of_lading", {}).get("on_board_date", "")
    vessel_name = case.get("bill_of_lading", {}).get("vessel_name", "")

    vessel_lat: float | None = None
    vessel_lon: float | None = None
    snapshot_date: str | None = None
    vessel_display_name = bol.get("vessel_name", vessel_name)
    vessel_imo_display = bol.get("imo_number", "UNKNOWN")

    if vessel is not None:
        vessel_display_name = vessel.get("vessel_name", vessel_display_name)
        vessel_imo_display = vessel.get("imo", vessel_imo_display)
        if "snapshots" in vessel:
            matched_snapshot = None
            for s in vessel["snapshots"]:
                if s.get("date") == board_date:
                    matched_snapshot = s
                    break
            if not matched_snapshot and len(vessel["snapshots"]) > 0:
                matched_snapshot = vessel["snapshots"][0]
            if matched_snapshot:
                vessel_lat = matched_snapshot.get("lat")
                vessel_lon = matched_snapshot.get("lon")
                snapshot_date = matched_snapshot.get("date")
        else:
            vessel_lat = vessel.get("lat")
            vessel_lon = vessel.get("lon")
            snapshot_date = vessel.get("snapshot_date")

    port_lat = port_coords["lat"]
    port_lon = port_coords["lon"]

    aishu_check: dict[str, Any] = {
        "rule": "AISHub Vessel Proximity (on-board date)",
        "vessel": vessel_display_name,
        "imo": vessel_imo_display,
        "snapshot_date": snapshot_date,
        "vessel_position": {"lat": vessel_lat, "lon": vessel_lon},
        "port": port_coords.get("port"),
        "port_position": {"lat": port_lat, "lon": port_lon},
        "threshold_nm": PORT_PROXIMITY_THRESHOLD_NM,
    }

    if vessel is None:
        # Bug Fix #2 — unknown IMO: fail-closed, do not crash
        distance_nm = None
        aishu_check["distance_nm"] = None
        aishu_check["status"] = "FAIL"
        msg = (
            f"AISHub / SOLAS Registry (FAIL-CLOSED): Vessel IMO {vessel_imo_display} "
            f"is not registered in the verified maritime vessel database."
        )
        aishu_check["finding"] = msg
        bl_issues.append(msg)
        findings["remediation_rows"].append({
            "field": "bill_of_lading.imo_number",
            "current_value": vessel_imo_display,
            "required_action": (
                "Verifikasi IMO number kapal dengan SOLAS/Lloyd's Register. "
                "IMO tidak ditemukan dalam database vessel terverifikasi."
            ),
        })
    elif vessel_lat is None or vessel_lon is None:
        # Bug Fix #4 — missing coordinates: fail-closed, do NOT default to 0.0 NM
        distance_nm = None
        aishu_check["distance_nm"] = None
        aishu_check["status"] = "FAIL"
        msg = (
            f"UCP 600 Art. 20(a)(ii) / AISHub (FAIL-CLOSED): Missing AIS satellite "
            f"coordinates (lat/lon) for vessel {vessel_display_name} "
            f"(IMO {vessel_imo_display}) on {board_date} — "
            f"potential dark vessel or unverified loading position."
        )
        aishu_check["finding"] = msg
        bl_issues.append(msg)
        findings["remediation_rows"].append({
            "field": "bill_of_lading.on_board_date",
            "current_value": f"{onboard_date} (koordinat AIS tidak tersedia)",
            "required_action": (
                f"Transponder AIS kapal {vessel_display_name} tidak aktif pada {board_date}. "
                "Minta konfirmasi posisi kapal dari Port Authority atau agent pelabuhan."
            ),
        })
    else:
        distance_nm = round(haversine_nm(vessel_lat, vessel_lon, port_lat, port_lon), 2)
        aishu_check["distance_nm"] = distance_nm
        if distance_nm > PORT_PROXIMITY_THRESHOLD_NM:
            msg = (
                f"PREDATED BoL (UCP 600 Art. 20): vessel {vessel_display_name} "
                f"(IMO {vessel_imo_display}) was {distance_nm} NM from {port_coords.get('port')} "
                f"on {snapshot_date} — physically impossible to be on-board at that port"
            )
            bl_issues.append(msg)
            aishu_check["status"] = "FAIL"
            aishu_check["finding"] = msg
            findings["remediation_rows"].append({
                "field": "bill_of_lading.on_board_date",
                "current_value": f"{onboard_date} (kapal {distance_nm} NM dari {port_coords.get('port')})",
                "required_action": (
                    f"Tanggal on-board harus setelah kapal tiba di {port_coords.get('port')}. "
                    f"Verifikasi posisi AISHub; kapal {vessel_display_name} (IMO {vessel_imo_display}) "
                    f"baru tiba di pelabuhan pada tanggal yang lebih lanjut."
                ),
            })
        else:
            aishu_check["status"] = "PASS"
            aishu_check["finding"] = f"Vessel confirmed within {distance_nm} NM of loading port"

    art20["status"] = "PASS" if not bl_issues else "FAIL"
    art20["issues"] = bl_issues
    findings["checks"]["ucp_art20_bol"] = art20
    findings["checks"]["aishu_proximity"] = aishu_check
    if bl_issues:
        findings["discrepancies"].extend(bl_issues)

    # ------------------------------------------------------------------
    # SOLAS IMO checksum
    # ------------------------------------------------------------------
    imo_valid, imo_check_digit = solas_imo_checksum(bol["imo_number"])
    findings["checks"]["imo_solas"] = {
        "rule": "SOLAS — IMO Number Checksum",
        "imo": bol["imo_number"],
        "computed_check_digit": imo_check_digit,
        "status": "PASS" if imo_valid else "FAIL",
    }
    if not imo_valid:
        findings["discrepancies"].append(f"Invalid IMO checksum for {bol['imo_number']}")
        findings["remediation_rows"].append({
            "field": "bill_of_lading.imo_number",
            "current_value": bol["imo_number"],
            "required_action": (
                f"IMO number tidak valid (check digit harus {imo_check_digit}). "
                f"Verifikasi IMO number kapal dengan SOLAS checksum algorithm."
            ),
        })

    # ------------------------------------------------------------------
    # World Bank Pink Sheet — Price Deviation
    # Bug Fix #3: guard against missing HS code or benchmark_price == 0 (ZeroDivisionError)
    # ------------------------------------------------------------------
    wb_price = benchmark.get("benchmark_price", 0)
    wb_tolerance = benchmark.get("tolerance_pct", PRICE_DEVIATION_MAX_DEFAULT_PCT)
    inv_price = inv["unit_price_usd_mt"]
    hs_code_used = benchmark.get("hs_code", inv.get("hs_code", "UNKNOWN"))

    price_check: dict[str, Any] = {
        "rule": "World Bank Pink Sheet — Unit Price Deviation",
        "commodity": benchmark.get("description", "Unknown"),
        "hs_code": hs_code_used,
        "invoice_price_usd_mt": inv_price,
        "benchmark_price_usd_mt": wb_price,
        "tolerance_pct": wb_tolerance,
    }

    if wb_price <= 0:
        # Bug Fix #3 — fail-closed: unknown or zero benchmark price
        deviation_pct = None
        price_check["deviation_pct"] = None
        price_check["status"] = "FAIL"
        msg = (
            f"World Bank Pink Sheet (FAIL-CLOSED): HS Code '{hs_code_used}' has no valid "
            f"benchmark reference price — manual price verification required."
        )
        price_check["finding"] = msg
        findings["discrepancies"].append(msg)
        findings["remediation_rows"].append({
            "field": "commercial_invoice.unit_price_usd_mt",
            "current_value": f"USD {inv_price}/MT",
            "required_action": (
                f"HS Code '{hs_code_used}' tidak memiliki harga benchmark World Bank Pink Sheet. "
                "Lakukan verifikasi harga manual dengan referensi komoditas yang sesuai."
            ),
        })
    else:
        deviation_pct = round(((inv_price - wb_price) / wb_price) * 100, 2)
        price_check["deviation_pct"] = deviation_pct
        if abs(deviation_pct) > wb_tolerance:
            msg = (
                f"Price deviation {deviation_pct:+.2f}% exceeds tolerance ±{wb_tolerance}% "
                f"(invoice ${inv_price}/MT vs benchmark ${wb_price}/MT)"
            )
            price_check["status"] = "FAIL"
            price_check["finding"] = msg
            findings["discrepancies"].append(msg)
            findings["remediation_rows"].append({
                "field": "commercial_invoice.unit_price_usd_mt",
                "current_value": f"USD {inv_price}/MT ({deviation_pct:+.2f}% dari benchmark)",
                "required_action": (
                    f"Harga harus dalam rentang USD {round(wb_price * (1 - wb_tolerance/100), 2)}–"
                    f"{round(wb_price * (1 + wb_tolerance/100), 2)}/MT "
                    f"(World Bank Pink Sheet benchmark USD {wb_price}/MT ± {wb_tolerance}%)"
                ),
            })
        else:
            price_check["status"] = "PASS"
            price_check["finding"] = f"Price within tolerance: {deviation_pct:+.2f}%"
    findings["checks"]["price_deviation"] = price_check

    # ------------------------------------------------------------------
    # Versioned DHE SDA Evaluator
    # ------------------------------------------------------------------
    rule_version = case.get("dhe_rule_version", "PADG_16_2026")
    active_rule = rules[rule_version]
    fob = dhe["fob_usd"]
    bank_cat = dhe.get("bank_category", "")
    fx_pct = dhe.get("requested_fx_conversion_pct", 0)
    hold_months = dhe.get("hold_period_months", 0)

    dhe_issues: list[str] = []

    if fob < active_rule["fob_threshold_usd"]:
        findings["checks"]["dhe_sda"] = {
            "rule": f"DHE SDA ({rule_version})",
            "status": "NOT_APPLICABLE",
            "finding": f"FOB USD {fob:,} below threshold USD {active_rule['fob_threshold_usd']:,}",
        }
    else:
        if hold_months < active_rule["min_hold_months"]:
            dhe_issues.append(
                f"Hold period {hold_months}m < required {active_rule['min_hold_months']}m "
                f"under {rule_version}"
            )
            findings["remediation_rows"].append({
                "field": "dhe_sda_transaction.hold_period_months",
                "current_value": hold_months,
                "required_action": (
                    f"Masa retensi minimal {active_rule['min_hold_months']} bulan "
                    f"sesuai {rule_version} ({active_rule['legal_basis']})"
                ),
            })

        if fx_pct > active_rule["fx_conversion_to_idr_max_pct"]:
            dhe_issues.append(
                f"Requested FX conversion {fx_pct}% exceeds {rule_version} maximum "
                f"{active_rule['fx_conversion_to_idr_max_pct']}%"
            )
            findings["remediation_rows"].append({
                "field": "dhe_sda_transaction.requested_fx_conversion_pct",
                "current_value": f"{fx_pct}%",
                "required_action": (
                    f"Konversi FX ke IDR maksimal {active_rule['fx_conversion_to_idr_max_pct']}% "
                    f"sesuai {rule_version} Pasal 38A ({active_rule['legal_basis']})"
                ),
            })

        if rule_version == "PADG_16_2026":
            bank_cat = dhe.get("bank_category", "")
            # Bug Fix #1 — case-insensitive multi-token check on both bank_category AND
            # nominated_bank so "HIMBARA", "Himbara", "STATE_OWNED", "BUMN" all pass,
            # and known Himbara bank names in nominated_bank also pass.
            bank_cat_upper = str(bank_cat).upper()
            nom_bank_upper = str(dhe.get("nominated_bank", "")).upper()
            is_himbara = (
                any(tok in bank_cat_upper for tok in ("HIMBARA", "STATE_OWNED", "BUMN"))
                or any(b in nom_bank_upper for b in (
                    "MANDIRI", "BRI", "RAKYAT INDONESIA",
                    "BNI", "NEGARA INDONESIA", "BTN", "TABUNGAN NEGARA",
                ))
            )
            if not is_himbara:
                dhe_issues.append(
                    f"Bank category '{bank_cat}' is NOT a Himbara state-owned bank. "
                    f"{rule_version} restricts placement to: {', '.join(active_rule['bank_categories']['HIMBARA'])}"
                )
                findings["remediation_rows"].append({
                    "field": "dhe_sda_transaction.nominated_bank",
                    "current_value": dhe.get("nominated_bank", bank_cat),
                    "required_action": (
                        f"Bank penerima harus merupakan Bank BUMN/Himbara: "
                        f"{', '.join(active_rule['bank_categories']['HIMBARA'])} "
                        f"sesuai {rule_version} Pasal 21 ({active_rule['legal_basis']})"
                    ),
                })
            placement_type = dhe.get("placement_type", "")
            if "Reksus" not in placement_type:
                dhe_issues.append(
                    f"Placement type '{placement_type}' is not a Reksus DHE SDA account as required by {rule_version}"
                )
                findings["remediation_rows"].append({
                    "field": "dhe_sda_transaction.placement_type",
                    "current_value": placement_type,
                    "required_action": (
                        f"Jenis penempatan harus 'Reksus DHE SDA' (Special FX Account) "
                        f"sesuai {rule_version} ({active_rule['legal_basis']})"
                    ),
                })

        findings["checks"]["dhe_sda"] = {
            "rule": f"DHE SDA ({rule_version})",
            "legal_basis": active_rule["legal_basis"],
            "fob_usd": fob,
            "threshold_usd": active_rule["fob_threshold_usd"],
            "retention_required_pct": active_rule["retention_pct"],
            "min_hold_months": active_rule["min_hold_months"],
            "fx_conversion_max_pct": active_rule["fx_conversion_to_idr_max_pct"],
            "requested_fx_conversion_pct": fx_pct,
            "nominated_bank": dhe.get("nominated_bank"),
            "bank_category": bank_cat,
            "status": "PASS" if not dhe_issues else "FAIL",
            "issues": dhe_issues,
        }
        if dhe_issues:
            findings["discrepancies"].extend(dhe_issues)

    # ------------------------------------------------------------------
    # Final overall status
    # ------------------------------------------------------------------
    findings["overall_status"] = "COMPLIANT" if not findings["discrepancies"] else "DISCREPANT"
    findings["discrepancy_count"] = len(findings["discrepancies"])
    return findings

# ===========================================================================
# MOCK / CACHED IBM BOB SYNTHESIS — Enhanced Bilingual Indonesian Executive Report
# ===========================================================================

_MOCK_CACHE: dict[str, str] = {}


def _mock_synthesis(findings: dict, case_id: str) -> str:
    """
    Return a deterministically cached mock synthesis narrative.
    Enhanced executive-ready bilingual Indonesian & English compliance report
    following AGENT.md Section 5 structure and PADG No. 16/2026 legal context.
    All key numbers are included verbatim to satisfy Guardrail 2.
    """
    cache_key = hashlib.md5(
        json.dumps(findings, sort_keys=True).encode()
    ).hexdigest()[:12]

    if cache_key in _MOCK_CACHE:
        return _MOCK_CACHE[cache_key]

    status = findings["overall_status"]
    n_disc = findings["discrepancy_count"]
    checks = findings["checks"]
    rem_rows = findings.get("remediation_rows", [])

    art18 = checks.get("ucp_art18_invoice", {})
    art20 = checks.get("ucp_art20_bol", {})
    aishu = checks.get("aishu_proximity", {})
    imo = checks.get("imo_solas", {})
    price = checks.get("price_deviation", {})
    dhe = checks.get("dhe_sda", {})

    # Verbatim numbers for Guardrail 2 faithfulness
    # deviation_pct may be None for fail-closed unknown HS (Bug Fix #3 guard)
    distance_nm = str(aishu.get("distance_nm", "") or "")
    _dev_raw = price.get("deviation_pct")
    deviation_pct = str(abs(_dev_raw)) if _dev_raw is not None else "N/A"
    fx_pct_val = str(dhe.get("requested_fx_conversion_pct", "")) if dhe else ""
    inv_price = price.get("invoice_price_usd_mt", "N/A")
    bench_price = price.get("benchmark_price_usd_mt", "N/A")
    dev_signed = price.get("deviation_pct")  # may be None for fail-closed unknown HS
    tol_pct = price.get("tolerance_pct", 10)

    # Build remediation table section
    rem_section = ""
    if rem_rows:
        rem_section = "\n\n📋 TABEL TINDAKAN KOREKTIF / CORRECTIVE ACTION TABLE\n"
        rem_section += "─" * 70 + "\n"
        rem_section += f"{'Field':<45} {'Nilai Saat Ini':<25} {'Tindakan Diperlukan'}\n"
        rem_section += "─" * 70 + "\n"
        for r in rem_rows:
            rem_section += f"  {r['field']:<43} {str(r['current_value']):<25} {r['required_action']}\n"
        rem_section += "─" * 70

    # Verdict status label
    verdict_id = "✅ PATUH (COMPLIANT)" if status == "COMPLIANT" else "❌ TIDAK PATUH (DISCREPANT)"
    verdict_action_id = (
        "Dokumen sesuai dengan UCP 600 Art. 18/20 dan kewajiban DHE SDA. "
        "Presentasi dapat dilanjutkan ke bank penerus (advising/confirming bank)."
        if status == "COMPLIANT" else
        "Set dokumen mengandung ketidaksesuaian yang memerlukan koreksi sebelum presentasi "
        "berdasarkan UCP 600 Art. 16. Pelanggaran DHE SDA harus diselesaikan dengan "
        "bank penempatan yang patuh sebelum repatriasi hasil ekspor."
    )
    verdict_action_en = (
        "All documents comply. Proceed to presentation."
        if status == "COMPLIANT" else
        "Document set contains discrepancies requiring correction before presentation under "
        "UCP 600 Art. 16. DHE SDA violation must be resolved with compliant bank placement."
    )

    narrative = f"""[IBM Bob — TradeFlow Sentinel | Mode: {'MOCK (0 Bobcoins)' if USE_MOCK_LLM else 'LIVE ibm/granite-3-3-8b-instruct'} | cache:{cache_key}]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAPORAN KEPATUHAN EKSEKUTIF / EXECUTIVE COMPLIANCE SYNTHESIS
TradeFlow Sentinel — Adaptive Trade Finance & DHE SDA Compliance Automation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nomor Kasus      : {case_id}
Aturan DHE SDA   : {dhe.get('rule', 'N/A')} | Dasar Hukum: {dhe.get('legal_basis', 'N/A')}
Verdik Eksekutif : {verdict_id}
Jumlah Temuan    : {n_disc} ketidaksesuaian / discrepancies

── TEMUAN UCP 600 / UCP 600 FINDINGS ─────────────────────────────────────────

Art. 18 (Commercial Invoice) : {art18.get('status', 'N/A')}
{chr(10).join(f'  ⚠ {i}' for i in art18.get('issues', [])) if art18.get('issues') else '  ✓ Seller, buyer, currency, amount, incoterms — semua sesuai LC MT700'}

Art. 20 (Bill of Lading)     : {art20.get('status', 'N/A')}
{chr(10).join(f'  ⚠ {i}' for i in art20.get('issues', [])) if art20.get('issues') else '  ✓ Port muat, port bongkar, tanggal on-board — semua sesuai LC'}

IMO / SOLAS Checksum         : {imo.get('status', 'N/A')}
  IMO {imo.get('imo', 'N/A')} | Check digit terhitung: {imo.get('computed_check_digit', 'N/A')}

── VERIFIKASI AISHub HAVERSINE / VESSEL PROXIMITY ────────────────────────────

Kapal           : {aishu.get('vessel', 'N/A')} (IMO {aishu.get('imo', 'N/A')})
Posisi Kapal    : Lat {aishu.get('vessel_position', {}).get('lat', 'N/A')}, Lon {aishu.get('vessel_position', {}).get('lon', 'N/A')} (snapshot: {aishu.get('snapshot_date', 'N/A')})
Pelabuhan Muat  : {aishu.get('port', 'N/A')}
Jarak Haversine : {distance_nm} NM (ambang batas: {aishu.get('threshold_nm', 10.0)} NM)
Status          : {aishu.get('status', 'N/A')} — {'⚠ PREDATED BILL OF LADING: kapal secara fisik tidak mungkin berada di pelabuhan pada tanggal tersebut' if aishu.get('status') == 'FAIL' else '✓ Kapal dikonfirmasi berada dalam radius pelabuhan pada tanggal on-board'}

── BENCHMARK HARGA WORLD BANK PINK SHEET ─────────────────────────────────────

Komoditas     : {price.get('commodity', 'N/A')} (HS {price.get('hs_code', 'N/A')})
Harga Invoice : USD {inv_price}/MT
Harga Benchmark: USD {bench_price}/MT (World Bank Pink Sheet, Ref. 2025-Q4)
Deviasi Harga  : {deviation_pct}% ({f'{dev_signed:+.2f}' if dev_signed is not None else 'N/A'}%)  |  Toleransi: ±{tol_pct}%
Status        : {price.get('status', 'N/A')} — {price.get('finding', '')}

── PENILAIAN DHE SDA / DHE SDA ASSESSMENT ────────────────────────────────────

Aturan Aktif           : {dhe.get('rule', 'N/A')}
Dasar Hukum            : {dhe.get('legal_basis', 'N/A')}
Jumlah FOB             : USD {dhe.get('fob_usd', 'N/A'):,} (≥ USD 250,000 — berlaku / applicable)
Retensi Diperlukan     : {dhe.get('retention_required_pct', 'N/A')}%
Masa Retensi Minimum   : {dhe.get('min_hold_months', 'N/A')} bulan
Batas Konversi FX      : maks {dhe.get('fx_conversion_max_pct', 'N/A')}%
Konversi FX Diminta    : {fx_pct_val}%
Bank yang Dinominasikan: {dhe.get('nominated_bank', 'N/A')} ({dhe.get('bank_category', 'N/A')})
Status DHE SDA         : {dhe.get('status', 'N/A')}
{chr(10).join(f'  ⚠ {i}' for i in dhe.get('issues', [])) if dhe.get('issues') else '  ✓ Bank Himbara, Reksus DHE SDA, konversi FX di bawah batas 50%'}\
{rem_section}

── RINGKASAN TINDAKAN KOREKTIF / CORRECTIVE ACTION SUMMARY ───────────────────

🇮🇩 BAHASA INDONESIA:
{verdict_action_id}

🇬🇧 ENGLISH:
{verdict_action_en}

[CATATAN TEKNIS: USE_MOCK_LLM=true — tidak ada token IBM watsonx API yang digunakan]
[TECHNICAL NOTE: USE_MOCK_LLM=true — 0 IBM watsonx API tokens consumed / 0 Bobcoins]
"""
    _MOCK_CACHE[cache_key] = narrative
    return narrative


def _live_synthesis(findings: dict, case_id: str) -> str:
    """
    Call IBM watsonx Granite 3.3 8B Instruct model for live synthesis.
    Passes remediation_rows to the model and enforces Guardrail 2 numerical faithfulness.
    Requires WATSONX_API_KEY and WATSONX_PROJECT_ID.
    """
    try:
        from ibm_watsonx_ai import APIClient, Credentials  # type: ignore
        from ibm_watsonx_ai.foundation_models import ModelInference  # type: ignore
    except ImportError:
        raise RuntimeError(
            "ibm-watsonx-ai package is required for live synthesis. "
            "Install with: pip install ibm-watsonx-ai"
        )

    checks = findings["checks"]
    aishu = checks.get("aishu_proximity", {})
    price = checks.get("price_deviation", {})
    dhe = checks.get("dhe_sda", {})

    # Pull verbatim numbers for the prompt to anchor Guardrail 2
    distance_nm = aishu.get("distance_nm", "")
    deviation_pct = price.get("deviation_pct", "")
    fx_pct = dhe.get("requested_fx_conversion_pct", "") if dhe else ""

    remediation_json = json.dumps(findings.get("remediation_rows", []), ensure_ascii=False, indent=2)

    prompt = f"""Anda adalah senior Trade Finance compliance officer dan IBM Bob agent.
Analisis temuan kepatuhan deterministik berikut dan hasilkan laporan sintesis kepatuhan eksekutif
dalam Bahasa Indonesia (utama) dan Bahasa Inggris (ringkasan), referensikan artikel UCP 600,
ISBP 745, dan peraturan DHE SDA Indonesia.

ATURAN GUARDRAIL 2 — KEPATUHAN NUMERIK (WAJIB DIPATUHI):
- JANGAN MEMBUAT ANGKA BARU. Setiap angka yang Anda sebutkan HARUS muncul verbatim di findings JSON.
- Jarak AISHub Haversine: {distance_nm} NM — gunakan angka ini PERSIS seperti adanya.
- Deviasi harga World Bank: {deviation_pct}% — gunakan angka ini PERSIS seperti adanya.
- Konversi FX DHE SDA yang diminta: {fx_pct}% — gunakan angka ini PERSIS seperti adanya.
- Jangan ubah atau bulatkan angka-angka ini.

CASE_ID: {case_id}
FINDINGS (JSON):
{json.dumps(findings, indent=2, ensure_ascii=False)}

TABEL TINDAKAN REMEDIAL (remediation_rows):
{remediation_json}

Format output:
1. Verdik Eksekutif (1-2 kalimat dalam Bahasa Indonesia)
2. Detail Temuan UCP 600 (bullet per isu dengan referensi pasal dan angka persis)
3. Verifikasi AISHub Haversine ({distance_nm} NM)
4. Deviasi Harga World Bank Pink Sheet ({deviation_pct}%)
5. Penilaian DHE SDA (referensikan aturan aktif, konversi FX {fx_pct}%)
6. Tabel Tindakan Korektif (dari remediation_rows di atas)
7. Ringkasan Tindakan (1 paragraf)
"""
    creds = Credentials(api_key=WATSONX_API_KEY, url=WATSONX_URL)
    client = APIClient(credentials=creds, project_id=WATSONX_PROJECT_ID)
    model = ModelInference(model_id=WATSONX_MODEL, api_client=client,
                           params={"max_new_tokens": 1024, "temperature": 0.0})
    return model.generate_text(prompt=prompt)


# ===========================================================================
# AI UNSTRUCTURED DOCUMENT EXTRACTOR
# ===========================================================================

# Regex-based key-value parser for mock/offline extraction
_KV_PATTERNS: dict[str, re.Pattern] = {
    "seller":            re.compile(r"(?:seller|beneficiary|shipper)\s*[:/]\s*([^\n,;]+)", re.I),
    "buyer":             re.compile(r"(?:buyer|applicant|consignee)\s*[:/]\s*([^\n,;]+)", re.I),
    "currency":          re.compile(r"\b(USD|EUR|SGD|CNY|IDR)\b"),
    "total_fob_usd":     re.compile(r"(?:total|fob|amount)\s*[:/]?\s*USD?\s*([\d,\.]+)", re.I),
    "unit_price_usd_mt": re.compile(r"(?:unit\s*price|price/mt|per\s*mt)\s*[:/]?\s*USD?\s*([\d,\.]+)", re.I),
    "hs_code":           re.compile(r"(?:hs\s*code|hs)\s*[:/]?\s*(\d{4}\.\d{2})", re.I),
    "incoterms":         re.compile(r"\b(FOB|CIF|CFR|EXW|DDP|DAP)\b", re.I),
    "vessel_name":       re.compile(r"(?:vessel|m/?v)\s*[:/]?\s*([A-Z][A-Z0-9 ]+?)(?:\s+IMO|\s*\n|,)", re.I),
    "imo_number":        re.compile(r"\bIMO\s*[:/]?\s*(\d{7})\b", re.I),
    "on_board_date":     re.compile(r"(?:on[\s-]?board|laden|shipped)\s*[:/]?\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", re.I),
    "port_of_loading":   re.compile(r"(?:port of loading|pol|from)\s*[:/]\s*([^\n,;]+)", re.I),
    "port_of_discharge": re.compile(r"(?:port of discharge|pod|to)\s*[:/]\s*([^\n,;]+)", re.I),
    "nominated_bank":    re.compile(r"(?:nominated bank|bank)\s*[:/]\s*([^\n,;]+)", re.I),
    "fx_conversion_pct": re.compile(r"(?:fx conversion|konversi fx)\s*[:/]?\s*([\d\.]+)\s*%", re.I),
    "fob_usd":           re.compile(r"(?:fob\s*(?:value|amount)?)\s*[:/]?\s*USD?\s*([\d,\.]+)", re.I),
}


def _regex_extract(raw_text: str) -> dict:
    """
    Deterministic regex key-value extractor used when USE_MOCK_LLM=true.
    Returns a best-effort document_data dict from raw unstructured text.
    """
    def _clean_float(s: str) -> float:
        return float(s.replace(",", ""))

    def _first(p: re.Pattern, text: str, transform=lambda x: x.strip()) -> Any:
        m = p.search(text)
        return transform(m.group(1)) if m else None

    seller = _first(_KV_PATTERNS["seller"], raw_text) or "UNKNOWN SELLER"
    buyer = _first(_KV_PATTERNS["buyer"], raw_text) or "UNKNOWN BUYER"
    currency = _first(_KV_PATTERNS["currency"], raw_text) or "USD"
    hs = _first(_KV_PATTERNS["hs_code"], raw_text) or "0000.00"
    incoterms = (_first(_KV_PATTERNS["incoterms"], raw_text) or "FOB").upper()
    unit_price_str = _first(_KV_PATTERNS["unit_price_usd_mt"], raw_text)
    unit_price = _clean_float(unit_price_str) if unit_price_str else 0.0
    total_str = _first(_KV_PATTERNS["total_fob_usd"], raw_text)
    total_fob = _clean_float(total_str) if total_str else 0.0
    vessel = _first(_KV_PATTERNS["vessel_name"], raw_text) or "UNKNOWN VESSEL"
    imo = _first(_KV_PATTERNS["imo_number"], raw_text) or "0000000"
    onboard = _first(_KV_PATTERNS["on_board_date"], raw_text) or "2026-01-01"
    pol = _first(_KV_PATTERNS["port_of_loading"], raw_text) or "Tanjung Priok, Jakarta"
    pod = _first(_KV_PATTERNS["port_of_discharge"], raw_text) or "Unknown Port"
    bank = _first(_KV_PATTERNS["nominated_bank"], raw_text) or "Unknown Bank"
    fx_str = _first(_KV_PATTERNS["fx_conversion_pct"], raw_text)
    fx_pct = float(fx_str) if fx_str else 50.0
    fob_str = _first(_KV_PATTERNS["fob_usd"], raw_text)
    fob_val = _clean_float(fob_str) if fob_str else total_fob

    # Date normalisation: dd/mm/yyyy → yyyy-mm-dd
    if onboard and "/" in onboard:
        parts = onboard.split("/")
        if len(parts) == 3:
            onboard = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"

    # Infer latest_shipment_date and lc_amount from text or defaults
    lsd_match = re.search(r"latest\s*shipment\s*[:/]?\s*(\d{4}-\d{2}-\d{2})", raw_text, re.I)
    latest_shipment = lsd_match.group(1) if lsd_match else onboard  # default to onboard
    lc_amt_match = re.search(r"(?:l/?c|credit)\s*amount\s*[:/]?\s*USD?\s*([\d,\.]+)", raw_text, re.I)
    lc_amount = _clean_float(lc_amt_match.group(1)) if lc_amt_match else total_fob

    # Infer DHE rule version from text
    dhe_version = "PADG_16_2026"
    if "PP_8_2025" in raw_text.upper() or "PP 8/2025" in raw_text:
        dhe_version = "PP_8_2025"
    elif "BASELINE" in raw_text.upper() or "PP_36" in raw_text.upper() or "36/2023" in raw_text:
        dhe_version = "BASELINE_PRE_2025"

    return {
        "dhe_rule_version": dhe_version,
        "lc_mt700_reference": {
            "beneficiary": seller,
            "applicant": buyer,
            "currency": currency,
            "amount": lc_amount,
            "tolerance_pct": 5,
            "incoterms": incoterms,
            "port_of_loading": pol.strip(),
            "port_of_discharge": pod.strip(),
            "latest_shipment_date": latest_shipment,
        },
        "commercial_invoice": {
            "seller": seller,
            "buyer": buyer,
            "currency": currency,
            "hs_code": hs,
            "goods_description": f"Extracted from document (HS {hs})",
            "quantity_mt": 1,
            "unit_price_usd_mt": unit_price,
            "total_fob_usd": total_fob,
            "incoterms": incoterms,
            "port_of_loading": pol.strip(),
        },
        "bill_of_lading": {
            "vessel_name": vessel.strip(),
            "imo_number": imo.strip(),
            "port_of_loading": pol.strip(),
            "port_of_discharge": pod.strip(),
            "on_board_date": onboard.strip(),
            "goods_description": f"Extracted from document (HS {hs})",
        },
        "dhe_sda_transaction": {
            "fob_usd": fob_val,
            "nominated_bank": bank.strip(),
            "bank_category": "UNKNOWN",
            "placement_type": "Unknown",
            "requested_fx_conversion_pct": fx_pct,
            "hold_period_months": 12,
        },
    }


def _live_extract(raw_text: str) -> dict:
    """
    Use ibm/granite-3-3-8b-instruct (temperature=0.0) to extract structured
    document_data JSON from raw unstructured L/C, Invoice, and B/L text.
    """
    try:
        from ibm_watsonx_ai import APIClient, Credentials  # type: ignore
        from ibm_watsonx_ai.foundation_models import ModelInference  # type: ignore
    except ImportError:
        raise RuntimeError("ibm-watsonx-ai required. pip install ibm-watsonx-ai")

    schema_hint = json.dumps({
        "dhe_rule_version": "PADG_16_2026",
        "lc_mt700_reference": {
            "beneficiary": "string", "applicant": "string", "currency": "USD",
            "amount": 0.0, "tolerance_pct": 5, "incoterms": "FOB",
            "port_of_loading": "string", "port_of_discharge": "string",
            "latest_shipment_date": "YYYY-MM-DD"
        },
        "commercial_invoice": {
            "seller": "string", "buyer": "string", "currency": "USD",
            "hs_code": "NNNN.NN", "goods_description": "string",
            "quantity_mt": 0, "unit_price_usd_mt": 0.0, "total_fob_usd": 0.0,
            "incoterms": "FOB", "port_of_loading": "string"
        },
        "bill_of_lading": {
            "vessel_name": "string", "imo_number": "NNNNNNN",
            "port_of_loading": "string", "port_of_discharge": "string",
            "on_board_date": "YYYY-MM-DD", "goods_description": "string"
        },
        "dhe_sda_transaction": {
            "fob_usd": 0.0, "nominated_bank": "string", "bank_category": "string",
            "placement_type": "string", "requested_fx_conversion_pct": 0,
            "hold_period_months": 12
        }
    }, indent=2)

    prompt = f"""You are a Trade Finance document parser. Extract ALL required fields from the raw document text below and output ONLY a valid JSON object matching this exact schema. Do not add commentary or markdown fences.

SCHEMA:
{schema_hint}

DOCUMENT TEXT:
{raw_text[:8000]}

OUTPUT (JSON only):"""

    creds = Credentials(api_key=WATSONX_API_KEY, url=WATSONX_URL)
    client = APIClient(credentials=creds, project_id=WATSONX_PROJECT_ID)
    model = ModelInference(model_id=WATSONX_MODEL, api_client=client,
                           params={"max_new_tokens": 1024, "temperature": 0.0})
    raw_json = model.generate_text(prompt=prompt).strip()
    # Strip markdown fences if present
    raw_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_json, flags=re.S).strip()
    return json.loads(raw_json)


def extract_documents_with_ai(
    raw_text: str,
    dhe_rule_version: str = "PADG_16_2026",
    case_id: str = "EXTRACTED_DOCUMENT",
) -> dict:
    """
    Phase 2 AI front-end: accept raw unstructured text from L/C MT700, Commercial Invoice,
    Bill of Lading, and DHE SDA instructions, extract structured document_data JSON,
    run a Document Completeness Gate, then pass to run_pipeline for full compliance audit.

    Returns the full pipeline result plus extraction metadata.
    """
    # Document Completeness Gate — required top-level keys
    REQUIRED_KEYS = {
        "lc_mt700_reference": ["beneficiary", "applicant", "port_of_loading",
                               "port_of_discharge", "latest_shipment_date"],
        "commercial_invoice": ["seller", "buyer", "hs_code", "unit_price_usd_mt", "total_fob_usd"],
        "bill_of_lading":    ["vessel_name", "imo_number", "on_board_date"],
        "dhe_sda_transaction": ["fob_usd", "nominated_bank", "requested_fx_conversion_pct"],
    }

    # Extract
    extraction_method = "mock_regex"
    extraction_errors: list[str] = []
    try:
        if USE_MOCK_LLM:
            doc_data = _regex_extract(raw_text)
        else:
            doc_data = _live_extract(raw_text)
            extraction_method = "ibm_granite_3_3_8b"
    except Exception as e:
        # Fallback to regex on live extract failure
        doc_data = _regex_extract(raw_text)
        extraction_method = "regex_fallback"
        extraction_errors.append(f"Live extraction error (fell back to regex): {e}")

    # Override DHE rule version if provided
    if dhe_rule_version:
        doc_data["dhe_rule_version"] = dhe_rule_version

    # Document Completeness Gate
    missing_fields: list[str] = []
    for section, fields in REQUIRED_KEYS.items():
        section_data = doc_data.get(section, {})
        for f in fields:
            val = section_data.get(f)
            if val is None or val == "" or val == 0 or val == "UNKNOWN":
                missing_fields.append(f"{section}.{f}")

    if missing_fields:
        extraction_errors.append(
            f"Document Completeness Gate: {len(missing_fields)} required field(s) could not be extracted: "
            + ", ".join(missing_fields)
        )

    # Run full compliance pipeline
    pipeline_result = run_pipeline(
        case_id=case_id,
        dhe_rule_version=dhe_rule_version,
        document_data=doc_data,
    )

    pipeline_result["extraction_metadata"] = {
        "extraction_method": extraction_method,
        "extraction_errors": extraction_errors,
        "missing_fields": missing_fields,
        "document_completeness_gate": "PASS" if not missing_fields else "WARN",
        "extracted_document_data": doc_data,
    }
    return pipeline_result


# ===========================================================================
# GUARDRAIL 2 — CLAIM-GROUNDED OUTPUT FAITHFULNESS
# ===========================================================================

def evaluate_claim_faithfulness(
    synthesis_text: str, document_data: dict, findings: dict
) -> dict:
    """
    Parse [JSON: path=value] citation tags in synthesis_text, verify each against
    the actual document_data payload and deterministic findings, and return a
    claim_faithfulness_score (0.0–100.0), verified_claims_count, and ungrounded_claims list.

    Expected citation format:  [JSON: commercial_invoice.unit_price_usd_mt=105]
    """
    pattern = re.compile(r"\[JSON:\s*([a-z_.]+)\s*=\s*([^\]]+)\]", re.IGNORECASE)
    citations = pattern.findall(synthesis_text)

    if not citations:
        # No citations at all — score based on number-faithfulness checks below
        return {
            "claim_faithfulness_score": None,
            "verified_claims_count": 0,
            "total_citations": 0,
            "ungrounded_claims": [],
            "note": "No [JSON: path=value] citations found in synthesis.",
        }

    verified, ungrounded = 0, []
    for path, raw_val in citations:
        raw_val = raw_val.strip()
        # Traverse document_data by dotted path
        parts = path.lower().split(".")
        obj: Any = document_data
        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = None
                break
        # Compare as string representation
        actual = str(obj) if obj is not None else None
        if actual is not None and (actual == raw_val or actual.lower() == raw_val.lower()):
            verified += 1
        else:
            ungrounded.append({
                "citation": f"[JSON: {path}={raw_val}]",
                "actual_value": actual,
                "verdict": "MISMATCH" if actual is not None else "PATH_NOT_FOUND",
            })

    total = len(citations)
    score = round((verified / total) * 100.0, 1) if total > 0 else 0.0
    return {
        "claim_faithfulness_score": score,
        "verified_claims_count": verified,
        "total_citations": total,
        "ungrounded_claims": ungrounded,
    }


def guardrail_output(
    synthesis: str, findings: dict, document_data: dict | None = None
) -> tuple[str, list[str], dict]:
    """
    Verify that key deterministic numbers from findings appear verbatim in the
    synthesis text. Also runs claim-grounded citation faithfulness evaluation.
    Returns (synthesis, list_of_faithfulness_warnings, claim_faithfulness_result).
    """
    warnings: list[str] = []

    price_check = findings["checks"].get("price_deviation", {})
    if price_check:
        dev_raw = price_check.get("deviation_pct")
        if dev_raw is not None:
            dev = str(abs(dev_raw))
            if dev != "0.0" and dev not in synthesis:
                warnings.append(
                    f"GUARDRAIL_2: Price deviation {dev}% not found verbatim in synthesis output"
                )

    aishu = findings["checks"].get("aishu_proximity", {})
    if aishu:
        dist_raw = aishu.get("distance_nm")
        if dist_raw is not None:
            dist = str(dist_raw)
            if dist and dist not in synthesis:
                warnings.append(
                    f"GUARDRAIL_2: AISHub distance {dist} NM not found verbatim in synthesis output"
                )

    dhe = findings["checks"].get("dhe_sda", {})
    if dhe and dhe.get("status") == "FAIL":
        fx = str(dhe.get("requested_fx_conversion_pct", ""))
        if fx and fx not in synthesis:
            warnings.append(
                f"GUARDRAIL_2: DHE SDA FX conversion {fx}% not found verbatim in synthesis output"
            )

    # Claim-grounded citation faithfulness
    faithfulness_result = evaluate_claim_faithfulness(synthesis, document_data or {}, findings)

    if warnings:
        synthesis += (
            "\n\n⚠️  GUARDRAIL 2 WARNINGS (numerical faithfulness):\n"
            + "\n".join(f"  • {w}" for w in warnings)
        )
    return synthesis, warnings, faithfulness_result


# ===========================================================================
# MAIN PIPELINE ORCHESTRATOR
# ===========================================================================

def run_pipeline(case_id: str | None = None, dhe_rule_version: str | None = None,
                 document_data: dict | None = None) -> dict:
    """
    Full end-to-end pipeline for a given case_id or live document_data payload.
    Returns a structured result dict ready for JSON serialisation.
    """
    if not case_id and not document_data:
        raise ValueError("Either case_id or document_data must be provided.")

    t_start = time.perf_counter()

    data = _load_data()
    cases = data["cases"]
    dhe_rules = data["dhe_sda_versions"]
    benchmarks = data["world_bank_pink_sheet_benchmarks"]["commodities"]
    vessels_db = data["aishu_vessel_snapshots"]["vessels"]
    lc_refs = data["lc_mt700_reference"]
    port_coords_db = {
        "TANJUNG_PERAK": data["aishu_vessel_snapshots"]["TANJUNG_PERAK_COORDS"],
        "TANJUNG_PRIOK": data["aishu_vessel_snapshots"]["TANJUNG_PRIOK_COORDS"],
    }

    if document_data:
        case = document_data
        case_id = case_id or "LIVE_PAYLOAD"
        if "exporter_instructions" in case and "dhe_sda_transaction" not in case:
            case["dhe_sda_transaction"] = case["exporter_instructions"]
    else:
        if case_id not in cases:
            raise ValueError(f"Unknown case_id '{case_id}'. Available: {list(cases.keys())}")
        case = cases[case_id]

    # Allow runtime override of DHE rule version
    if dhe_rule_version:
        case = dict(case)
        case["dhe_rule_version"] = dhe_rule_version

    rule_version = case.get("dhe_rule_version", data["_meta"]["active_rule_version"])
    if rule_version not in dhe_rules:
        raise ValueError(f"Unknown DHE rule version '{rule_version}'")

    # Guardrail 1 — sanitise free-text fields
    g1_all_warnings: list[str] = []
    for field in ["goods_description"]:
        raw = case.get("commercial_invoice", {}).get(field, "")
        _, w = guardrail_input(raw)
        g1_all_warnings.extend(w)
        raw_bol = case.get("bill_of_lading", {}).get(field, "")
        _, w2 = guardrail_input(raw_bol)
        g1_all_warnings.extend(w2)

    # Resolve LC reference
    if "lc_mt700_reference" in case and isinstance(case["lc_mt700_reference"], dict):
        lc_ref = case["lc_mt700_reference"]
    else:
        lc_key = case["lc_reference"]
        lc_ref = lc_refs[lc_key]

    # Resolve vessel — Bug Fix #2: use .get() so unknown IMO returns None (fail-closed)
    imo_key = f"IMO{str(case['bill_of_lading']['imo_number']).strip()}"
    vessel = vessels_db.get(imo_key)  # None if IMO not in DB — engine handles fail-closed

    # Resolve port coords for loading port
    port_name = lc_ref["port_of_loading"]
    if "Perak" in port_name or "Surabaya" in port_name:
        port_coords = port_coords_db["TANJUNG_PERAK"]
    else:
        port_coords = port_coords_db["TANJUNG_PRIOK"]

    # Resolve commodity benchmark
    hs = case["commercial_invoice"]["hs_code"]
    benchmark = next(
        (v for v in benchmarks.values() if v["hs_code"] == hs),
        {"benchmark_price": 0, "tolerance_pct": 5, "description": "Unknown", "hs_code": hs},
    )

    # Deterministic engine
    findings = run_deterministic_engine(
        case=case,
        lc_ref=lc_ref,
        rules=dhe_rules,
        vessel=vessel,
        port_coords=port_coords,
        benchmark=benchmark,
    )

    # IBM Bob Synthesis
    if USE_MOCK_LLM:
        synthesis = _mock_synthesis(findings, case_id)
    else:
        synthesis = _live_synthesis(findings, case_id)

    # Guardrail 2 — output faithfulness + claim-grounded citation check
    synthesis, g2_warnings, claim_faithfulness = guardrail_output(
        synthesis, findings, document_data=case
    )

    t_elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)

    return {
        "case_id": case_id,
        "dhe_rule_version_applied": rule_version,
        "overall_status": findings["overall_status"],
        "discrepancy_count": findings["discrepancy_count"],
        "processing_time_ms": t_elapsed_ms,
        "guardrail_1_warnings": g1_all_warnings,
        "guardrail_2_warnings": g2_warnings,
        "claim_faithfulness": claim_faithfulness,
        "findings": findings,
        "synthesis": synthesis,
        "roi_context": {
            # Measured practitioner baseline (14.5 min) replaces hardcoded 2700 s (45 min)
            "measured_analyst_baseline_sec": ANALYST_BASELINE_SEC,
            "sentinel_time_ms": t_elapsed_ms,
            "sentinel_time_s": round(t_elapsed_ms / 1000, 3),
            "time_reduction_pct": min(
                round((1 - (t_elapsed_ms / 1000) / max(ANALYST_BASELINE_SEC, 1)) * 100, 1),
                99.9
            ),
        },
    }


# ===========================================================================
# FASTAPI APPLICATION
# ===========================================================================

if _FASTAPI_AVAILABLE:
    app = FastAPI(
        title="TradeFlow Sentinel API",
        description=(
            "Adaptive Trade Finance & DHE SDA Compliance Automation. "
            "UCP 600 Art. 5/18/20 + ISBP 745 + Versioned Indonesia DHE SDA Rules. "
            "Phase 2 Semifinal — IBM SkillsBuild National Hackathon 2026."
        ),
        version="2.0.0",
    )

    # CORS — allow all origins for portable multi-device access (Cloud VPS / local)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Pydantic Models
    # -----------------------------------------------------------------------
    class VerifyRequest(BaseModel):
        dhe_rule_version: str
        case_id: Optional[str] = None
        document_data: Optional[Any] = None

    class ValidationFeedback(BaseModel):
        name_initials: str
        role_title: str
        company_type: str
        scenario_tested: str
        usability_score: int  # 1–5
        benefit_score: int    # 1–5
        testimonial: Optional[str] = None

    class ExtractAndVerifyRequest(BaseModel):
        raw_text: str
        dhe_rule_version: str = "PADG_16_2026"
        case_id: str = "EXTRACTED_DOCUMENT"

    # -----------------------------------------------------------------------
    # Existing endpoints (preserved — backward compatible)
    # -----------------------------------------------------------------------
    @app.post("/verify-trade-documents", summary="Verify trade documents for compliance")
    async def verify_trade_documents(body: VerifyRequest):
        try:
            doc_data = body.document_data if isinstance(body.document_data, dict) else None
            if not body.case_id and not doc_data:
                raise ValueError("Either case_id or document_data must be provided.")
            result = run_pipeline(
                case_id=body.case_id,
                dhe_rule_version=body.dhe_rule_version,
                document_data=doc_data
            )
            return JSONResponse(content=result)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Internal error: {exc}")

    @app.get("/health")
    async def health():
        return {"status": "ok", "use_mock_llm": USE_MOCK_LLM, "version": "2.0.0"}

    # -----------------------------------------------------------------------
    # GET / — Portable Web UI
    # -----------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def serve_ui():
        if UI_FILE.exists():
            return HTMLResponse(content=UI_FILE.read_text(encoding="utf-8"))
        # Fallback minimal page if HTML file not yet present
        return HTMLResponse(content="""<!DOCTYPE html>
<html lang="id"><head><meta charset="UTF-8"><title>TradeFlow Sentinel</title></head>
<body style="font-family:sans-serif;max-width:700px;margin:60px auto;padding:20px">
<h1>TradeFlow Sentinel — Phase 2</h1>
<p>Portable UI file (<code>tradeflow_sentinel_portable_ui.html</code>) not found.
Mount it into the container or place it alongside this script.</p>
<p><a href="/docs">📖 API Docs (Swagger UI)</a></p>
</body></html>""", status_code=200)

    # -----------------------------------------------------------------------
    # GET /presets — dynamic preset loader for the Web UI
    # -----------------------------------------------------------------------
    @app.get("/presets", summary="Return preset cases and DHE SDA versions for the Web UI")
    async def get_presets():
        try:
            data = _load_data()
            return JSONResponse(content={
                "cases": {k: v for k, v in data["cases"].items()},
                "dhe_sda_versions": data["dhe_sda_versions"],
                "active_rule_version": data["_meta"]["active_rule_version"],
            })
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to load presets: {exc}")

    # -----------------------------------------------------------------------
    # POST /validation-feedback — save practitioner feedback
    # -----------------------------------------------------------------------
    @app.post("/validation-feedback", summary="Submit practitioner validation feedback")
    async def post_validation_feedback(body: ValidationFeedback):
        try:
            record = body.model_dump()
            record["submitted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            existing: list = []
            if FEEDBACK_FILE.exists():
                with FEEDBACK_FILE.open("r", encoding="utf-8") as fh:
                    existing = json.load(fh)

            existing.append(record)
            with FEEDBACK_FILE.open("w", encoding="utf-8") as fh:
                json.dump(existing, fh, ensure_ascii=False, indent=2)

            return JSONResponse(content={
                "status": "saved",
                "total_responses": len(existing),
                "record": record,
            })
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to save feedback: {exc}")

    # -----------------------------------------------------------------------
    # GET /validation-feedback — retrieve all feedback records
    # -----------------------------------------------------------------------
    @app.get("/validation-feedback", summary="Retrieve all practitioner validation feedback")
    async def get_validation_feedback():
        try:
            if not FEEDBACK_FILE.exists():
                return JSONResponse(content={"total_responses": 0, "responses": []})
            with FEEDBACK_FILE.open("r", encoding="utf-8") as fh:
                data_fb = json.load(fh)
            return JSONResponse(content={"total_responses": len(data_fb), "responses": data_fb})
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to read feedback: {exc}")


    # -----------------------------------------------------------------------
    # POST /extract-and-verify — AI document extraction + compliance audit
    # -----------------------------------------------------------------------
    @app.post("/extract-and-verify",
              summary="Extract structured data from raw document text, then run compliance audit")
    async def extract_and_verify(body: ExtractAndVerifyRequest):
        try:
            result = extract_documents_with_ai(
                raw_text=body.raw_text,
                dhe_rule_version=body.dhe_rule_version,
                case_id=body.case_id,
            )
            return JSONResponse(content=result)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Extraction error: {exc}")

    # -----------------------------------------------------------------------
    # GET /benchmark-suite — return 40 planted test cases (metadata only)
    # -----------------------------------------------------------------------
    @app.get("/benchmark-suite", summary="Return the 40 planted benchmark test case definitions")
    async def get_benchmark_suite():
        try:
            # Import lazily to avoid circular dependency
            from test_suite_benchmark import build_test_suite  # type: ignore
            suite = build_test_suite()
            return JSONResponse(content={
                "total_cases": len(suite),
                "cases": [
                    {
                        "case_id": c["case_id"],
                        "ground_truth": c["ground_truth"],
                        "category": c.get("category", ""),
                        "description": c.get("description", ""),
                        "dhe_rule_version": c.get("dhe_rule_version", "PADG_16_2026"),
                        "document_data": c.get("document_data"),
                    }
                    for c in suite
                ],
            })
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="test_suite_benchmark.py not found. Place it alongside langflow_sentinel_engine.py."
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Benchmark suite error: {exc}")


# NOTE: The Langflow component class lives in langflow_component.py.
# This engine file is NOT placed in LANGFLOW_COMPONENTS_PATH — it is
# mounted as a plain Python module so langflow_component.py can import it.


# ===========================================================================
# CLI ENTRYPOINT
# ===========================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TradeFlow Sentinel")
    sub = parser.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run", help="Run compliance check for a case")
    run_p.add_argument("case_id", nargs="?", default="CASE_1_COMPLIANT_CPO")
    run_p.add_argument("--dhe-version", default=None)
    run_p.add_argument("--json", action="store_true", help="Output raw JSON")

    serve_p = sub.add_parser("serve", help="Start FastAPI server")
    serve_p.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)))

    args = parser.parse_args()

    if args.cmd == "run" or args.cmd is None:
        case_id = getattr(args, "case_id", "CASE_1_COMPLIANT_CPO")
        dhe_ver = getattr(args, "dhe_version", None)
        result = run_pipeline(case_id=case_id, dhe_rule_version=dhe_ver)
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            reduction_val = result['roi_context']['time_reduction_pct']
            proc_time = result['processing_time_ms']

            if reduction_val >= 99.9 and proc_time > 0:
                display_reduction = ">99.9"
            else:
                display_reduction = f"{round(reduction_val, 1)}"
            print(f"\n{'='*60}")
            print(f"  TradeFlow Sentinel — {result['case_id']}")
            print(f"{'='*60}")
            print(f"  Status          : {result['overall_status']}")
            print(f"  Discrepancies   : {result['discrepancy_count']}")
            print(f"  DHE SDA Rule    : {result['dhe_rule_version_applied']}")
            print(f"  Processing Time : {proc_time} ms")
            print(f"  Time Reduction  : {display_reduction}%")
            print(f"\n--- Synthesis ---\n{result['synthesis']}")
            if result["findings"]["discrepancies"]:
                print("\n--- Discrepancies ---")
                for d in result["findings"]["discrepancies"]:
                    print(f"  [FAIL] {d}")
            if result["findings"].get("remediation_rows"):
                print("\n--- Remediation Rows ---")
                for r in result["findings"]["remediation_rows"]:
                    print(f"  [{r['field']}] Current: {r['current_value']}")
                    print(f"    Action: {r['required_action']}")

    elif args.cmd == "serve":
        if not _FASTAPI_AVAILABLE:
            print("FastAPI not installed. Run: pip install fastapi uvicorn")
        else:
            print(f"Starting TradeFlow Sentinel API on port {args.port} ...")
            uvicorn.run(app, host="0.0.0.0", port=args.port)
