# TradeFlow Sentinel
## Adaptive Trade Finance & DHE SDA Compliance Automation (Final Stage)

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
5. **Zero-Cost Open Data & Mock-First Execution:** Uses open data snapshots (AISHub vessel coordinates and World Bank Pink Sheet benchmarks) plus MD5-cached mock synthesis (`USE_MOCK_LLM=true` by default, consuming `0` IBM Bobcoins).

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
│ Entry points                                                                     │
│ • Portable Web Portal (GET :8000/)                                               │
│ • IBM Bob MCP Agent (AGENT.md) ──► .bob/mcp.json ──► uvx mcp-proxy ──►           │
│   IBM Langflow 9-Node MCP Flow (:7860) ──► POST /verify-trade-documents          │
│ • IBM watsonx Orchestrate OpenAPI Skill ──► POST /verify-trade-documents         │
│ • POST /extract-and-verify  ──► extract_documents_with_ai()                      │
│   (_live_extract via ibm/granite-3-3-8b-instruct OR _regex_extract)              │
│   ──► Document Completeness Gate ──► Structured JSON (document_data)             │
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
│ ├── 3. Synthesis: _mock_synthesis() (MD5 cache) or _live_synthesis()             │
│ │      (Granite 3.3 8B, temperature=0.0) with [JSON: path=value] citations       │
│ └── 4. Guardrail 2: guardrail_output() -> (synthesis, warnings, faithfulness)    │
│        • Verifies verbatim numbers + evaluate_claim_faithfulness() (0–100%)      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Langflow Execution Topologies

| Topology | Source Files | How It Works |
| :--- | :--- | :--- |
| **9-Node MCP Flow (Primary)** | `TradeFlow Sentinel Compliance Tool.json` + `langflow_sentinel_engine.py` | Exposed as MCP tool `tradeflow_sentinel_compliance`: **Chat Input** → 3 parallel **Intent & Payload Extractor** nodes (`extract_case_id`, `extract_dhe_rule`, `extract_json`) → **API Message Payload Builder** → **API Request** (`POST :8000/verify-trade-documents`) → **⚖️ Sentinel Compliance Checker** → **📋 Report Formatter** → **📄 Compliance Report Output**. |
| **3-Node Native Component Pipeline** | `component_input.py` → `component_engine.py` → `component_output.py` | Mounted to `/app/custom_components` in `docker-compose.yml`. Three native Langflow `Component` subclasses passing `Data` objects in-process. |
| **1-Node All-in-One Component** | `langflow_component.py` | Single self-contained `TradeFlowSentinelComponent` with all validation, synthesis, and guardrail logic inlined for Langflow's validator sandbox. |

### Role of IBM Bob & IBM watsonx Orchestrate

- **IBM Bob — Development Role (Spec-Driven Development):** Used to architect and validate the repository from the specifications in `Docs/MARKDOWN/prompt for phase 1 to IBM Bob.md` and `prompt for phase 2 to IBM Bob.md`, plus 7 custom developer skills in `.bob/skills/` (`solution-architect`, `sop-builder`, `agentic-workflow-advisor`, `agent-instructions-evaluator`, `wxo-builder`, `wxo-analyzer`, `telemetry-analyzer`).
- **IBM Bob — Operational Role (Compliance Officer via MCP):** Configured via `.bob/mcp.json` (Langflow MCP Streamable HTTP endpoint via `uvx mcp-proxy`) and governed by `tradeflow-sentinel/AGENT.md`. Bob invokes the Langflow MCP tool and formats deterministic findings into an executive audit report under the **Passthrough Numerical Faithfulness** rules in `AGENT.md`.
- **IBM watsonx Orchestrate — Enterprise OpenAPI Skill:** `tradeflow-sentinel/orchestrate_skill_openapi.json` (OpenAPI 3.0.1, `operationId: verifyTradeDocuments`, `healthCheck`) is ready for one-click import so enterprise workflows or ERP webhooks can trigger `/verify-trade-documents`.

## 4. Deep Dive: Deterministic Engine & Rules

### 4.1 Six-Layer Deterministic Validation (`run_deterministic_engine`)

| Check Key in `findings.checks` | Standard / Source | Deterministic Logic |
| :--- | :--- | :--- |
| `ucp_art18_invoice` | **ICC UCP 600 Art. 18** | Case-insensitive `seller == beneficiary` and `buyer == applicant`, exact `currency` and `incoterms`, and `abs(total_fob_usd - amount) <= amount * tolerance_pct / 100`. |
| `ucp_art20_bol` | **ICC UCP 600 Art. 20** | Verifies `port_of_loading`, `port_of_discharge`, and `on_board_date <= latest_shipment_date`, plus aggregates the AISHub predated-BoL failure. |
| `aishu_proximity` | **AISHub Historical Snapshots** | Matches `on_board_date` against the vessel's `snapshots`, computes `haversine_nm()` ($R = 3440.065\text{ NM}$), flags **PREDATED BoL** if `distance_nm > 10.0 NM`. Unknown IMO or `lat/lon = null` → **FAIL** (fail-closed). |
| `imo_solas` | **SOLAS Checksum** | $\left(\sum_{i=0}^{5} \text{digit}_i \times (7 - i)\right) \bmod 10$ must equal the 7th check digit. |
| `price_deviation` | **World Bank Pink Sheet** | Looks up benchmark by `hs_code`, computes `round(((inv_price - wb_price) / wb_price) * 100, 2)`, fails if `abs(deviation_pct) > tolerance_pct`. Unknown HS / `wb_price <= 0` → **FAIL** (fail-closed). |
| `dhe_sda` | **Bank Indonesia DHE SDA** | `NOT_APPLICABLE` if `fob_usd < USD 250,000`. Otherwise checks `hold_period_months`, `requested_fx_conversion_pct`, and under `PADG_16_2026` a case-insensitive Himbara / state-owned bank match plus Reksus placement. |

### 4.2 Versioned DHE SDA Rule Matrix (`synthetic_data_and_rules.json`)

| Rule Version Key | Legal Basis | Effective Date | FOB Threshold | Retention | Min Hold | Max FX to IDR | Eligible Bank & Account Placement |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `BASELINE_PRE_2025` | PP No. 36/2023 | 2023-07-01 | USD 250,000 | 30% | 3 months | 100% (No cap) | Any licensed Bank Devisa or LPEI |
| `PP_8_2025` | PP No. 8/2025 + PBI No. 3/2025 | 2025-03-01 | USD 250,000 | 100% | 12 months | 100% (No cap) | Any licensed Bank Devisa or LPEI |
| `PADG_16_2026` *(Active)* | PADG No. 16/2026 | 2026-06-01 | USD 250,000 | 100% | 12 months | **50% hard cap** | **Reksus DHE SDA at Himbara (BRI, BNI, Mandiri, BTN) only** |

### 4.3 Reference Database (`synthetic_data_and_rules.json`)

- **6 Commodity Benchmarks (World Bank Pink Sheet):**
  1. `1511.10` — Crude Palm Oil (CPO): **USD 910 / MT** (`±5%`)
  2. `2701.12` — Thermal Coal: **USD 72 / MT** (`±10%`)
  3. `7501.20` — Nickel Matte: **USD 16,500 / MT** (`±8%`)
  4. `4001.22` — Natural Rubber (SIR-20): **USD 1,750 / MT** (`±7%`)
  5. `1801.00` — Cocoa Beans: **USD 7,800 / MT** (`±10%`)
  6. `0901.11` — Arabica Coffee: **USD 4,600 / MT** (`±8%`)
- **4 Vessel Records (AISHub Maritime Registry):**
  1. `IMO 9315460` — **MV BORNEO STAR** (`1.1 NM` at Tanjung Perak, Surabaya — `AT PORT / LOADING`)
  2. `IMO 9811000` — **MV KALIMANTAN BULK** (`209.97 NM` mid-sea on `2026-09-28` vs. `0.1 NM` at Tanjung Priok on `2026-09-30`)
  3. `IMO 9112233` — **MV SULAWESI NICKEL** (at port near Morowali Nickel Terminal)
  4. `IMO 9200005` — **MV SUMATRA RUBBER** (dark vessel with `lat: null, lon: null` to verify fail-closed AIS handling)

## 5. Verified 40-Case Benchmark Suite (`test_suite_benchmark.py`)

In accordance with [IBM Model Performance](https://www.ibm.com/id-id/think/topics/model-performance) evaluation standards, `tradeflow-sentinel/test_suite_benchmark.py` (also accessible via `GET /benchmark-suite` and Tab 5 of the Portable Web UI) evaluates **40 planted documentary presentations** across all 6 validation layers and the technical mentor edge cases:

| Category | Cases | Ground Truth | Engine Result | Confusion Matrix |
| :--- | :---: | :---: | :---: | :---: |
| **Clean Compliant (`C01–C12`, incl. Edge Case `"HIMBARA"` uppercase)** | 12 | `COMPLIANT` | 12 `COMPLIANT` | **TN = 12, FP = 0** |
| **UCP 600 Art. 18 Commercial Invoice Discrepancies** | 5 | `DISCREPANT` | 5 `DISCREPANT` | **TP = 5** |
| **UCP 600 Art. 20 Bill of Lading & Maritime Discrepancies** | 6 | `DISCREPANT` | 6 `DISCREPANT` | **TP = 6** |
| **SOLAS IMO Modulo-10 Checksum Failures** | 4 | `DISCREPANT` | 4 `DISCREPANT` | **TP = 4** |
| **World Bank Pink Sheet Price Deviation Failures** | 4 | `DISCREPANT` | 4 `DISCREPANT` | **TP = 4** |
| **DHE SDA Regulatory Violations (`PADG_16_2026` & `PP_8_2025`)** | 6 | `DISCREPANT` | 6 `DISCREPANT` | **TP = 6** |
| **Technical Edge Cases (`E01` Unknown IMO, `E02` Unknown HS, `E03` Dark Vessel `lat=None`)** | 3 | `DISCREPANT` | 3 `DISCREPANT` | **TP = 3** |
| **TOTAL BENCHMARK SUITE** | **40** | **12 Clean / 28 Discrepant** | **40 / 40 Exact Match** | **TP=28, TN=12, FP=0, FN=0** |

- **Discrepancy Recall (`TP / (TP + FN)`):** **`100.0%`** (`28 / 28`; `0` false negatives)
- **Precision (`TP / (TP + FP)`):** **`100.0%`** (`28 / 28`)
- **F1-Score:** **`1.0000`**
- **False Alarm Rate / FPR (`FP / (FP + TN)`):** **`0.0%`** (`0 / 12`)
- **Mean Execution Time:** **`~0.6–5.4 ms`** per presentation depending on hardware (**`>99.9%` time reduction** vs. the `870 s` analyst baseline)

### Quantifiable ROI

| Metric | Manual Process | TradeFlow Sentinel | Verified Result |
| :--- | :--- | :--- | :--- |
| **Document Examination Time** | 14.5 minutes (`870 s`) | **Single-digit ms** | **>99.9% time reduction** (capped in `roi_context`) |
| **DHE SDA Regulatory Updates** | Manual SOP rewrite (hours/days) | Runtime `dhe_rule_version` parameter | **0 ms code downtime** (JSON config switch) |
| **Predated BoL Detection** | Manual AIS lookup (15–20 mins) | `haversine_nm()` + historical snapshot match | **Deterministic (`1.1 NM` PASS vs `209.97 NM` FAIL)** |
| **Price Manipulation Check** | Subjective analyst check | World Bank Pink Sheet lookup by HS code | **Deterministic (`0.0%` vs `+45.83%` FAIL)** |
| **Compute Cost per Audit** | Staff & operational overhead | `~$0.001` (mock/deterministic) / `~$0.012` (live Granite) | **>95% SaaS gross margin** |

## 6. Quick Start, Benchmark CLI & Cloud Deployment

### 6.1 Docker Compose (Recommended)

```bash
cd tradeflow-sentinel
cp .env.example .env
# Edit .env to set LANGFLOW_SUPERUSER_PASSWORD and LANGFLOW_SECRET_KEY
docker-compose up --build
```

- **Portable Web Portal:** `http://localhost:8000/`
- **Swagger UI:** `http://localhost:8000/docs`
- **Langflow UI & MCP Server:** `http://localhost:7860`

### 6.2 Cloud VPS Deploy (IDCloudHost Ubuntu 22.04 / 24.04)

```bash
cd tradeflow-sentinel
chmod +x deploy_idcloudhost.sh
./deploy_idcloudhost.sh   # checks Docker, generates secret key + .env, builds, waits for health checks
```

### 6.3 Benchmark Suite & CLI (no Docker)

```bash
cd tradeflow-sentinel

# Full 40-case benchmark (Recall, Precision, False Alarm Rate, F1, Speed)
python test_suite_benchmark.py

# Individual pre-loaded cases
python langflow_sentinel_engine.py run CASE_1_COMPLIANT_CPO
python langflow_sentinel_engine.py run CASE_2_DISCREPANT_COAL --dhe-version PADG_16_2026
python langflow_sentinel_engine.py run CASE_2_DISCREPANT_COAL --dhe-version PP_8_2025 --json

# FastAPI server + Portable 5-Tab Web UI
python langflow_sentinel_engine.py serve --port 8000
```

### 6.4 FastAPI Endpoints (`Port :8000`)

| Method & Path | Description |
| :--- | :--- |
| `GET /` | Serves the **5-Tab Portable Multi-Device Web Portal** (`tradeflow_sentinel_portable_ui.html`) |
| `POST /verify-trade-documents` | Guardrail 1 → 6-layer deterministic engine → synthesis → Guardrail 2 (`evaluate_claim_faithfulness`) |
| `POST /extract-and-verify` | `extract_documents_with_ai()` on unstructured text (`_live_extract` Granite 3.3 8B or `_regex_extract`) + Completeness Gate + `run_pipeline()` |
| `GET /benchmark-suite` | 40-case benchmark suite definitions |
| `GET /presets` | Preset cases and DHE SDA versions for the Web UI |
| `GET` / `POST /validation-feedback` | Retrieve / submit practitioner validation feedback |
| `GET /health` | Health check (`{"status": "ok", "use_mock_llm": true, "version": "1.0.0"}`) |

Example — runtime rule switch on the same case (5 discrepancies under `PADG_16_2026` drop to 2 under `PP_8_2025`):

```bash
curl -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE_2_DISCREPANT_COAL", "dhe_rule_version": "PP_8_2025"}'
```

Live payloads are sent as `document_data` (`lc_mt700_reference`, `commercial_invoice`, `bill_of_lading`, `dhe_sda_transaction` or `exporter_instructions`); full examples are in `Docs/MARKDOWN/test_case-result.md`.

### 6.5 Langflow 9-Node Flow & IBM Bob MCP

1. Import `tradeflow-sentinel/TradeFlow Sentinel Compliance Tool.json` into Langflow (`http://localhost:7860`).
2. Point `.bob/mcp.json` to your Langflow project's MCP Streamable HTTP URL and API key.
3. In IBM Bob (with `tradeflow-sentinel/AGENT.md` loaded), prompt with a case string (`CASE_2_DISCREPANT_COAL PADG_16_2026`) or a natural-language request containing a JSON payload.
4. Bob invokes `mcp__lf-starter_project__tradeflow_sentinel_compliance` and returns an Indonesian compliance report with UCP 600 citations and corrective action tables.

## 7. Repository Structure

```text
Hacktiv8---IBM-National-Hackathon/
├── README.md
├── .bob/
│   ├── mcp.json                                   # MCP proxy config: IBM Bob → Langflow (:7860)
│   └── skills/                                    # 7 IBM Bob skills for Spec-Driven Development
├── Docs/
│   ├── IMG/                                       # Langflow flow, IBM Bob outputs, architecture diagram
│   ├── MARKDOWN/                                  # Phase 1 & 2 Bob prompts, test transcripts, submission notes
│   └── PDF/                                       # Blueprint, mentor feedback, submission form, pitch deck
├── tradeflow-sentinel/
│   ├── AGENT.md                                   # IBM Bob system instructions & passthrough guardrails
│   ├── TradeFlow Sentinel Compliance Tool.json    # 9-node Langflow MCP flow export
│   ├── langflow_sentinel_engine.py                # Engine, extractor, Guardrails 1 & 2, FastAPI & CLI
│   ├── tradeflow_sentinel_portable_ui.html        # 5-tab Portable Web Portal (served at GET /)
│   ├── test_suite_benchmark.py                    # 40-case benchmark suite
│   ├── component_input.py / component_engine.py / component_output.py  # 3-node topology
│   ├── langflow_component.py                      # 1-node all-in-one topology
│   ├── synthetic_data_and_rules.json              # DHE SDA versions, AISHub, Pink Sheet, cases
│   ├── orchestrate_skill_openapi.json             # watsonx Orchestrate OpenAPI 3.0.1 skill
│   ├── docker-compose.yml                         # tradeflow_langflow :7860 + tradeflow_sentinel_api :8000
│   ├── deploy_idcloudhost.sh                      # One-command Ubuntu VPS deploy
│   └── .env.example                               # Environment template
└── archives/                                      # Iteration snapshots, old test scripts & node prototypes
```

## 8. Business Model, Market Sizing & Go-To-Market

### Pricing Tiers

| Tier | Model | Price | Target Segment |
| :--- | :--- | :--- | :--- |
| **Free Trial** | Onboarding | **5 shipments free** | Any exporter evaluating the product |
| **Pay-Per-Audit** | Transaction-based | **USD 2.50 / audit** | SME commodity exporters & occasional L/C users |
| **Professional SaaS** | Monthly subscription | **USD 199 / month** (up to 500 audits/mo) | Mid-to-large commodity exporters (>10 L/Cs/month) |
| **Enterprise** | Annual contract | **USD 1,499 / month** (unlimited + ERP webhooks) | Major trading houses & multinational commodity groups |
| **Bank OEM (White-Label)** | API licensing / rev-share | **Custom (~USD 5,000 / mo)** | Trade Finance Operations at Bank Umum Devisa |

### Market Sizing (Indonesia Baseline: BPS Export Statistics USD 264B/yr)

- **TAM (USD 22M–26M / year):** Full SaaS penetration across national documentary credit presentations (~42,000–52,000 L/C sets annually, USD 21B–26B in L/C-financed trade).
- **SAM (USD 13M–16M / year):** Mandatory DHE SDA commodity export segment (FOB ≥ USD 250,000, ~62% of non-oil & gas exports).
- **SOM (USD 240,000 ARR Target in Year 1–2):** 50 exporters on Professional SaaS (`50 × $199 × 12 = $119,400`) + 2 Bank OEM contracts (`2 × $5,000 × 12 = $120,000`).

### Go-To-Market (Kotter's *Leading Change*)

1. **Dual-Track Pilot Adoption:**
   - ***Leading by Enforce* (CFO & Treasury Level):** Enforces compliance with **PADG BI No. 16/2026** (Art. 21 Himbara Reksus & Art. 38A 50% FX cap) to prevent export service suspension ([PMK No. 73/2023](https://jdih.kemenkeu.go.id/dok/pmk-73-tahun-2023/summary)) and eliminate **USD 100–150 L/C discrepancy fees**.
   - ***Leading by Comfortable* (Operational Exim Staff Level):** **Free 5-Shipment Trial** — staff upload raw documents in the Portable Web UI and get an instant risk summary and remediation table without typing JSON.
2. **Co-opetition with Trade Finance Consultants, PPJK & Associations:** Free audit credits for PPJK customs brokers and associations ([GAPKI](https://gapki.id/) & [APBI-ICMA](https://apbi-icma.org/)) to pre-screen member shipments before bank presentation.
3. **Horizontal Market Expansion:** The hot-swappable JSON rule engine extends to **LNSW Import Lartas/Neraca Komoditas compliance**, **EU Deforestation & Carbon Border rules (EUDR / EU CBAM)**, and **domestic SKBDN documentary letters of credit**.

## 9. Product Roadmap

- **Phase 1 — MVP (Completed ✅):** UCP 600 Art. 18 & 20 cross-checks, SOLAS IMO checksum, AISHub Haversine proximity, World Bank Pink Sheet deviation, versioned DHE SDA engine, Dual Guardrails, 9-node Langflow MCP flow, IBM Bob `AGENT.md`, watsonx Orchestrate OpenAPI skill.
- **Phase 2 — Final Stage (Completed ✅):** AI unstructured document extractor + Completeness Gate (`/extract-and-verify`), claim-faithfulness Guardrail 2, fail-closed fixes for unknown IMO / unknown HS / dark vessels / Himbara casing, 6-commodity & 4-vessel reference data, 40-case benchmark suite, 5-tab Portable Web Portal, one-command VPS deploy.
- **Phase 3 — Next:**
  - Full parser for raw **SWIFT Category 7 (`MT700` / `MT707`)** and automated `MT734` Notice of Refusal drafting.
  - Complex documentary edge cases: **Charter Party BoL (UCP 600 Art. 22)**, **Multimodal Transport Documents (Art. 19)**, multi-currency invoicing, disguised HS code detection.
  - ERP webhook connectors (**SAP S/4HANA GTM**, **Odoo**) and Bank Umum Devisa white-label API.

## License

MIT License. Synthetic trade documents and open benchmark snapshots only — contains no real customer PII or confidential banking records.
