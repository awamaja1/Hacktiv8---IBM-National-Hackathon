import json
import urllib.request

from langflow.custom import Component
from langflow.io import DataInput, MessageTextInput, Output
from langflow.schema.data import Data
from langflow.schema.message import Message


class SentinelComplianceCheckerComponent(Component):
    """Calls TradeFlow Sentinel API or formats existing API Request output into a compliance report."""

    display_name = "⚖️ Sentinel Compliance Checker"
    description = (
        "Parses case parameters from chat or API Request response, "
        "returns full compliance report with UCP 600, DHE SDA, and ROI metrics."
    )
    icon = "shield-check"
    name = "SentinelComplianceChecker"

    inputs = [
        DataInput(
            name="api_data",
            display_name="API Request Data (Optional)",
            required=False,
            info="Hubungkan langsung output 'Data' dari komponen API Request jika tidak ingin memanggil API ulang.",
        ),
    ]

    outputs = [
        Output(display_name="Report", name="report", method="check_compliance"),
    ]

    API_URLS = [
        "http://tradeflow_sentinel_api:8000/verify-trade-documents",
        "http://host.docker.internal:8000/verify-trade-documents",
    ]

    def _parse_input(self, raw: str) -> dict:
        """Parse flexible input into API parameters or already-fetched API result."""
        raw = raw.strip()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                # Jika input adalah JSON response utuh dari node API Request
                if "result" in parsed and isinstance(parsed["result"], dict):
                    return {"_prefetched_result": parsed["result"]}
                # Jika input adalah JSON response langsung dari endpoint
                if "overall_status" in parsed and "findings" in parsed:
                    return {"_prefetched_result": parsed}
                # Jika input adalah JSON parameter request
                if "case_id" in parsed:
                    return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        parts = raw.split()
        return {
            "case_id": parts[0] if parts else "CASE_1_COMPLIANT_CPO",
            "dhe_rule_version": parts[1] if len(parts) > 1 else "PADG_16_2026",
        }

    def _call_api(self, params: dict) -> dict:
        """Call Sentinel FastAPI endpoint with fallback host."""
        payload = json.dumps(params).encode("utf-8")
        last_err = None
        for url in self.API_URLS:
            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                last_err = e
        raise RuntimeError(f"Failed connecting to {self.API_URLS}: {last_err}")

    def _format_report(self, r: dict) -> str:
        """Format API response into readable compliance report."""
        icon = "✅" if r.get("overall_status") == "COMPLIANT" else "❌"
        roi = r.get("roi_context", {})
        time_red = float(roi.get("time_reduction_pct", 0.0))
        baseline_s = int(roi.get("baseline_review_time_s", 2700))
        proc_time = float(r.get("processing_time_ms", 0.0))
        
        # Logika cegah pembulatan 100.0%
        if time_red >= 99.9 and proc_time > 0:
            time_red_display = ">99.9%"
        else:
            time_red_display = f"{time_red:.1f}%"

        lines = [
            "=" * 60,
            f"  {icon} TradeFlow Sentinel — {r.get('case_id', 'UNKNOWN')}",
            "=" * 60,
            f"  Status          : {r.get('overall_status', 'UNKNOWN')}",
            f"  Discrepancies   : {r.get('discrepancy_count', 0)}",
            f"  DHE SDA Rule    : {r.get('dhe_rule_version_applied', '-')}",
            f"  Processing Time : {proc_time} ms",
            f"  Time Reduction  : {time_red_display}", # <-- Variabel teks masuk di sini
            "",
            "--- IBM Bob Synthesis ---",
            r.get("synthesis", "").rstrip() + "\n",
        ]

        findings = r.get("findings", {})
        discrepancies = findings.get("discrepancies", [])
        if discrepancies:
            lines.append("\n--- Discrepancies ---")
            for i, d in enumerate(discrepancies, 1):
                lines.append(f"  [{i}] {d}")

        # Checks summary
        lines.append("\n--- Check Results ---")
        for check_name, check_data in findings.get("checks", {}).items():
            status = check_data.get("status", "?")
            rule = check_data.get("rule", check_name)
            s_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⬜"
            lines.append(f"  {s_icon} {rule}: {status}")

        # ROI
        lines.extend([
            "",
            "--- ROI ---",
            f"  Manual review : {baseline_s:,} seconds ({baseline_s // 60} minutes)",
            f"  Sentinel      : {r.get('processing_time_ms', 0)} ms",
            f"  Reduction     : {time_red_display}",
        ])
        return "\n".join(lines)

    def check_compliance(self) -> Message:
        """Main entry point — parse input or Data, call API if needed, return report."""
        try:
            # 1. Cek apakah ada input dari node API Request (DataInput)
            if self.api_data is not None:
                data_dict = self.api_data.data if isinstance(self.api_data, Data) else self.api_data
                if isinstance(data_dict, dict):
                    result = data_dict.get("result", data_dict)
                    report = self._format_report(result)
                    icon = "✅" if result.get("overall_status") == "COMPLIANT" else "❌"
                    self.status = f"{icon} {result.get('overall_status')} — {result.get('discrepancy_count')} discrepancies"
                    return Message(text=report)

        except Exception as e:
            self.status = f"❌ Error: {e}"
            return Message(
                text=f"❌ Error calling Sentinel API: {e}\n\n"
                f"Troubleshooting:\n"
                f"  1. Pastikan container sentinel berjalan: docker ps\n"
                f"  2. Test: docker exec tradeflow_langflow curl -s http://tradeflow_sentinel_api:8000/health"
            )