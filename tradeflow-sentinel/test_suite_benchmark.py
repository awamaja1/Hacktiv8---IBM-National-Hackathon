"""
TradeFlow Sentinel — 40-Case Benchmark Suite
=============================================
Executable benchmark that generates and evaluates 40 diverse trade document
presentations with planted discrepancies, computes a confusion matrix, recall,
precision, F1, false-alarm rate, mean claim faithfulness, and execution time.

Usage:
    python test_suite_benchmark.py                  # run all 40 cases
    python test_suite_benchmark.py --json           # output JSON results
    python test_suite_benchmark.py --case-id C01    # run one case

Requires:
    pip install tabulate   (optional, for pretty table output)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Allow importing engine from same directory
sys.path.insert(0, str(Path(__file__).parent))
from langflow_sentinel_engine import run_pipeline, ANALYST_BASELINE_SEC  # noqa: E402

# ===========================================================================
# SHARED LC / VESSEL HELPERS
# ===========================================================================

def _cpo_lc(amount=1820000, tol=5, lsd="2026-07-15") -> dict:
    return {
        "beneficiary": "PT SUMATRA AGRO INDUSTRIES",
        "applicant": "ASIA PACIFIC TRADING SDN BHD",
        "currency": "USD",
        "amount": amount,
        "tolerance_pct": tol,
        "incoterms": "FOB",
        "port_of_loading": "Tanjung Perak, Surabaya",
        "port_of_discharge": "Port Klang, Malaysia",
        "latest_shipment_date": lsd,
    }

def _coal_lc(amount=5250000, tol=5, lsd="2026-09-30", pol="Tanjung Priok, Jakarta",
             pod="Qingdao, China") -> dict:
    return {
        "beneficiary": "PT KALIMANTAN COAL EXPORT",
        "applicant": "SHANGHAI ENERGY IMPORTS CO. LTD",
        "currency": "USD",
        "amount": amount,
        "tolerance_pct": tol,
        "incoterms": "FOB",
        "port_of_loading": pol,
        "port_of_discharge": pod,
        "latest_shipment_date": lsd,
    }

def _nickel_lc(amount=16500000, tol=5, lsd="2026-10-05") -> dict:
    return {
        "beneficiary": "PT SULAWESI MINERAL EXPORT",
        "applicant": "KOREA METALS CORP",
        "currency": "USD",
        "amount": amount,
        "tolerance_pct": tol,
        "incoterms": "FOB",
        "port_of_loading": "Tanjung Priok, Jakarta",
        "port_of_discharge": "Busan, South Korea",
        "latest_shipment_date": lsd,
    }

def _rubber_lc(amount=1750000, tol=5, lsd="2026-07-15") -> dict:
    return {
        "beneficiary": "PT SUMATRA RUBBER CO",
        "applicant": "CONTINENTAL AG",
        "currency": "USD",
        "amount": amount,
        "tolerance_pct": tol,
        "incoterms": "FOB",
        "port_of_loading": "Tanjung Perak, Surabaya",
        "port_of_discharge": "Hamburg, Germany",
        "latest_shipment_date": lsd,
    }

def _cpo_inv(unit_price=910, total=1820000, seller="PT SUMATRA AGRO INDUSTRIES",
             buyer="ASIA PACIFIC TRADING SDN BHD", currency="USD",
             incoterms="FOB") -> dict:
    return {
        "seller": seller, "buyer": buyer, "currency": currency,
        "hs_code": "1511.10", "goods_description": "CRUDE PALM OIL (CPO)",
        "quantity_mt": 2000, "unit_price_usd_mt": unit_price,
        "total_fob_usd": total, "incoterms": incoterms,
        "port_of_loading": "Tanjung Perak, Surabaya",
    }

def _coal_inv(unit_price=72, total=3600000, seller="PT KALIMANTAN COAL EXPORT",
              buyer="SHANGHAI ENERGY IMPORTS CO. LTD", currency="USD",
              incoterms="FOB", hs="2701.12", pol="Tanjung Priok, Jakarta") -> dict:
    return {
        "seller": seller, "buyer": buyer, "currency": currency,
        "hs_code": hs, "goods_description": "THERMAL COAL",
        "quantity_mt": 50000, "unit_price_usd_mt": unit_price,
        "total_fob_usd": total, "incoterms": incoterms,
        "port_of_loading": pol,
    }

def _nickel_inv(unit_price=16500, total=16500000) -> dict:
    return {
        "seller": "PT SULAWESI MINERAL EXPORT",
        "buyer": "KOREA METALS CORP",
        "currency": "USD",
        "hs_code": "7501.20",
        "goods_description": "NICKEL MATTE CLASS 1",
        "quantity_mt": 1000,
        "unit_price_usd_mt": unit_price,
        "total_fob_usd": total,
        "incoterms": "FOB",
        "port_of_loading": "Tanjung Priok, Jakarta",
    }

def _rubber_inv(unit_price=1750, total=1750000) -> dict:
    return {
        "seller": "PT SUMATRA RUBBER CO",
        "buyer": "CONTINENTAL AG",
        "currency": "USD",
        "hs_code": "4001.22",
        "goods_description": "NATURAL RUBBER SIR-20",
        "quantity_mt": 1000,
        "unit_price_usd_mt": unit_price,
        "total_fob_usd": total,
        "incoterms": "FOB",
        "port_of_loading": "Tanjung Perak, Surabaya",
    }

def _cpo_bol(imo="9315460", onboard="2026-07-10", pol="Tanjung Perak, Surabaya",
             pod="Port Klang, Malaysia") -> dict:
    return {
        "vessel_name": "MV BORNEO STAR", "imo_number": imo,
        "port_of_loading": pol, "port_of_discharge": pod,
        "on_board_date": onboard, "goods_description": "CRUDE PALM OIL (CPO)",
    }

def _coal_bol(imo="9811000", onboard="2026-09-30",
              pol="Tanjung Priok, Jakarta", pod="Qingdao, China") -> dict:
    return {
        "vessel_name": "MV KALIMANTAN BULK", "imo_number": imo,
        "port_of_loading": pol, "port_of_discharge": pod,
        "on_board_date": onboard, "goods_description": "THERMAL COAL",
    }

def _nickel_bol(imo="9811000", onboard="2026-09-30",
                pol="Tanjung Priok, Jakarta", pod="Busan, South Korea") -> dict:
    return {
        "vessel_name": "MV KALIMANTAN BULK", "imo_number": imo,
        "port_of_loading": pol, "port_of_discharge": pod,
        "on_board_date": onboard, "goods_description": "NICKEL MATTE",
    }

def _rubber_bol(imo="9315460", onboard="2026-07-10",
                pol="Tanjung Perak, Surabaya", pod="Hamburg, Germany") -> dict:
    return {
        "vessel_name": "MV BORNEO STAR", "imo_number": imo,
        "port_of_loading": pol, "port_of_discharge": pod,
        "on_board_date": onboard, "goods_description": "NATURAL RUBBER",
    }

def _himbara_dhe(fob=1820000, bank="PT Bank Mandiri (Persero) Tbk",
                 cat="HIMBARA", fx=40, hold=12) -> dict:
    return {
        "fob_usd": fob, "nominated_bank": bank, "bank_category": cat,
        "placement_type": "Reksus DHE SDA",
        "requested_fx_conversion_pct": fx, "hold_period_months": hold,
    }

def _private_dhe(fob=5250000, bank="PT Bank CIMB Niaga Tbk",
                 cat="PRIVATE_BANK", fx=80, hold=12) -> dict:
    return {
        "fob_usd": fob, "nominated_bank": bank, "bank_category": cat,
        "placement_type": "Regular FX Account",
        "requested_fx_conversion_pct": fx, "hold_period_months": hold,
    }

# ===========================================================================
# TEST SUITE BUILDER — 40 PLANTED CASES
# ===========================================================================

def build_test_suite() -> list[dict]:
    """
    Return the full list of 40 test case dicts, each with:
      case_id, ground_truth, category, description, document_data, dhe_rule_version
    """
    cases: list[dict] = []

    def add(case_id, ground_truth, category, description, doc_data, rule="PADG_16_2026"):
        cases.append({
            "case_id": case_id,
            "ground_truth": ground_truth,   # "COMPLIANT" or "NON_COMPLIANT"
            "category": category,
            "description": description,
            "document_data": doc_data,
            "dhe_rule_version": rule,
        })

    # ── 12 CLEAN COMPLIANT CASES ──────────────────────────────────────────
    # C01 — baseline CPO compliant
    add("C01", "COMPLIANT", "CLEAN_COMPLIANT",
        "Baseline CPO compliant — all 6 checks PASS",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(), "dhe_sda_transaction": _himbara_dhe()})

    # C02 — EDGE CASE #1: bank_category = "HIMBARA" all-caps (Bug Fix #1 regression)
    add("C02", "COMPLIANT", "CLEAN_COMPLIANT",
        "Edge Case #1: bank_category='HIMBARA' all-caps must PASS Himbara check",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe(cat="HIMBARA")})

    # C03 — bank_category = "himbara" all-lowercase
    add("C03", "COMPLIANT", "CLEAN_COMPLIANT",
        "bank_category='himbara' lowercase must PASS case-insensitive check",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe(cat="himbara")})

    # C04 — nominated_bank contains "Mandiri" (name-based Himbara detection)
    add("C04", "COMPLIANT", "CLEAN_COMPLIANT",
        "nominated_bank='Bank Mandiri' with bank_category='STATE_OWNED' must PASS",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe(
             cat="STATE_OWNED", bank="PT Bank Mandiri (Persero) Tbk")})

    # C05 — Thermal Coal compliant, 45% FX (< 50% cap), Mandiri Reksus
    add("C05", "COMPLIANT", "CLEAN_COMPLIANT",
        "Thermal Coal compliant — on-board 2026-09-30 (at port), 45% FX",
        {"lc_mt700_reference": _coal_lc(amount=3600000, lsd="2026-10-01"),
         "commercial_invoice": _coal_inv(unit_price=72, total=3600000),
         "bill_of_lading": _coal_bol(onboard="2026-09-30"),
         "dhe_sda_transaction": _himbara_dhe(
             fob=3600000, bank="PT Bank Mandiri (Persero) Tbk", cat="HIMBARA", fx=45)})

    # C06 — Nickel compliant
    add("C06", "COMPLIANT", "CLEAN_COMPLIANT",
        "Nickel Matte compliant — MV Sulawesi Nickel at Morowali Terminal",
        {"lc_mt700_reference": _nickel_lc(), "commercial_invoice": _nickel_inv(),
         "bill_of_lading": _nickel_bol(),
         "dhe_sda_transaction": _himbara_dhe(fob=16500000, fx=30)})

    # C07 — Natural Rubber compliant
    add("C07", "COMPLIANT", "CLEAN_COMPLIANT",
        "Natural Rubber compliant — SIR-20 at benchmark price",
        {"lc_mt700_reference": _rubber_lc(), "commercial_invoice": _rubber_inv(),
         "bill_of_lading": _rubber_bol(),
         "dhe_sda_transaction": _himbara_dhe(fob=1750000, fx=35)})

    # C08 — CPO compliant, PP_8_2025 rule (no Himbara restriction)
    add("C08", "COMPLIANT", "CLEAN_COMPLIANT",
        "CPO compliant under PP_8_2025 — any Bank Devisa, 100% FX allowed",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _private_dhe(
             fob=1820000, bank="PT Bank CIMB Niaga Tbk", cat="PRIVATE_BANK",
             fx=70, hold=12)},
        rule="PP_8_2025")

    # C09 — CPO compliant, BASELINE_PRE_2025 (30% retention, 3 months, any bank)
    add("C09", "COMPLIANT", "CLEAN_COMPLIANT",
        "CPO compliant under BASELINE_PRE_2025 — 3-month hold, any bank",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe(fob=1820000, fx=80, hold=3)},
        rule="BASELINE_PRE_2025")

    # C10 — nominated_bank "BRI" triggers Himbara detection
    add("C10", "COMPLIANT", "CLEAN_COMPLIANT",
        "nominated_bank contains 'BRI' — Himbara detection via name substring",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe(
             cat="BUMN", bank="PT Bank Rakyat Indonesia (BRI)")})

    # C11 — CPO compliant, tolerance boundary: invoice within ±5% of LC
    add("C11", "COMPLIANT", "CLEAN_COMPLIANT",
        "CPO amount within ±5% tolerance boundary (invoice = 1.04 × LC amount)",
        {"lc_mt700_reference": _cpo_lc(amount=1750000, tol=5),
         "commercial_invoice": _cpo_inv(total=1820000),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe()})

    # C12 — Rubber compliant with BNI
    add("C12", "COMPLIANT", "CLEAN_COMPLIANT",
        "Natural Rubber compliant — BNI nominated bank",
        {"lc_mt700_reference": _rubber_lc(), "commercial_invoice": _rubber_inv(),
         "bill_of_lading": _rubber_bol(),
         "dhe_sda_transaction": _himbara_dhe(
             fob=1750000, bank="PT Bank Negara Indonesia (BNI)", cat="HIMBARA", fx=25)})

    # ── 5 UCP 600 ART. 18 COMMERCIAL INVOICE DISCREPANCIES ──────────────
    # D01 — FOB amount exceeds ±10% tolerance
    add("D01", "NON_COMPLIANT", "ART18_INVOICE",
        "FOB amount USD 6,000,000 exceeds LC USD 5,250,000 ± 5% tolerance",
        {"lc_mt700_reference": _coal_lc(amount=5250000),
         "commercial_invoice": _coal_inv(unit_price=120, total=6000000),
         "bill_of_lading": _coal_bol(onboard="2026-09-30"),
         "dhe_sda_transaction": _himbara_dhe(fob=6000000, fx=30)})

    # D02 — currency mismatch EUR vs USD
    add("D02", "NON_COMPLIANT", "ART18_INVOICE",
        "Currency mismatch: invoice EUR ≠ LC USD (UCP 600 Art. 18(a)(iii))",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(currency="EUR"),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe()})

    # D03 — seller/beneficiary name mismatch
    add("D03", "NON_COMPLIANT", "ART18_INVOICE",
        "Seller 'PT AGRO NUSANTARA' ≠ LC beneficiary 'PT SUMATRA AGRO INDUSTRIES'",
        {"lc_mt700_reference": _cpo_lc(),
         "commercial_invoice": _cpo_inv(seller="PT AGRO NUSANTARA"),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe()})

    # D04 — incoterms mismatch CIF vs FOB
    add("D04", "NON_COMPLIANT", "ART18_INVOICE",
        "Incoterms mismatch: invoice CIF ≠ LC FOB (UCP 600 Art. 18)",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(incoterms="CIF"),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe()})

    # D05 — buyer/applicant name mismatch
    add("D05", "NON_COMPLIANT", "ART18_INVOICE",
        "Buyer 'GLOBAL TRADING PTE LTD' ≠ LC applicant 'ASIA PACIFIC TRADING SDN BHD'",
        {"lc_mt700_reference": _cpo_lc(),
         "commercial_invoice": _cpo_inv(buyer="GLOBAL TRADING PTE LTD"),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe()})

    # ── 6 UCP 600 ART. 20 BoL & MARITIME DISCREPANCIES ──────────────────
    # D06 — late shipment: on_board_date > latest_shipment_date
    add("D06", "NON_COMPLIANT", "ART20_BOL",
        "Late shipment: on-board 2026-07-20 > LC latest shipment 2026-07-15",
        {"lc_mt700_reference": _cpo_lc(lsd="2026-07-15"),
         "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(onboard="2026-07-20"),
         "dhe_sda_transaction": _himbara_dhe()})

    # D07 — wrong port of loading
    add("D07", "NON_COMPLIANT", "ART20_BOL",
        "Port of loading mismatch: BoL 'Tanjung Priok' ≠ LC 'Tanjung Perak'",
        {"lc_mt700_reference": _cpo_lc(),
         "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(pol="Tanjung Priok, Jakarta"),
         "dhe_sda_transaction": _himbara_dhe()})

    # D08 — wrong port of discharge
    add("D08", "NON_COMPLIANT", "ART20_BOL",
        "Port of discharge mismatch: BoL 'Singapore' ≠ LC 'Port Klang, Malaysia'",
        {"lc_mt700_reference": _cpo_lc(),
         "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(pod="Singapore"),
         "dhe_sda_transaction": _himbara_dhe()})

    # D09 — PREDATED BoL: MV Kalimantan Bulk 209.97 NM away on 2026-09-28
    add("D09", "NON_COMPLIANT", "ART20_BOL",
        "PREDATED BoL: MV Kalimantan Bulk 209.97 NM from Tanjung Priok on 2026-09-28",
        {"lc_mt700_reference": _coal_lc(lsd="2026-09-29"),
         "commercial_invoice": _coal_inv(unit_price=72, total=3600000),
         "bill_of_lading": _coal_bol(onboard="2026-09-28"),
         "dhe_sda_transaction": _himbara_dhe(fob=3600000, fx=30)})

    # D10 — late shipment + wrong POL (double Art. 20 violation)
    add("D10", "NON_COMPLIANT", "ART20_BOL",
        "Double Art. 20 violation: late shipment + wrong port of loading",
        {"lc_mt700_reference": _coal_lc(lsd="2026-09-25"),
         "commercial_invoice": _coal_inv(unit_price=72, total=3600000),
         "bill_of_lading": _coal_bol(onboard="2026-09-30",
                                      pol="Tanjung Perak, Surabaya"),
         "dhe_sda_transaction": _himbara_dhe(fob=3600000, fx=30)})

    # D11 — both late shipment AND predated BoL scenario
    add("D11", "NON_COMPLIANT", "ART20_BOL",
        "MV Kalimantan Bulk on-board 2026-09-28 — vessel at sea 209.97 NM AND after LC expiry",
        {"lc_mt700_reference": _coal_lc(lsd="2026-09-20"),
         "commercial_invoice": _coal_inv(unit_price=72, total=3600000),
         "bill_of_lading": _coal_bol(onboard="2026-09-28"),
         "dhe_sda_transaction": _himbara_dhe(fob=3600000, fx=30)})

    # ── 4 SOLAS IMO CHECKSUM FAILURES ────────────────────────────────────
    # D12 — IMO 9315461 wrong check digit (should be 9315460 → check=0, not 1)
    add("D12", "NON_COMPLIANT", "SOLAS_IMO",
        "SOLAS checksum FAIL: IMO 9315461 (check digit should be 0, not 1)",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(imo="9315461"),
         "dhe_sda_transaction": _himbara_dhe()})

    # D13 — IMO 9811001 wrong check digit
    add("D13", "NON_COMPLIANT", "SOLAS_IMO",
        "SOLAS checksum FAIL: IMO 9811001 wrong check digit",
        {"lc_mt700_reference": _coal_lc(lsd="2026-09-30"),
         "commercial_invoice": _coal_inv(unit_price=72, total=3600000),
         "bill_of_lading": _coal_bol(imo="9811001", onboard="2026-09-30"),
         "dhe_sda_transaction": _himbara_dhe(fob=3600000, fx=30)})

    # D14 — IMO 1234568 wrong check digit
    add("D14", "NON_COMPLIANT", "SOLAS_IMO",
        "SOLAS checksum FAIL: IMO 1234568",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": {**_cpo_bol(), "imo_number": "1234568"},
         "dhe_sda_transaction": _himbara_dhe()})

    # D15 — IMO 9999991 wrong check digit (7-digit but fails checksum)
    add("D15", "NON_COMPLIANT", "SOLAS_IMO",
        "SOLAS checksum FAIL: IMO 9999991",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": {**_cpo_bol(), "imo_number": "9999991"},
         "dhe_sda_transaction": _himbara_dhe()})

    # ── 4 WORLD BANK PRICE DEVIATION FAILURES ────────────────────────────
    # D16 — coal over-invoiced +45.83% (canonical CASE_2 scenario)
    add("D16", "NON_COMPLIANT", "PRICE_DEVIATION",
        "Coal over-invoiced: $105/MT vs benchmark $72/MT = +45.83% (> ±10%)",
        {"lc_mt700_reference": _coal_lc(amount=5250000, lsd="2026-09-30"),
         "commercial_invoice": _coal_inv(unit_price=105, total=5250000),
         "bill_of_lading": _coal_bol(onboard="2026-09-30"),
         "dhe_sda_transaction": _himbara_dhe(fob=5250000, fx=30)})

    # D17 — coal under-invoiced −25.0%
    add("D17", "NON_COMPLIANT", "PRICE_DEVIATION",
        "Coal under-invoiced: $54/MT vs benchmark $72/MT = -25.0% (> ±10%)",
        {"lc_mt700_reference": _coal_lc(amount=2700000, lsd="2026-09-30"),
         "commercial_invoice": _coal_inv(unit_price=54, total=2700000),
         "bill_of_lading": _coal_bol(onboard="2026-09-30"),
         "dhe_sda_transaction": _himbara_dhe(fob=2700000, fx=30)})

    # D18 — CPO over-invoiced +20%
    add("D18", "NON_COMPLIANT", "PRICE_DEVIATION",
        "CPO over-invoiced: $1092/MT vs benchmark $910/MT = +20.0% (> ±5%)",
        {"lc_mt700_reference": _cpo_lc(amount=2184000),
         "commercial_invoice": _cpo_inv(unit_price=1092, total=2184000),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe(fob=2184000, fx=30)})

    # D19 — Nickel over-invoiced +15%
    add("D19", "NON_COMPLIANT", "PRICE_DEVIATION",
        "Nickel over-invoiced: $18975/MT vs $16500/MT = +15.0% (> ±8%)",
        {"lc_mt700_reference": _nickel_lc(amount=18975000),
         "commercial_invoice": _nickel_inv(unit_price=18975, total=18975000),
         "bill_of_lading": _nickel_bol(),
         "dhe_sda_transaction": _himbara_dhe(fob=18975000, fx=30)})

    # ── 6 DHE SDA VIOLATIONS ─────────────────────────────────────────────
    # D20 — private bank PADG_16_2026
    add("D20", "NON_COMPLIANT", "DHE_SDA",
        "PADG_16_2026: private bank PT CIMB Niaga (not Himbara)",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _private_dhe(fob=1820000, fx=30)})

    # D21 — regular FX account instead of Reksus
    add("D21", "NON_COMPLIANT", "DHE_SDA",
        "PADG_16_2026: placement_type 'Regular FX Account' — Reksus required",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": {
             "fob_usd": 1820000, "nominated_bank": "PT Bank Mandiri (Persero) Tbk",
             "bank_category": "HIMBARA", "placement_type": "Regular FX Account",
             "requested_fx_conversion_pct": 40, "hold_period_months": 12}})

    # D22 — FX conversion 80% > 50% cap (PADG_16_2026)
    add("D22", "NON_COMPLIANT", "DHE_SDA",
        "PADG_16_2026: requested FX conversion 80% > 50% cap",
        {"lc_mt700_reference": _coal_lc(amount=5250000, lsd="2026-09-30"),
         "commercial_invoice": _coal_inv(unit_price=105, total=5250000),
         "bill_of_lading": _coal_bol(onboard="2026-09-30"),
         "dhe_sda_transaction": {
             "fob_usd": 5250000, "nominated_bank": "PT Bank Mandiri (Persero) Tbk",
             "bank_category": "HIMBARA", "placement_type": "Reksus DHE SDA",
             "requested_fx_conversion_pct": 80, "hold_period_months": 12}})

    # D23 — hold period 6 months < 12 months minimum (PADG_16_2026)
    add("D23", "NON_COMPLIANT", "DHE_SDA",
        "PADG_16_2026: hold period 6 months < 12 months minimum",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe(hold=6)})

    # D24 — hold period 3 months (violates PP_8_2025 which requires 12 months)
    add("D24", "NON_COMPLIANT", "DHE_SDA",
        "PP_8_2025: hold period 3 months < 12 months minimum",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe(hold=3)},
        rule="PP_8_2025")

    # D25 — FX 101% > 100% (PP_8_2025 — technically exceeds even the 100% cap)
    add("D25", "NON_COMPLIANT", "DHE_SDA",
        "PP_8_2025: FX conversion 101% > 100% maximum",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe(fx=101, hold=12)},
        rule="PP_8_2025")

    # ── 3 MENTOR TECHNICAL EDGE CASES ─────────────────────────────────────
    # E01 — EDGE CASE #2: Unknown IMO 9999997 — KeyError guard (fail-closed)
    add("E01", "NON_COMPLIANT", "EDGE_CASE_UNKNOWN_IMO",
        "Edge Case #2: IMO 9999997 not in vessel DB — must FAIL-CLOSED (no KeyError)",
        {"lc_mt700_reference": _cpo_lc(), "commercial_invoice": _cpo_inv(),
         "bill_of_lading": {**_cpo_bol(), "imo_number": "9999997"},
         "dhe_sda_transaction": _himbara_dhe()})

    # E02 — EDGE CASE #3: Unknown HS code 9999.99 — ZeroDivisionError guard
    add("E02", "NON_COMPLIANT", "EDGE_CASE_UNKNOWN_HS",
        "Edge Case #3: HS Code 9999.99 has no benchmark — must FAIL-CLOSED (no ZeroDivisionError)",
        {"lc_mt700_reference": _cpo_lc(),
         "commercial_invoice": {**_cpo_inv(), "hs_code": "9999.99"},
         "bill_of_lading": _cpo_bol(),
         "dhe_sda_transaction": _himbara_dhe()})

    # E03 — EDGE CASE #4: Dark vessel (lat=None, lon=None) — fail-closed guard
    # Use CPO case with MV SUMATRA RUBBER — other checks pass cleanly.
    add("E03", "NON_COMPLIANT", "EDGE_CASE_DARK_VESSEL",
        "Edge Case #4: IMO 9200005 lat/lon=None — AISHub FAIL-CLOSED, no 0.0 NM default",
        {"lc_mt700_reference": _cpo_lc(),
         "commercial_invoice": _cpo_inv(),
         "bill_of_lading": {**_cpo_bol(), "imo_number": "9200005",
                            "vessel_name": "MV SUMATRA RUBBER"},
         "dhe_sda_transaction": _himbara_dhe()})


    assert len(cases) == 40, f"Expected 40 test cases, got {len(cases)}"
    return cases


# ===========================================================================
# BENCHMARK RUNNER
# ===========================================================================

def run_benchmark(cases: list[dict] | None = None, verbose: bool = True) -> dict:
    """
    Run all test cases, compute confusion matrix and metrics.
    Returns a comprehensive results dict.
    """
    if cases is None:
        cases = build_test_suite()

    results: list[dict] = []
    tp = tn = fp = fn = 0
    faithfulness_scores: list[float] = []
    exec_times_ms: list[float] = []

    for tc in cases:
        t0 = time.perf_counter()
        try:
            r = run_pipeline(
                case_id=tc["case_id"],
                dhe_rule_version=tc["dhe_rule_version"],
                document_data=tc["document_data"],
            )
            predicted = r["overall_status"]          # "COMPLIANT" or "DISCREPANT"
            actual_discrepancies = r["discrepancy_count"]
            g2_warnings = r.get("guardrail_2_warnings", [])
            cf = r.get("claim_faithfulness", {})
            cf_score = cf.get("claim_faithfulness_score")
            if cf_score is not None:
                faithfulness_scores.append(cf_score)
            exec_ms = r["processing_time_ms"]
            exec_times_ms.append(exec_ms)
            error = None
        except Exception as exc:
            predicted = "ERROR"
            actual_discrepancies = -1
            g2_warnings = []
            cf_score = None
            exec_ms = round((time.perf_counter() - t0) * 1000, 2)
            exec_times_ms.append(exec_ms)
            error = str(exc)

        gt = tc["ground_truth"]
        # gt "COMPLIANT" = negative class; gt "NON_COMPLIANT" = positive class
        if gt == "NON_COMPLIANT" and predicted == "DISCREPANT":
            verdict = "TP"
            tp += 1
        elif gt == "COMPLIANT" and predicted == "COMPLIANT":
            verdict = "TN"
            tn += 1
        elif gt == "COMPLIANT" and predicted == "DISCREPANT":
            verdict = "FP"   # False Alarm
            fp += 1
        elif gt == "NON_COMPLIANT" and (predicted == "COMPLIANT" or predicted == "ERROR"):
            verdict = "FN"
            fn += 1
        else:
            verdict = f"ERROR({predicted})"

        results.append({
            "case_id": tc["case_id"],
            "category": tc.get("category", ""),
            "description": tc.get("description", ""),
            "ground_truth": gt,
            "predicted": predicted,
            "verdict": verdict,
            "discrepancy_count": actual_discrepancies,
            "exec_ms": exec_ms,
            "g2_warnings": len(g2_warnings),
            "claim_faithfulness_score": cf_score,
            "error": error,
        })

    # Metrics
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    mean_exec = sum(exec_times_ms) / len(exec_times_ms) if exec_times_ms else 0.0
    mean_faith = (sum(faithfulness_scores) / len(faithfulness_scores)
                  if faithfulness_scores else None)
    time_reduction = min(
        round((1 - (mean_exec / 1000.0) / max(ANALYST_BASELINE_SEC, 1)) * 100.0, 1),
        99.9
    )

    summary = {
        "total_cases": len(cases),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "recall_discrepancy": round(recall, 4),
        "precision": round(precision, 4),
        "f1_score": round(f1, 4),
        "false_alarm_rate_fpr": round(fpr, 4),
        "mean_exec_ms": round(mean_exec, 2),
        "measured_analyst_baseline_sec": ANALYST_BASELINE_SEC,
        "mean_time_reduction_pct": time_reduction,
        "mean_claim_faithfulness_score": round(mean_faith, 1) if mean_faith is not None else None,
    }

    if verbose:
        _print_results(results, summary)

    return {"summary": summary, "results": results}


def _print_results(results: list[dict], summary: dict) -> None:
    sep = "=" * 120
    print(f"\n{sep}")
    print("  TradeFlow Sentinel — 40-Case Benchmark Suite")
    print(sep)

    # Per-case table
    hdr = f"  {'ID':<6} {'Cat':<22} {'GT':<14} {'Pred':<12} {'Verdict':<6} {'Disc':>4} {'ms':>6} {'G2':>3}"
    print(hdr)
    print("  " + "-" * 115)
    for r in results:
        icon = {"TP": "OK", "TN": "OK", "FP": "FA", "FN": "MS"}.get(r["verdict"], "??")
        print(
            f"  {r['case_id']:<6} {r['category']:<22} {r['ground_truth']:<14} "
            f"{r['predicted']:<12} {icon} {r['verdict']:<4} "
            f"{r['discrepancy_count']:>4} {r['exec_ms']:>6.1f}  G2:{r['g2_warnings']}"
        )
        if r.get("error"):
            print(f"         ERROR: {r['error'][:100]}")

    print(f"\n{sep}")
    print("  CONFUSION MATRIX & BENCHMARK METRICS")
    print(sep)
    print(f"  True  Positives (TP — correctly flagged discrepancies): {summary['tp']}")
    print(f"  True  Negatives (TN — correctly passed compliant cases): {summary['tn']}")
    print(f"  False Positives (FP — false alarms on compliant cases):  {summary['fp']}")
    print(f"  False Negatives (FN — missed discrepancies):             {summary['fn']}")
    print(f"\n  Discrepancy Recall (TP/(TP+FN)):          {summary['recall_discrepancy']:.1%}")
    print(f"  Precision        (TP/(TP+FP)):             {summary['precision']:.1%}")
    print(f"  F1-Score         (harmonic mean):          {summary['f1_score']:.4f}")
    print(f"  False Alarm Rate / FPR (FP/(FP+TN)):       {summary['false_alarm_rate_fpr']:.1%}")
    print(f"\n  Mean Execution Time:                       {summary['mean_exec_ms']:.2f} ms")
    print(f"  Measured Analyst Baseline:                 {summary['measured_analyst_baseline_sec']:.0f} s")
    print(f"  Mean Time Reduction:                       {summary['mean_time_reduction_pct']:.1f}%")
    if summary["mean_claim_faithfulness_score"] is not None:
        print(f"  Mean Claim Faithfulness Score:             {summary['mean_claim_faithfulness_score']:.1f}%")
    else:
        print(f"  Mean Claim Faithfulness Score:             N/A (no [JSON:] citations in mock synthesis)")
    print(sep + "\n")


# ===========================================================================
# CLI ENTRYPOINT
# ===========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TradeFlow Sentinel — 40-Case Benchmark Suite")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")
    parser.add_argument("--case-id", default=None, help="Run a single case by case_id")
    args = parser.parse_args()

    suite = build_test_suite()
    if args.case_id:
        suite = [c for c in suite if c["case_id"] == args.case_id]
        if not suite:
            print(f"Case '{args.case_id}' not found. Available: {[c['case_id'] for c in build_test_suite()]}")
            sys.exit(1)

    results = run_benchmark(suite, verbose=not args.json)
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
