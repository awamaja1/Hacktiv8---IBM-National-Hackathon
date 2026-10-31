"""
TradeFlow Sentinel — Archived Mock LLM Mode Reference
=====================================================
Archived on: 2026-10-31
Purpose: Reference implementation of zero-cost, MD5-cached deterministic mock synthesis.

When USE_MOCK_LLM=true was enabled in early MVP phases:
1. Findings JSON was hashed via MD5 to generate deterministic cache keys.
2. Executive narratives were constructed using structured template interpolation.
3. Consumed 0 API tokens and executed with 0.5 ms latency.
"""

import hashlib
import json

_MOCK_CACHE: dict[str, str] = {}


def mock_synthesis(findings: dict, case_id: str) -> str:
    """
    Deterministic cached synthesis generator for offline testing.
    """
    cache_key = hashlib.md5(
        json.dumps(findings, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]

    if cache_key in _MOCK_CACHE:
        return _MOCK_CACHE[cache_key]

    status = findings.get("overall_status", "UNKNOWN")
    n_disc = findings.get("discrepancy_count", 0)
    checks = findings.get("checks", {})
    rem_rows = findings.get("remediation_rows", [])

    art18 = checks.get("ucp_art18_invoice", {})
    art20 = checks.get("ucp_art20_bol", {})
    aishu = checks.get("aishu_proximity", {})
    imo = checks.get("imo_solas", {})
    price = checks.get("price_deviation", {})
    dhe = checks.get("dhe_sda", {})

    narrative = f"""[TradeFlow Sentinel — Archived Mock Synthesis Reference | Session: {cache_key[:8]}]

CASE: {case_id}
STATUS: {status}
DISCREPANCIES: {n_disc}

CHECKS:
- UCP 600 Art. 18 (Commercial Invoice): {art18.get('status', 'N/A')}
- UCP 600 Art. 20 (Bill of Lading): {art20.get('status', 'N/A')}
- AISHub Proximity: {aishu.get('status', 'N/A')} ({aishu.get('distance_nm', 'N/A')} NM)
- SOLAS Check Digit: {imo.get('status', 'N/A')} (IMO {imo.get('imo', 'N/A')})
- World Bank Pink Sheet: {price.get('status', 'N/A')} (Deviation: {price.get('deviation_pct', 'N/A')}%)
- DHE SDA ({dhe.get('rule', 'N/A')}): {dhe.get('status', 'N/A')}

REMEDIATION:
{json.dumps(rem_rows, indent=2, ensure_ascii=False) if rem_rows else 'All documents compliant.'}
"""
    _MOCK_CACHE[cache_key] = narrative
    return narrative
