"""
TradeFlow Sentinel — Node 2: Compliance Engine
===============================================
Receives the structured document set from Node 1 (Trade Document Input)
and runs all deterministic compliance checks:
  - UCP 600 Art. 18 (Commercial Invoice cross-check)
  - UCP 600 Art. 20 (Bill of Lading cross-check)
  - SOLAS IMO Number Checksum
  - AISHub Vessel Proximity Validation
  - World Bank Pink Sheet Price Deviation
  - Versioned DHE SDA Regulatory Compliance

Self-contained: no cross-file Python imports.
"""

from __future__ import annotations

import math
import os
import re
from typing import Any

from langflow.custom import Component
from langflow.io import HandleInput, Output
from langflow.schema import Data

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
PORT_PROXIMITY_THRESHOLD_NM = float(os.getenv("PORT_PROXIMITY_THRESHOLD_NM", "10.0"))
PRICE_DEVIATION_MAX_DEFAULT_PCT = float(os.getenv("PRICE_DEVIATION_MAX_DEFAULT_PCT", "10.0"))


# ---------------------------------------------------------------------------
# SOLAS IMO CHECKSUM
# ---------------------------------------------------------------------------

def _solas_imo_checksum(imo_str: str) -> tuple[bool, int]:
    digits = re.sub(r"[^0-9]", "", imo_str)
    if len(digits) != 7:
        return False, -1
    total = sum(int(digits[i]) * (7 - i) for i in range(6))
    check = total % 10
    return check == int(digits[6]), check


# ---------------------------------------------------------------------------
# HAVERSINE DISTANCE
# ---------------------------------------------------------------------------

def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R_NM = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R_NM * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# DETERMINISTIC TRADE COMPLIANCE ENGINE
# ---------------------------------------------------------------------------

def _run_deterministic_engine(case: dict, lc_ref: dict, rules: dict,
                               vessel: dict, port_coords: dict, benchmark: dict) -> dict:
    findings: dict[str, Any] = {
        "checks": {},
        "discrepancies": [],
        "overall_status": "COMPLIANT",
    }

    inv = case["commercial_invoice"]
    bol = case["bill_of_lading"]
    dhe = case["dhe_sda_transaction"]

    # ── UCP 600 Art. 18 — Commercial Invoice ──────────────────────────
    art18: dict[str, Any] = {"rule": "UCP 600 Art. 18 — Commercial Invoice"}
    ci_issues: list[str] = []
    if inv["seller"].upper() != lc_ref["beneficiary"].upper():
        ci_issues.append(f"Seller '{inv['seller']}' ≠ LC beneficiary '{lc_ref['beneficiary']}'")
    if inv["buyer"].upper() != lc_ref["applicant"].upper():
        ci_issues.append(f"Buyer '{inv['buyer']}' ≠ LC applicant '{lc_ref['applicant']}'")
    if inv["currency"] != lc_ref["currency"]:
        ci_issues.append(f"Currency mismatch: invoice '{inv['currency']}' ≠ LC '{lc_ref['currency']}'")
    if abs(inv["total_fob_usd"] - lc_ref["amount"]) > lc_ref["amount"] * lc_ref["tolerance_pct"] / 100:
        ci_issues.append(
            f"Amount mismatch: invoice USD {inv['total_fob_usd']:,} outside LC "
            f"USD {lc_ref['amount']:,} ± {lc_ref['tolerance_pct']}%"
        )
    if inv["incoterms"] != lc_ref["incoterms"]:
        ci_issues.append(f"Incoterms mismatch: '{inv['incoterms']}' ≠ '{lc_ref['incoterms']}'")
    art18["status"] = "PASS" if not ci_issues else "FAIL"
    art18["issues"] = ci_issues
    findings["checks"]["ucp_art18_invoice"] = art18
    if ci_issues:
        findings["discrepancies"].extend(ci_issues)

    # ── UCP 600 Art. 20 — Bill of Lading ──────────────────────────────
    art20: dict[str, Any] = {"rule": "UCP 600 Art. 20 — Bill of Lading"}
    bl_issues: list[str] = []
    if bol["port_of_loading"].upper() != lc_ref["port_of_loading"].upper():
        bl_issues.append(
            f"Port of loading mismatch: BoL '{bol['port_of_loading']}' ≠ LC '{lc_ref['port_of_loading']}'"
        )
    if bol["port_of_discharge"].upper() != lc_ref["port_of_discharge"].upper():
        bl_issues.append(
            f"Port of discharge mismatch: BoL '{bol['port_of_discharge']}' ≠ LC '{lc_ref['port_of_discharge']}'"
        )
    if bol["on_board_date"] > lc_ref["latest_shipment_date"]:
        bl_issues.append(
            f"On-board date {bol['on_board_date']} is after LC latest shipment date "
            f"{lc_ref['latest_shipment_date']}"
        )

    # ── AISHub Vessel Proximity ───────────────────────────────────────
    distance_nm = round(_haversine_nm(
        vessel["lat"], vessel["lon"],
        port_coords["lat"], port_coords["lon"]
    ), 2)
    aishu_check: dict[str, Any] = {
        "rule": "AISHub Vessel Proximity (on-board date)",
        "vessel": vessel["vessel_name"],
        "imo": vessel["imo"],
        "snapshot_date": vessel["snapshot_date"],
        "vessel_position": {"lat": vessel["lat"], "lon": vessel["lon"]},
        "port": port_coords.get("port"),
        "port_position": {"lat": port_coords["lat"], "lon": port_coords["lon"]},
        "distance_nm": distance_nm,
        "threshold_nm": PORT_PROXIMITY_THRESHOLD_NM,
    }
    if distance_nm > PORT_PROXIMITY_THRESHOLD_NM:
        msg = (
            f"PREDATED BoL (UCP 600 Art. 20): vessel {vessel['vessel_name']} "
            f"(IMO {vessel['imo']}) was {distance_nm} NM from {port_coords.get('port')} "
            f"on {vessel['snapshot_date']} — physically impossible to be on-board at that port"
        )
        bl_issues.append(msg)
        aishu_check["status"] = "FAIL"
        aishu_check["finding"] = msg
    else:
        aishu_check["status"] = "PASS"
        aishu_check["finding"] = f"Vessel confirmed within {distance_nm} NM of loading port"
    art20["status"] = "PASS" if not bl_issues else "FAIL"
    art20["issues"] = bl_issues
    findings["checks"]["ucp_art20_bol"] = art20
    findings["checks"]["aishu_proximity"] = aishu_check
    if bl_issues:
        findings["discrepancies"].extend(bl_issues)

    # ── SOLAS IMO Checksum ────────────────────────────────────────────
    imo_valid, imo_check_digit = _solas_imo_checksum(bol["imo_number"])
    findings["checks"]["imo_solas"] = {
        "rule": "SOLAS — IMO Number Checksum",
        "imo": bol["imo_number"],
        "computed_check_digit": imo_check_digit,
        "status": "PASS" if imo_valid else "FAIL",
    }
    if not imo_valid:
        findings["discrepancies"].append(f"Invalid IMO checksum for {bol['imo_number']}")

    # ── World Bank Pink Sheet — Price Deviation ───────────────────────
    wb_price = benchmark["benchmark_price"]
    wb_tolerance = benchmark.get("tolerance_pct", PRICE_DEVIATION_MAX_DEFAULT_PCT)
    inv_price = inv["unit_price_usd_mt"]
    deviation_pct = round(((inv_price - wb_price) / wb_price) * 100, 2)
    price_check: dict[str, Any] = {
        "rule": "World Bank Pink Sheet — Unit Price Deviation",
        "commodity": benchmark.get("description"),
        "hs_code": benchmark.get("hs_code"),
        "invoice_price_usd_mt": inv_price,
        "benchmark_price_usd_mt": wb_price,
        "deviation_pct": deviation_pct,
        "tolerance_pct": wb_tolerance,
    }
    if abs(deviation_pct) > wb_tolerance:
        msg = (
            f"Price deviation {deviation_pct:+.2f}% exceeds tolerance ±{wb_tolerance}% "
            f"(invoice ${inv_price}/MT vs benchmark ${wb_price}/MT)"
        )
        price_check["status"] = "FAIL"
        price_check["finding"] = msg
        findings["discrepancies"].append(msg)
    else:
        price_check["status"] = "PASS"
        price_check["finding"] = f"Price within tolerance: {deviation_pct:+.2f}%"
    findings["checks"]["price_deviation"] = price_check

    # ── Versioned DHE SDA Evaluator ───────────────────────────────────
    rule_version = case.get("dhe_rule_version", "PADG_16_2026")
    active_rule = rules[rule_version]
    fob = dhe["fob_usd"]
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
        if fx_pct > active_rule["fx_conversion_to_idr_max_pct"]:
            dhe_issues.append(
                f"Requested FX conversion {fx_pct}% exceeds {rule_version} maximum "
                f"{active_rule['fx_conversion_to_idr_max_pct']}%"
            )
        if rule_version == "PADG_16_2026":
            himbara_banks = [b.upper() for b in active_rule["bank_categories"]["HIMBARA"]]
            nominated = dhe.get("nominated_bank", "").upper()
            is_himbara = any(h.split("(")[0].strip() in nominated for h in himbara_banks)
            if not is_himbara:
                dhe_issues.append(
                    f"Nominated bank '{dhe.get('nominated_bank')}' is NOT a Himbara state-owned bank. "
                    f"{rule_version} restricts placement to: "
                    f"{', '.join(active_rule['bank_categories']['HIMBARA'])}"
                )
            placement_type = dhe.get("placement_type", "")
            if "Reksus" not in placement_type:
                dhe_issues.append(
                    f"Placement type '{placement_type}' is not a Reksus DHE SDA account "
                    f"as required by {rule_version}"
                )
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
            "bank_category": dhe.get("bank_category", ""),
            "status": "PASS" if not dhe_issues else "FAIL",
            "issues": dhe_issues,
        }
        if dhe_issues:
            findings["discrepancies"].extend(dhe_issues)

    findings["overall_status"] = "COMPLIANT" if not findings["discrepancies"] else "DISCREPANT"
    findings["discrepancy_count"] = len(findings["discrepancies"])
    return findings


# ---------------------------------------------------------------------------
# LANGFLOW COMPONENT — NODE 2: Compliance Engine
# ---------------------------------------------------------------------------

class ComplianceEngineComponent(Component):
    """
    Node 2 — Runs UCP 600 Art. 18/20 + SOLAS + AISHub + Price Deviation
    + DHE SDA checks on the document set received from Node 1.

    Connects: ⬅ Trade Document Input (Node 1)  ⮕  Compliance Report (Node 3)
    """

    display_name = "⚖️ Compliance Engine"
    description = (
        "Deterministic UCP 600 Art. 18/20 cross-check + SOLAS IMO checksum "
        "+ AISHub vessel proximity + World Bank price deviation "
        "+ versioned Indonesia DHE SDA compliance engine. "
        "Connect input ← Document Input, output → Compliance Report."
    )
    icon = "shield-check"
    name = "ComplianceEngine"

    inputs = [
        HandleInput(
            name="document_set",
            display_name="Document Set",
            input_types=["Data"],
            info="Connect from Trade Document Input node's 'Document Set' output.",
        ),
    ]

    outputs = [
        Output(
            name="compliance_findings",
            display_name="Compliance Findings",
            method="run_checks",
        ),
    ]

    def run_checks(self) -> Data:
        import time

        t_start = time.perf_counter()

        doc: dict = self.document_set.data if hasattr(self.document_set, "data") else self.document_set

        case = doc["case"]
        case["dhe_rule_version"] = doc["dhe_rule_version"]

        findings = _run_deterministic_engine(
            case=case,
            lc_ref=doc["lc_ref"],
            rules=doc["dhe_rules"],
            vessel=doc["vessel"],
            port_coords=doc["port_coords"],
            benchmark=doc["benchmark"],
        )

        t_elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)

        return Data(data={
            "case_id": doc["case_id"],
            "dhe_rule_version": doc["dhe_rule_version"],
            "findings": findings,
            "guardrail_1_warnings": doc.get("guardrail_1_warnings", []),
            "processing_time_ms": t_elapsed_ms,
        })
