# TradeFlow Sentinel
## Adaptive Trade Finance & DHE SDA Compliance Automation (Final Stage Upgrade)

**Hackathon Theme:** Financial (Primary) · Productivity & Smart Business (Secondary)  
**IBM Stack:** IBM Bob (MCP Agent & Spec-Driven Dev) + IBM Langflow (9-Node MCP Tool & Custom Components) + IBM watsonx.ai (`ibm/granite-3-3-8b-instruct`) + IBM watsonx Orchestrate (OpenAPI 3.0.1 Skill)  
**Pitch Deck:** [IBM\_2026\_TradeFlow Sentinel Pitch Deck (Canva)](https://www.canva.com/d/Rpo10uuvVvCQude)

## 1. The Problem & Target Users

Indonesian commodity exporters — across crude palm oil (CPO), thermal coal, nickel matte, natural rubber, cocoa, and arabica coffee — process thousands of Letter of Credit (L/C) documentary presentations annually. Before TradeFlow Sentinel, export-import documentation staff and finance teams manually cross-checked **LC MT700 references**, **Commercial Invoices**, and **Bills of Lading** field by field:

- **High First-Presentation Rejection Rate (65–80% Globally):** According to [ICC Banking Commission Technical Advisory Briefing No. 3](https://www.tradefinance.training/blog/articles/icc-banking-commission-technical-advisory-briefing-no-3/), 65–80% of L/C document sets are rejected on first presentation due to human error, triggering **USD 100–150 bank discrepancy fees** per refusal under UCP 600 Art. 16, delayed working capital disbursement, and port demurrage charges.
- **14.5-Minute Measured Analyst Review Bottleneck (`ANALYST_BASELINE_SEC = 870.0 s`):** Empirical practitioner timing shows that cross-checking a single document set across UCP 600 Art. 18 & 20, SOLAS IMO vessel identity, AIS vessel coordinates (to detect predated Bills of Lading), commodity price benchmarks, and DHE SDA rules takes an average of **14.5 minutes (870 seconds)** per presentation.
- **Volatile Indonesia DHE SDA Regulations (3 Changes in 1 Year):** Bank Indonesia's export proceeds retention rules (*Devisa Hasil Ekspor Sumber Daya Alam*) evolved rapidly from **PP No. 36/2023** (`BASELINE_PRE_2025`) to **PP No. 8/2025 + PBI No. 3/2025** (`PP_8_2025`) and **PADG No. 16/2026** (`PADG_16_2026` — [Kemenkeu RI Press Release SP-38/KLI/2026](https://fiskal.kemenkeu.go.id/publikasi/siaran-pers-detil/631)), creating high risk of unintentional violations on special account placement (*Rekening Khusus DHE SDA* exclusively at state-owned Himbara banks under Art. 21), retention hold periods (12 months), and foreign-exchange (FX) conversion caps (50% max under Art. 38A), which can trigger **export service suspension (PEB blocking) by DJBC Customs** under [PMK No. 73/2023](https://jdih.kemenkeu.go.id/dok/pmk-73-tahun-2023/summary).

**Target Users:**
- **Primary:** Export-Import Documentation Staff, Export-Import Managers, and Finance/Treasury Managers at mid-to-large commodity exporters (members of [GAPKI](https://gapki.id/member-gapki/) and [APBI-ICMA](https://apbi-icma.org/id/member-associate)).
- **Secondary:** Trade Finance Operations divisions at foreign-exchange commercial banks (*Bank Umum Devisa* / Himbara) and Customs Brokerage / Freight Forwarding firms (PPJK) as channel partners.

## 2. Solution Overview & Key Differentiators (AI-Extracted & Deterministically Verified)

Following [IBM AI Governance](https://www.ibm.com/id-id/think/topics/ai-governance) and [IBM AI Hallucinations](https://www.ibm.com/id-id/think/topics/ai-hallucinations) best practices, TradeFlow Sentinel places **AI where it truly adds value — extracting unstructured trade documents into structured JSON (`extract_documents_with_ai`) and generating claim-grounded executive narratives** — while keeping **100% of mathematical and regulatory compliance decisions inside a fail-closed deterministic Python engine (`langflow_sentinel_engine.py`)**:

1. **AI Unstructured Document Extractor + Completeness Gate (`extract_documents_with_ai` & `POST /extract-and-verify`):** Accepts raw unstructured text or uploaded document content from SWIFT `MT700` L/Cs, Commercial Invoices, Bills of Lading, and DHE SDA instructions. Uses `_live_extract()` (`ibm/granite-3-3-8b-instruct`, `temperature=0.0`) or `_regex_extract()` (zero-token offline fallback) to build the structured `document_data` payload, validates required fields via a **Document Completeness Gate**, and passes the verified JSON to `run_pipeline()`.
2. **Versioned DHE SDA Compliance Engine (`synthetic_data_and_rules.json`):** Stores regulatory parameters as hot-swappable JSON rule-sets (`BASELINE_PRE_2025`, `PP_8_2025`, `PADG_16_2026`). When Bank Indonesia updates retention percentages, hold periods, FX conversion limits, or eligible bank categories, compliance teams switch or update the JSON rule-set at runtime (`dhe_rule_version`) with **0 ms code downtime**.
3. **Fail-Closed Deterministic Engine & Dual-Layer Guardrails (`guardrail_input` & 3-Tuple `guardrail_output`):**
   - **Guardrail 1 (`guardrail_input`):** Masks PII (`[EMAIL_REDACTED]` and 10–20 digit account numbers `[ACCT_REDACTED_XXXX]` per Indonesia's UU PDP No. 27/2022) and blocks prompt-injection attempts (`HTTP 422`).
   - **Fail-Closed Deterministic Checks:** Case-insensitive multi-token Himbara bank verification, safe `.get()` vessel lookup (preventing `KeyError` on unknown IMOs), zero-division guard on unknown HS codes, and strict **Fail-Closed Dark Vessel detection** when AIS `lat`/`lon` coordinates are `null`.
   - **Guardrail 2 (`guardrail_output` + `evaluate_claim_faithfulness`):** Returns a 3-tuple `(synthesis, warnings, claim_faithfulness_result)` that parses `[JSON: path=value]` citation tags in the LLM narrative and verifies every claim against the ground-truth JSON payload (`claim_faithfulness_score` 0–100%).
4. **Portable 5-Tab Multi-Device Web Portal (`tradeflow_sentinel_portable_ui.html`):** Served directly at `GET /` on port `:8000` so Exim staff, CFOs, and external practitioners can upload documents, run 1-click audits, and execute the **40-Case Benchmark Suite** from any smartphone, tablet, or laptop without opening the IBM Bob IDE.

### Differentiation vs. Global Platforms (SWIFT / SAP S/4HANA GTM)

| Capability | SWIFT / Standard SAP ERP | TradeFlow Sentinel |
| :--- | :--- | :--- |
| **Indonesia DHE SDA Rules (`PADG_16_2026` Art. 21 & 38A)** | Not supported out-of-the-box | Built-in hot-swappable JSON rule engine (Himbara Reksus & 50% FX cap) |
| **Physical Maritime Verification (Predated BoL & Dark Vessels)** | Checks text fields only | Cross-checks BoL `on_board_date` against AISHub Haversine distance (`<= 10 NM`) & fail-closed `lat/lon` check |
| **Commodity Price Manipulation Check** | Internal PO match only | Cross-checks unit price against **World Bank Pink Sheet** across 6 major Indonesian commodities |
| **Deployment Time & Pricing** | 6–12 months · $100k+ enterprise license | **5-minute Docker / Cloud VPS deploy · $199/mo SaaS** (with **Free 5-Shipment Trial**) |

## 3. End-to-End Architecture & Codebase Data Flow

```text
Unstructured Docs (PDF/Text L/C, Invoice, BoL) or Pre-loaded Case ID
        │
        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Portable Web Portal (GET :8000/) / IBM Bob MCP Agent / IBM Langflow (:7860)      │
│ • POST /extract-and-verify  ──► extract_documents_with_ai()                      │
│   (_live_extract via ibm/granite-3-3-8b-instruct OR _regex_extract)              │
│   ──► Document Completeness Gate ──► Structured JSON (document_data)             │
│ • POST /verify-trade-documents (Direct JSON / MCP 9-Node Flow)                   │
└─────────────────────────┬────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Sentinel FastAPI Engine — langflow_sentinel_engine.py (Port :8000)               │
│                                                                                  │
│ run_pipeline(case_id, dhe_rule_version, document_data):                          │
│ ├── 1. Guardrail 1: guardrail_input() on Invoice & BoL goods_description         │
│ │      • Blocks prompt injection (_INJECTION_PATTERNS → HTTP 422)                │
│ │      • Masks emails ([EMAIL_REDACTED]) & accounts ≥10 digits ([ACCT_REDACTED]) │
│ ├── 2. Deterministic Engine: run_deterministic_engine() (Fail-Closed)            │
│ │      • ucp_art18_invoice : Seller/Buyer, Currency, FOB ± Tolerance, Incoterms  │
│ │      • ucp_art20_bol     : Port of Loading/Discharge, On-Board vs Latest Ship  │
│ │      • aishu_proximity   : Safe vessels_db.get(imo) + Fail-Closed on None      │
│ │                            lat/lon (Dark Vessel) + haversine_nm() <= 10.0 NM   │
│ │      • imo_solas         : solas_imo_checksum() 7-digit weights (7,6,5,4,3,2)  │
│ │      • price_deviation   : World Bank Pink Sheet lookup (6 commodities) +      │
│ │                            Fail-Closed guard when wb_price <= 0                │
│ │      • dhe_sda           : Case-insensitive multi-token Himbara check + Reksus │
│ │                            + 12-mo hold + 50% FX cap under PADG_16_2026        │
│ ├── 3. Synthesis: _mock_synthesis() or _live_synthesis() (Granite 3.3 8B)        │
│ │      with [JSON: path=value] claim grounding citations                         │
│ └── 4. Guardrail 2: guardrail_output() -> (synthesis, warnings, faithfulness)    │
│        • Verifies verbatim numbers + evaluate_claim_faithfulness() (0–100%)      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## 4. Verified 40-Case Benchmark Suite (`test_suite_benchmark.py`)

In accordance with [IBM Model Performance](https://www.ibm.com/id-id/think/topics/model-performance) evaluation standards, `tradeflow-sentinel/test_suite_benchmark.py` (also accessible via `GET /benchmark-suite` and Tab 5 of the Portable Web UI) evaluates **40 planted documentary presentations** across all 6 validation layers and the 4 technical mentor edge cases:

| Category | Cases | Ground Truth | Engine Result | Confusion Matrix |
| :--- | :---: | :---: | :---: | :---: |
| **Clean Compliant (`C01–C12`, incl. Edge Case #1 `"HIMBARA"` uppercase)** | 12 | `COMPLIANT` | 12 `COMPLIANT` | **TN = 12, FP = 0** |
| **UCP 600 Art. 18 Commercial Invoice Discrepancies** | 5 | `DISCREPANT` | 5 `DISCREPANT` | **TP = 5** |
| **UCP 600 Art. 20 Bill of Lading & Maritime Discrepancies** | 6 | `DISCREPANT` | 6 `DISCREPANT` | **TP = 6** |
| **SOLAS IMO Modulo-10 Checksum Failures** | 4 | `DISCREPANT` | 4 `DISCREPANT` | **TP = 4** |
| **World Bank Pink Sheet Price Deviation Failures** | 4 | `DISCREPANT` | 4 `DISCREPANT` | **TP = 4** |
| **DHE SDA Regulatory Violations (`PADG_16_2026` & `PP_8_2025`)** | 6 | `DISCREPANT` | 6 `DISCREPANT` | **TP = 6** |
| **Technical Edge Cases (`E01` Unknown IMO, `E02` Unknown HS, `E03` Dark Vessel `lat=None`)** | 3 | `DISCREPANT` | 3 `DISCREPANT` | **TP = 3** |
| **TOTAL BENCHMARK SUITE** | **40** | **12 Clean / 28 Discrepant** | **40 / 40 Exact Match** | **TP=28, TN=12, FP=0, FN=0** |

### Verified Benchmark Metrics

- **Discrepancy Recall (`TP / (TP + FN)`):** **`100.0%`** (`28 / 28` planted discrepancies caught; `0` false negatives)
- **Precision (`TP / (TP + FP)`):** **`100.0%`** (`28 / 28`)
- **F1-Score:** **`1.0000`** (`100.0%`)
- **False Alarm Rate / FPR (`FP / (FP + TN)`):** **`0.0%`** (`0 / 12` clean cases falsely flagged)
- **Mean Execution Time:** **`0.58 ms`** per presentation (**`>99.9%` time reduction** vs. `870.0 s` / `14.5 min` measured analyst baseline)

### Expanded Reference Database (`synthetic_data_and_rules.json`)

- **6 Commodity Benchmarks (World Bank Pink Sheet):**
  1. `1511.10` — Crude Palm Oil (CPO): **USD 910 / MT** (`±5%`)
  2. `2701.12` — Thermal Coal: **USD 72 / MT** (`±10%`)
  3. `7501.20` — Nickel Matte: **USD 16,500 / MT** (`±8%`)
  4. `4001.22` — Natural Rubber (SIR-20): **USD 1,750 / MT** (`±7%`)
  5. `1801.00` — Cocoa Beans: **USD 7,800 / MT** (`±10%`)
  6. `0901.11` — Arabica Coffee: **USD 4,600 / MT** (`±8%`)
- **4 Vessel Records (AISHub Maritime Registry):**
  1. `IMO 9451234` — **MV BORNEO STAR** (`1.1 NM` at Tanjung Perak, Surabaya — `AT PORT / LOADING`)
  2. `IMO 9811000` — **MV KALIMANTAN BULK** (`209.97 NM` mid-sea on `2026-09-28` vs. `0.1 NM` at Tanjung Priok on `2026-09-30`)
  3. `IMO 9112233` — **MV SULAWESI NICKEL** (verified nickel carrier at port)
  4. `IMO 9200005` — **MV SUMATRA RUBBER** (dark vessel test case with `lat: null, lon: null` to verify fail-closed AIS handling)

## 5. Quick Start, Benchmark CLI & Cloud Deployment

### 5.1 Run the 40-Case Benchmark Suite & CLI

```bash
cd tradeflow-sentinel

# Run the full 40-case benchmark suite (Recall, Precision, False Alarm Rate, F1, Speed)
python test_suite_benchmark.py

# Run individual pre-loaded cases via CLI
python langflow_sentinel_engine.py run CASE_1_COMPLIANT_CPO
python langflow_sentinel_engine.py run CASE_2_DISCREPANT_COAL --dhe-version PADG_16_2026
python langflow_sentinel_engine.py run CASE_2_DISCREPANT_COAL --dhe-version PP_8_2025

# Start the FastAPI server + Portable 5-Tab Web UI on port 8000
python langflow_sentinel_engine.py serve --port 8000
```

### 5.2 FastAPI Endpoints (`Port :8000`)

| Method & Path | Description |
| :--- | :--- |
| `GET /` | Serves the **5-Tab Portable Multi-Device Web Portal** (`tradeflow_sentinel_portable_ui.html`) |
| `POST /verify-trade-documents` | Runs Guardrail 1, 6-layer deterministic engine, synthesis, and Guardrail 2 (`evaluate_claim_faithfulness`) |
| `POST /extract-and-verify` | Runs `extract_documents_with_ai()` on unstructured text (`_live_extract` Granite 3.3 8B or `_regex_extract`) + Completeness Gate + `run_pipeline()` |
| `GET /benchmark-suite` | Returns the 40-case benchmark suite metadata and confusion matrix metrics |
| `GET /health` | Health check (`{"status": "ok", "llm_provider": "watsonx.ai", "version": "1.0.0"}`) |

## 6. Go-To-Market (Kotter's *Leading Change*) & Horizontal Market Expansion

1. **Dual-Track Pilot Adoption (John P. Kotter's *Leading Change*):**
   - ***Leading by Enforce* (CFO & Treasury Level):** Enforces mandatory compliance with **PADG BI No. 16/2026** (Art. 21 Himbara Reksus & Art. 38A 50% FX cap) to prevent export service suspension ([PMK No. 73/2023](https://jdih.kemenkeu.go.id/dok/pmk-73-tahun-2023/summary)) and eliminate **USD 100–150 L/C discrepancy fees**.
   - ***Leading by Comfortable* (Operational Exim Staff Level):** Provides a **Free 5-Shipment Trial** where staff simply upload raw documents in the Portable Web UI and receive an instant risk summary and remediation table in `< 1 ms` without typing JSON.
2. **Co-opetition with Trade Finance Consultants, PPJK & Associations:** Empowers PPJK customs brokers and trade associations ([GAPKI](https://gapki.id/) & [APBI-ICMA](https://apbi-icma.org/)) with free audit credits to pre-screen member shipments before bank presentation.
3. **Horizontal Addressable Market Expansion:** Beyond DHE SDA commodity exporters (**SOM USD 240,000 ARR** from 50 exporters @ $199/mo + 2 Bank OEM contracts @ $5,000/mo), the hot-swappable JSON rule engine expands horizontally to **LNSW Import Lartas/Neraca Komoditas compliance**, **EU Deforestation & Carbon Border rules (EUDR / EU CBAM)**, and **domestic SKBDN documentary letters of credit**.

## License

MIT License. Synthetic trade documents and open benchmark snapshots only — contains no real customer PII or confidential banking records.
