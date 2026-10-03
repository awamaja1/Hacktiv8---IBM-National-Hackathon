"""
TradeFlow Sentinel — Node 3: Compliance Report
===============================================
Receives compliance findings from Node 2 (Compliance Engine),
runs IBM Bob synthesis (mock or live), applies Guardrail 2
(numerical faithfulness), and outputs the final formatted report
with ROI metrics.

Self-contained: no cross-file Python imports.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

from langflow.custom import Component
from langflow.io import HandleInput, Output
from langflow.schema import Data

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "true").lower() != "false"
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_MODEL = os.getenv("WATSONX_MODEL", "ibm/granite-3-3-8b-instruct")


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
    if aishu :
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
# LANGFLOW COMPONENT — NODE 3: Compliance Report
# ---------------------------------------------------------------------------

class ComplianceReportComponent(Component):
    """
    Node 3 — Generates the final compliance report with IBM Bob synthesis,
    Guardrail 2 checks, and ROI metrics.

    Connects: ⬅ Compliance Engine (Node 2)
    """

    display_name = "📊 Compliance Report"
    description = (
        "Generates IBM Bob AI synthesis (mock or live watsonx), "
        "applies Guardrail 2 (numerical faithfulness), and outputs "
        "the final compliance report with ROI metrics. "
        "Connect input ← Compliance Engine."
    )
    icon = "bar-chart-2"
    name = "ComplianceReport"

    inputs = [
        HandleInput(
            name="compliance_findings",
            display_name="Compliance Findings",
            input_types=["Data"],
            info="Connect from Compliance Engine node's 'Compliance Findings' output.",
        ),
    ]

    outputs = [
        Output(
            name="compliance_report",
            display_name="Compliance Report",
            method="generate_report",
        ),
    ]

    def generate_report(self) -> Data:
        t_start = time.perf_counter()

        doc: dict = (
            self.compliance_findings.data
            if hasattr(self.compliance_findings, "data")
            else self.compliance_findings
        )

        if doc.get("case_id") == "JSON_PARSE_ERROR":
            return Data(data=doc)

        case_id = doc["case_id"]
        findings = doc["findings"]
        engine_time_ms = doc.get("processing_time_ms", 0)

        # IBM Bob Synthesis
        synthesis = (
            _mock_synthesis(findings, case_id)
            if USE_MOCK_LLM
            else _live_synthesis(findings, case_id)
        )
        synthesis, g2_warnings = _guardrail_output(synthesis, findings)

        report_time_ms = round((time.perf_counter() - t_start) * 1000, 1)
        total_time_ms = round(engine_time_ms + report_time_ms, 1)

        return Data(data={
            "case_id": case_id,
            "dhe_rule_version_applied": doc["dhe_rule_version"],
            "overall_status": findings["overall_status"],
            "discrepancy_count": findings["discrepancy_count"],
            "processing_time_ms": total_time_ms,
            "guardrail_1_warnings": doc.get("guardrail_1_warnings", []),
            "guardrail_2_warnings": g2_warnings,
            "findings": findings,
            "synthesis": synthesis,
            "roi_context": {
                "baseline_review_time_s": 2700,
                "sentinel_time_ms": total_time_ms,
                "sentinel_time_s": round(total_time_ms / 1000, 3),
                "time_reduction_pct": min(round((1 - (total_time_ms / 1000) / 2700) * 100, 1), 99.9),
            },
        })
