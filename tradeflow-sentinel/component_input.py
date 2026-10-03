"""
TradeFlow Sentinel — Node 1: Trade Document Input
==================================================
Loads synthetic trade case data, applies Guardrail 1 (input
sanitisation), and outputs a structured document set for the
Compliance Engine node downstream.

Self-contained: no cross-file Python imports.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from langflow.custom import Component
from langflow.io import DropdownInput, Output, MultilineInput
from langflow.schema import Data

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
DATA_FILE = Path(os.getenv("DATA_FILE", "/app/synthetic_data_and_rules.json"))

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
# LANGFLOW COMPONENT — NODE 1: Trade Document Input
# ---------------------------------------------------------------------------

class TradeDocumentInputComponent(Component):
    """
    Node 1 — Loads a synthetic trade case, applies input guardrails,
    and outputs the parsed document set for downstream compliance checks.

    Connects to: ⮕ Compliance Engine (Node 2)
    """

    display_name = "📄 Trade Document Input"
    description = (
        "Loads trade case data (LC, Invoice, BoL, DHE) and applies "
        "Guardrail 1 (PII masking, injection detection). "
        "Connect output → Compliance Engine node."
    )
    icon = "file-text"
    name = "TradeDocumentInput"

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
        MultilineInput(
            name="live_document_payload",
            display_name="Live Document Payload (JSON)",
            info="Paste raw JSON here to override the dropdown case. Must follow schema.",
            value="",
            advanced=False,
        ),
    ]

    outputs = [
        Output(
            name="document_set",
            display_name="Document Set",
            method="load_documents",
        ),
    ]

    def load_documents(self) -> Data:
        data = _load_data()
        cases = data["cases"]

        case = None
        if getattr(self, "live_document_payload", "").strip():
            try:
                case = json.loads(self.live_document_payload.strip())
            except json.JSONDecodeError as e:
                return Data(data={
                    "case_id": "JSON_PARSE_ERROR",
                    "overall_status": "ERROR - INVALID JSON FORMAT",
                    "discrepancy_count": 1,
                    "dhe_rule_version": "UNKNOWN",
                    "processing_time_ms": 0.0,
                    "roi_context": {
                        "baseline_review_time_s": 2700,
                        "sentinel_time_ms": 0.0,
                        "sentinel_time_s": 0.0,
                        "time_reduction_pct": 0.0
                    },
                    "llm_prompt_context": "Sistem gagal mengekstrak data karena format JSON cacat (JSONDecodeError). Beritahu user bahwa ada kesalahan sintaksis seperti koma atau tanda kutip yang hilang pada payload.",
                    "check_results": {
                        "JSON_Validation": {
                            "status": "FAIL",
                            "message": "Terdeteksi kesalahan format pada input JSON (missing comma, trailing quote, dll)."
                        }
                    },
                    "discrepancy_notes": [
                        "FATAL ERROR: Format JSON yang dimasukkan tidak valid. Harap periksa kembali sintaksis payload."
                    ]
                })
        
        if case is None:
            if self.case_id not in cases:
                raise ValueError(
                    f"Unknown case_id '{self.case_id}'. "
                    f"Available: {list(cases.keys())}"
                )
            case = cases[self.case_id]
        
        dhe_rule_version = getattr(self, "dhe_rule_version", None) or data["_meta"]["active_rule_version"]

        # Apply Guardrail 1
        g1_warnings: list[str] = []
        for field in ["goods_description"]:
            _, w = _guardrail_input(case["commercial_invoice"].get(field, ""))
            g1_warnings.extend(w)
            _, w2 = _guardrail_input(case["bill_of_lading"].get(field, ""))
            g1_warnings.extend(w2)

        # Resolve references
        lc_ref = data["lc_mt700_reference"][case["lc_reference"]]
        imo_key = f"IMO{case['bill_of_lading']['imo_number']}"
        vessel = data["aishu_vessel_snapshots"]["vessels"][imo_key]

        port_name = lc_ref["port_of_loading"]
        port_coords_db = {
            "TANJUNG_PERAK": data["aishu_vessel_snapshots"]["TANJUNG_PERAK_COORDS"],
            "TANJUNG_PRIOK": data["aishu_vessel_snapshots"]["TANJUNG_PRIOK_COORDS"],
        }
        port_coords = (
            port_coords_db["TANJUNG_PERAK"]
            if ("Perak" in port_name or "Surabaya" in port_name)
            else port_coords_db["TANJUNG_PRIOK"]
        )

        hs = case["commercial_invoice"]["hs_code"]
        benchmarks = data["world_bank_pink_sheet_benchmarks"]["commodities"]
        benchmark = next(
            (v for v in benchmarks.values() if v["hs_code"] == hs),
            {"benchmark_price": 0, "tolerance_pct": 5, "description": "Unknown", "hs_code": hs},
        )

        dhe_rules = data["dhe_sda_versions"]
        if dhe_rule_version not in dhe_rules:
            raise ValueError(f"Unknown DHE rule version '{dhe_rule_version}'")

        return Data(data={
            "case_id": self.case_id,
            "dhe_rule_version": dhe_rule_version,
            "case": case,
            "lc_ref": lc_ref,
            "vessel": vessel,
            "port_coords": port_coords,
            "benchmark": benchmark,
            "dhe_rules": dhe_rules,
            "guardrail_1_warnings": g1_warnings,
        })
