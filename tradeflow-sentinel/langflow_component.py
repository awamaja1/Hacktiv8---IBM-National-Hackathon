"""
TradeFlow Sentinel — Langflow Custom Component (self-contained)
===============================================================
Single-file component: ALL compliance logic is inlined here.
No external file imports. Langflow's validator, code-cache, and
job-executor all see exactly the same source.

Stack: IBM watsonx Orchestrate + Langflow + IBM Bob (watsonx Granite)
Environment variables
---------------------
USE_MOCK_LLM=true      (default) zero-cost MD5-cached mock responses
WATSONX_API_KEY        required only when USE_MOCK_LLM=false
WATSONX_PROJECT_ID     required only when USE_MOCK_LLM=false
WATSONX_URL            defaults to https://us-south.ml.cloud.ibm.com
DATA_FILE              path to synthetic_data_and_rules.json
                       (default: /app/synthetic_data_and_rules.json)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import DropdownInput, Output
from langflow.schema import Data

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
DATA_FILE = Path(os.getenv("DATA_FILE", "/app/synthetic_data_and_rules.json"))
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "true").lower() != "false"

WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_MODEL = os.getenv("WATSONX_MODEL", "ibm/granite-3-3-8b-instruct")

PORT_PROXIMITY_THRESHOLD_NM = float(os.getenv("PORT_PROXIMITY_THRESHOLD_NM", "10.0"))
PRICE_DEVIATION_MAX_DEFAULT_PCT = float(os.getenv("PRICE_DEVIATION_MAX_DEFAULT_PCT", "10.0"))

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
_ACCOUNT_PATTERN = re.compile(r"\b(\d{6,20})\b")
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# ---------------------------------------------------------------------------
# DATA LOADER
# ---------------------------------------------------------------------------

def _load_data() -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_FILE}")
    with DATA_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)

# ---------------------------------------------------------------------------
# GUARDRAIL 1 — INPUT SANITISATION
# ---------------------------------------------------------------------------

def _guardrail_input(text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if _INJECTION_PATTERNS.search(text):
        raise ValueError(
            "GUARDRAIL_1_BLOCKED: Prompt injection pattern detected. Request rejected."
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

    # UCP 600 Art. 18 — Commercial Invoice
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

    # UCP 600 Art. 20 — Bill of Lading
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

    # AISHub vessel proximity
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

    # SOLAS IMO checksum
    imo_valid, imo_check_digit = _solas_imo_checksum(bol["imo_number"])
    findings["checks"]["imo_solas"] = {
        "rule": "SOLAS — IMO Number Checksum",
        "imo": bol["imo_number"],
        "computed_check_digit": imo_check_digit,
        "status": "PASS" if imo_valid else "FAIL",
    }
    if not imo_valid:
        findings["discrepancies"].append(f"Invalid IMO checksum for {bol['imo_number']}")

    # World Bank Pink Sheet — Price Deviation
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

    # Versioned DHE SDA Evaluator
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
# MOCK / CACHED IBM BOB SYNTHESIS
# ---------------------------------------------------------------------------

_MOCK_CACHE: dict[str, str] = {}


def _mock_synthesis(findings: dict, case_id: str) -> str:
    cache_key = hashlib.md5(json.dumps(findings, sort_keys=True).encode()).hexdigest()[:12]
    if cache_key in _MOCK_CACHE:
        return _MOCK_CACHE[cache_key]
    status = findings["overall_status"]
    n_disc = findings["discrepancy_count"]
    disc_list = "\n".join(f"  - {d}" for d in findings["discrepancies"]) or "  None"
    narrative = f"""[IBM Bob — Mock Synthesis | cache:{cache_key}]

CASE: {case_id}
OVERALL STATUS: {status}
DISCREPANCIES FOUND: {n_disc}

{disc_list}

REGULATORY CONTEXT:
  Active DHE SDA Rule: {findings['checks'].get('dhe_sda', {}).get('rule', 'N/A')}
  Legal Basis: {findings['checks'].get('dhe_sda', {}).get('legal_basis', 'N/A')}

RECOMMENDATION:
{"All documents comply with UCP 600 Art. 18/20 and DHE SDA obligations. Proceed to presentation." if status == "COMPLIANT" else
 "Document set contains discrepancies requiring correction before presentation under UCP 600 Art. 16. "
 "Refer to findings above. DHE SDA violation must be resolved with compliant bank placement before proceeds repatriation."}

[NOTE: USE_MOCK_LLM=true — no IBM watsonx API tokens consumed]
"""
    _MOCK_CACHE[cache_key] = narrative
    return narrative


def _live_synthesis(findings: dict, case_id: str) -> str:
    try:
        from ibm_watsonx_ai import APIClient, Credentials  # type: ignore
        from ibm_watsonx_ai.foundation_models import ModelInference  # type: ignore
    except ImportError:
        raise RuntimeError(
            "ibm-watsonx-ai package is required for live synthesis. "
            "Install with: pip install ibm-watsonx-ai"
        )
    prompt = f"""You are a senior Trade Finance compliance officer and IBM Bob agent.
Analyse the following deterministic compliance findings and produce a concise, factual
compliance synthesis referencing UCP 600 articles, ISBP 745, and Indonesia DHE SDA regulations.
Do NOT invent numbers. Use only the figures provided in the findings JSON.

CASE_ID: {case_id}
FINDINGS:
{json.dumps(findings, indent=2)}

Output format:
1. Executive Summary (2 sentences)
2. Discrepancy Detail (bullet per issue with article reference)
3. DHE SDA Regulatory Assessment
4. Recommended Action
"""
    creds = Credentials(api_key=WATSONX_API_KEY, url=WATSONX_URL)
    client = APIClient(credentials=creds, project_id=WATSONX_PROJECT_ID)
    model = ModelInference(model_id=WATSONX_MODEL, api_client=client,
                           params={"max_new_tokens": 600, "temperature": 0.0})
    return model.generate_text(prompt=prompt)

# ---------------------------------------------------------------------------
# GUARDRAIL 2 — OUTPUT NUMERICAL FAITHFULNESS
# ---------------------------------------------------------------------------

def _guardrail_output(synthesis: str, findings: dict) -> tuple[str, list[str]]:
    warnings: list[str] = []
    price_check = findings["checks"].get("price_deviation", {})
    if price_check:
        dev = str(abs(price_check.get("deviation_pct", 0)))
        if dev != "0.0" and dev not in synthesis:
            warnings.append(f"GUARDRAIL_2: Price deviation {dev}% not found verbatim in synthesis")
    aishu = findings["checks"].get("aishu_proximity", {})
    if aishu and aishu.get("status") == "FAIL":
        dist = str(aishu.get("distance_nm", ""))
        if dist and dist not in synthesis:
            warnings.append(f"GUARDRAIL_2: AISHub distance {dist} NM not found verbatim in synthesis")
    dhe = findings["checks"].get("dhe_sda", {})
    if dhe and dhe.get("status") == "FAIL":
        fx = str(dhe.get("requested_fx_conversion_pct", ""))
        if fx and fx not in synthesis:
            warnings.append(f"GUARDRAIL_2: DHE SDA FX conversion {fx}% not found verbatim in synthesis")
    if warnings:
        synthesis += (
            "\n\n⚠️  GUARDRAIL 2 WARNINGS (numerical faithfulness):\n"
            + "\n".join(f"  • {w}" for w in warnings)
        )
    return synthesis, warnings

# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

def _run_pipeline(case_id: str, dhe_rule_version: str | None = None) -> dict:
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

    if case_id not in cases:
        raise ValueError(f"Unknown case_id '{case_id}'. Available: {list(cases.keys())}")

    case = cases[case_id]
    if dhe_rule_version:
        case = dict(case)
        case["dhe_rule_version"] = dhe_rule_version

    rule_version = case.get("dhe_rule_version", data["_meta"]["active_rule_version"])
    if rule_version not in dhe_rules:
        raise ValueError(f"Unknown DHE rule version '{rule_version}'")

    g1_all_warnings: list[str] = []
    for field in ["goods_description"]:
        _, w = _guardrail_input(case["commercial_invoice"].get(field, ""))
        g1_all_warnings.extend(w)
        _, w2 = _guardrail_input(case["bill_of_lading"].get(field, ""))
        g1_all_warnings.extend(w2)

    lc_ref = lc_refs[case["lc_reference"]]
    imo_key = f"IMO{case['bill_of_lading']['imo_number']}"
    vessel = vessels_db[imo_key]

    port_name = lc_ref["port_of_loading"]
    port_coords = (
        port_coords_db["TANJUNG_PERAK"]
        if ("Perak" in port_name or "Surabaya" in port_name)
        else port_coords_db["TANJUNG_PRIOK"]
    )

    hs = case["commercial_invoice"]["hs_code"]
    benchmark = next(
        (v for v in benchmarks.values() if v["hs_code"] == hs),
        {"benchmark_price": 0, "tolerance_pct": 5, "description": "Unknown", "hs_code": hs},
    )

    findings = _run_deterministic_engine(
        case=case, lc_ref=lc_ref, rules=dhe_rules,
        vessel=vessel, port_coords=port_coords, benchmark=benchmark,
    )

    synthesis = _mock_synthesis(findings, case_id) if USE_MOCK_LLM else _live_synthesis(findings, case_id)
    synthesis, g2_warnings = _guardrail_output(synthesis, findings)
    t_elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)

    return {
        "case_id": case_id,
        "dhe_rule_version_applied": rule_version,
        "overall_status": findings["overall_status"],
        "discrepancy_count": findings["discrepancy_count"],
        "processing_time_ms": t_elapsed_ms,
        "guardrail_1_warnings": g1_all_warnings,
        "guardrail_2_warnings": g2_warnings,
        "findings": findings,
        "synthesis": synthesis,
        "roi_context": {
            "baseline_review_time_s": 2700,
            "sentinel_time_ms": t_elapsed_ms,
            "sentinel_time_s": round(t_elapsed_ms / 1000, 3),
            "time_reduction_pct": round((1 - (t_elapsed_ms / 1000) / 2700) * 100, 2),
        },
    }

# ---------------------------------------------------------------------------
# LANGFLOW COMPONENT
# ---------------------------------------------------------------------------

class TradeFlowSentinelComponent(Component):
    """
    TradeFlow Sentinel — UCP 600 Art.18/20 + SOLAS + AISHub + DHE SDA
    compliance automation for Indonesian commodity export trade finance.

    Inputs
    ------
    case_id           : Synthetic trade case to evaluate.
    dhe_rule_version  : Indonesia DHE SDA regulatory version to apply.

    Output
    ------
    compliance_result : Data containing full findings, synthesis & ROI.
    """

    display_name = "TradeFlow Sentinel"
    description = (
        "Deterministic UCP 600 Art.18/20 cross-check + SOLAS IMO checksum "
        "+ AISHub vessel proximity + World Bank price deviation "
        "+ versioned Indonesia DHE SDA compliance (PADG 16/2026 active)."
    )
    icon = "shield-check"
    name = "TradeFlowSentinel"

    inputs = [
        DropdownInput(
            name="case_id",
            display_name="Case ID",
            options=["CASE_1_COMPLIANT_CPO", "CASE_2_DISCREPANT_COAL"],
            value="CASE_1_COMPLIANT_CPO",
            info=(
                "CASE_1: Compliant CPO export — expects COMPLIANT, 0 violations. "
                "CASE_2: Discrepant Coal export — expects DISCREPANT, 5 violations."
            ),
        ),
        DropdownInput(
            name="dhe_rule_version",
            display_name="DHE SDA Rule Version",
            options=["BASELINE_PRE_2025", "PP_8_2025", "PADG_16_2026"],
            value="PADG_16_2026",
            info=(
                "Active rule: PADG_16_2026 (effective 2026-06-01). "
                "Switch versions for live regulatory comparison demo."
            ),
        ),
    ]

    outputs = [
        Output(
            name="compliance_result",
            display_name="Compliance Result",
            method="run_compliance_check",
        ),
    ]

    def run_compliance_check(self) -> Data:
        result = _run_pipeline(
            case_id=self.case_id,
            dhe_rule_version=self.dhe_rule_version,
        )
        return Data(data=result)
