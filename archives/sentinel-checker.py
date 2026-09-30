import json
import urllib.request

from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema.message import Message


class SentinelComplianceCheckerComponent(Component):
    """Calls TradeFlow Sentinel API and returns formatted compliance report."""

    display_name = "⚖️ Sentinel Compliance Checker"
    description = (
        "Parses case parameters from chat, calls Sentinel Compliance API, "
        "returns full compliance report with UCP 600, DHE SDA, and ROI metrics."
    )
    icon = "shield-check"
    name = "SentinelComplianceChecker"

    inputs = [
        MessageTextInput(
            name="input_text",
            display_name="Chat Message",
            info=(
                "Accepted formats:\n"
                "  1) JSON: {\"case_id\": \"CASE_1_COMPLIANT_CPO\", \"dhe_rule_version\": \"PADG_16_2026\"}\n"
                "  2) Space-separated: CASE_1_COMPLIANT_CPO PADG_16_2026\n"
                "  3) Case ID only: CASE_1_COMPLIANT_CPO (defaults to PADG_16_2026)"
            ),
        ),
    ]

    outputs = [
        Output(display_name="Report", name="report", method="check_compliance"),
    ]

    API_URL = "http://tradeflow_sentinel_api:8000/verify-trade-documents"

    def _parse_input(self, raw: str) -> dict:
        """Parse flexible input into API parameters."""
        raw = raw.strip()
        # Try JSON first
        try:
            params = json.loads(raw)
            if isinstance(params, dict) and "case_id" in params:
                return params
        except (json.JSONDecodeError, TypeError):
            pass
        # Fall back to space-separated
        parts = raw.split()
        return {
            "case_id": parts[0] if parts else "CASE_1_COMPLIANT_CPO",
            "dhe_rule_version": parts[1] if len(parts) > 1 else "PADG_16_2026",
        }

    def _call_api(self, params: dict) -> dict:
        """Call Sentinel FastAPI endpoint."""
        payload = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(
            self.API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _format_report(self, r: dict) -> str:
        """Format API response into readable compliance report."""
        icon = "✅" if r["overall_status"] == "COMPLIANT" else "❌"
        lines = [
            "=" * 60,
            f"  {icon} TradeFlow Sentinel — {r['case_id']}",
            "=" * 60,
            f"  Status          : {r['overall_status']}",
            f"  Discrepancies   : {r['discrepancy_count']}",
            f"  DHE SDA Rule    : {r['dhe_rule_version_applied']}",
            f"  Processing Time : {r['processing_time_ms']} ms",
            f"  Time Reduction  : {r['roi_context']['time_reduction_pct']}%",
            "",
            "--- IBM Bob Synthesis ---",
            r["synthesis"],
        ]
        if r["findings"]["discrepancies"]:
            lines.append("\n--- Discrepancies ---")
            for i, d in enumerate(r["findings"]["discrepancies"], 1):
                lines.append(f"  [{i}] {d}")
        # Checks summary
        lines.append("\n--- Check Results ---")
        for check_name, check_data in r["findings"]["checks"].items():
            status = check_data.get("status", "?")
            rule = check_data.get("rule", check_name)
            s_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⬜"
            lines.append(f"  {s_icon} {rule}: {status}")
        # ROI
        lines.extend([
            "",
            "--- ROI ---",
            f"  Manual review : 2,700 seconds (45 minutes)",
            f"  Sentinel      : {r['processing_time_ms']} ms",
            f"  Reduction     : {r['roi_context']['time_reduction_pct']}%",
        ])
        return "\n".join(lines)

    def check_compliance(self) -> Message:
        """Main entry point — parse input, call API, return report."""
        raw = self.input_text
        if hasattr(raw, "text"):
            raw = raw.text
        raw = str(raw).strip()

        try:
            params = self._parse_input(raw)
            self.log(f"Calling Sentinel API with: {params}")
            result = self._call_api(params)
            report = self._format_report(result)
            icon = "✅" if result["overall_status"] == "COMPLIANT" else "❌"
            self.status = f"{icon} {result['overall_status']} — {result['discrepancy_count']} discrepancies"
            return Message(text=report)
        except Exception as e:
            self.status = f"❌ Error: {e}"
            return Message(
                text=f"❌ Error calling Sentinel API: {e}\n\n"
                f"Input received: {raw}\n\n"
                f"Troubleshooting:\n"
                f"  1. Pastikan container sentinel berjalan: docker ps\n"
                f"  2. Test: docker exec tradeflow_langflow curl -s http://tradeflow_sentinel_api:8000/health"
            )