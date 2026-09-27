"""
TradeFlow Sentinel — Langflow Custom Component (standalone)
============================================================
This is the ONLY file Langflow loads from LANGFLOW_COMPONENTS_PATH.
All compliance logic lives in langflow_sentinel_engine.py, which
this file imports lazily inside the method body.

Import rules enforced by this file:
- Only langflow.* symbols at module level (the validator requires this).
- langflow_sentinel_engine is imported lazily inside run_compliance_check()
  so the validator exec() never needs to resolve it.
"""

import sys
from pathlib import Path

# Make the engine importable. It lives in the deactivated/ subdirectory so
# Langflow's component scanner skips it. We add that path to sys.path here.
_HERE = Path(__file__).parent
_DEACTIVATED = _HERE / "deactivated"
for _p in (_DEACTIVATED, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from langflow.custom import Component       # noqa: E402  (validator injects this)
from langflow.io import DropdownInput, Output  # noqa: E402
from langflow.schema import Data            # noqa: E402


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
        from _sentinel_engine import run_pipeline  # lazy import — underscore file skipped by Langflow scanner
        result = run_pipeline(
            case_id=self.case_id,
            dhe_rule_version=self.dhe_rule_version,
        )
        return Data(data=result)
