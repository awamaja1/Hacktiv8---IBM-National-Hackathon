import urllib.request
import json
import traceback

payload = {
  "case_id": "LIVE_DEMO_COAL",
  "dhe_rule_version": "PADG_16_2026",
  "document_data": {
    "lc_mt700_reference": {
      "beneficiary": "PT KALIMANTAN COAL EXPORT",
      "applicant": "SHANGHAI ENERGY IMPORTS CO. LTD",
      "currency": "USD",
      "amount": 5250000,
      "tolerance_pct": 10,
      "incoterms": "FOB",
      "port_of_loading": "Tanjung Priok, Jakarta",
      "port_of_discharge": "Qingdao, China",
      "latest_shipment_date": "2026-09-30",
      "goods_description": "THERMAL COAL, HS 2701.12"
    },
    "commercial_invoice": {
      "invoice_number": "INV-2026-KCE-0805",
      "seller": "PT KALIMANTAN COAL EXPORT",
      "buyer": "SHANGHAI ENERGY IMPORTS CO. LTD",
      "issue_date": "2026-09-28",
      "currency": "USD",
      "hs_code": "2701.12",
      "goods_description": "THERMAL COAL",
      "quantity_mt": 50000,
      "unit_price_usd_mt": 105,
      "total_fob_usd": 5250000,
      "incoterms": "FOB",
      "port_of_loading": "Tanjung Priok, Jakarta"
    },
    "bill_of_lading": {
      "bl_number": "BL-2026-KB-0805",
      "vessel_name": "MV KALIMANTAN BULK",
      "imo_number": "9811000",
      "shipper": "PT KALIMANTAN COAL EXPORT",
      "consignee": "TO ORDER OF PT BANK BNI",
      "notify_party": "SHANGHAI ENERGY IMPORTS CO. LTD",
      "port_of_loading": "Tanjung Priok, Jakarta",
      "port_of_discharge": "Qingdao, China",
      "on_board_date": "2026-09-28",
      "goods_description": "THERMAL COAL, HS 2701.12",
      "quantity_mt": 50000,
      "freight_terms": "FREIGHT PREPAID"
    },
    "dhe_sda_transaction": {
      "fob_usd": 5250000,
      "nominated_bank": "PT Bank CIMB Niaga Tbk",
      "bank_category": "PRIVATE_BANK",
      "placement_type": "Regular FX Account",
      "requested_fx_conversion_pct": 80,
      "hold_period_months": 12
    }
  }
}

req = urllib.request.Request(
    'http://localhost:8000/verify-trade-documents',
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(e.read().decode())
except Exception as e:
    print(e)
