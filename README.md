# TradeFlow Sentinel
## Adaptive Trade Finance & DHE SDA Compliance Automation

**Hackathon Theme:** Financial (Primary) · Productivity & Smart Business (Secondary)  
**IBM Stack:** IBM Bob (MCP Agent & Spec-Driven Dev) + IBM Langflow (9-Node MCP Tool & Custom Components) + IBM watsonx.ai (`ibm/granite-3-3-8b-instruct`) + IBM watsonx Orchestrate (OpenAPI 3.0.1 Skill)  
**Pitch Deck:** [IBM\_2026\_TradeFlow Sentinel Pitch Deck (Canva)](https://www.google.com/search?q=https://canva.link/w9xre2lqzl1nw87)

## 1. The Problem & Target Users

Indonesian commodity exporters — across crude palm oil (CPO), thermal coal, nickel, and rubber — process thousands of Letter of Credit (L/C) documentary presentations annually. Before TradeFlow Sentinel, export-import documentation staff and finance teams manually cross-checked **LC MT700 references**, **Commercial Invoices**, and **Bills of Lading** field by field:

- **High First-Presentation Rejection Rate (65–80% Globally):** According to ICC Banking Commission research, 65–80% of L/C document sets are rejected on first presentation due to human error, triggering **USD 100–150 bank discrepancy fees** per refusal under UCP 600 Art. 16, delayed working capital disbursement, and port demurrage charges.
- **45-Minute Manual Review Bottleneck:** A single document presentation takes an average of **45 minutes (2,700 seconds)** to verify across UCP 600 Art. 18 & 20, SOLAS IMO vessel identity, AIS vessel coordinates (to detect predated Bills of Lading), and commodity price benchmarks.
- **Volatile Indonesia DHE SDA Regulations (3 Changes in 1 Year):** Bank Indonesia's export proceeds retention rules (*Devisa Hasil Ekspor Sumber Daya Alam*) evolved rapidly from **PP No. 36/2023** (`BASELINE_PRE_2025`) to **PP No. 8/2025 + PBI No. 3/2025** (`PP_8_2025`) and **PADG No. 16/2026** (`PADG_16_2026`), creating high risk of unintentional violations on special account placement (*Rekening Khusus DHE SDA* at state-owned Himbara banks), retention hold periods, and foreign-exchange (FX) conversion caps.

**Target Users:**
- **Primary:** Export-Import Documentation Staff, Export-Import Managers, and Finance Managers at mid-to-large commodity exporters and importers (CPO, coal, nickel, rubber).
- **Secondary:** Trade Finance Operations divisions at foreign-exchange commercial banks (*Bank Umum Devisa*).

## 2. Solution Overview & Key Differentiators

TradeFlow Sentinel separates **deterministic mathematical verification** (executed in pure Python inside `langflow_sentinel_engine.py`) from **natural-language compliance synthesis** (performed by IBM Bob governed by `AGENT.md` and Dual-Layer AI Guardrails).

1. **Versioned DHE SDA Compliance Engine (`synthetic_data_and_rules.json`):** Stores regulatory parameters as hot-swappable JSON rule-sets (`BASELINE_PRE_2025`, `PP_8_2025`, `PADG_16_2026`). When Bank Indonesia updates retention percentages, hold periods, FX conversion limits, or eligible bank categories, compliance teams switch or update the JSON rule-set at runtime (`dhe_rule_version`) without changing engine code or restarting containers.
2. **Hybrid Deterministic + AI Architecture with Dual Guardrails:** Every numerical calculation — SOLAS modulo-10 IMO checksum, Haversine great-circle distance in nautical miles from AISHub historical snapshots, World Bank Pink Sheet price deviation percentage, and FOB tolerance — is computed deterministically by Python. **Guardrail 1** sanitizes inputs (PII masking and prompt-injection blocking), while **Guardrail 2** and `AGENT.md` passthrough rules guarantee that no number or regulatory threshold is ever invented by the LLM.
3. **Zero-Cost Open Data & Sub-Millisecond to Millisecond Execution:** Uses open data snapshots (AISHub vessel coordinates and World Bank Pink Sheet commodity benchmarks) plus MD5-cached mock synthesis (`USE_MOCK_LLM=true` by default, consuming `0` IBM Bobcoins) to slash audit time from **45 minutes (2,700 s)** to **~0.7 ms** (regression mode via `case_id`) or **3.8–6.2 ms** (live payload mode via `document_data`).

## 3. End-to-End Architecture & Codebase Data Flow

The codebase implements an MCP-native operational workflow connecting **IBM Bob**, **IBM Langflow**, and the **Sentinel FastAPI Engine**, alongside an import-ready **IBM watsonx Orchestrate** OpenAPI 3.0.1 skill:

```text
Dokumen (OCR JSON / Case ID) ──► IBM Bob Agent (tradeflow-sentinel/AGENT.md)
                                       │
                                       ▼  MCP Tool Call (.bob/mcp.json -> uvx mcp-proxy :7860)
                                  mcp__lf-starter_project__tradeflow_sentinel_compliance
                                       │
┌──────────────────────────────────────┴───────────────────────────────────────────┐
│ IBM Langflow — "TradeFlow Sentinel Compliance Tool.json" (9-Node MCP Flow)       │
│                                                                                  │
│ [1. Chat Input]                                                                  │
│       ├──► [2. Intent & Payload Extractor] ──► extract_case_id() (Regex CASE_*)  │
│       ├──► [3. Intent & Payload Extractor] ──► extract_dhe_rule() (Default PADG) │
│       └──► [4. Intent & Payload Extractor] ──► extract_json() (document_data)    │
│                         │                                                        │
│                         ▼                                                        │
│ [5. API Message Payload Builder]                                                 │
│     • _extract_pure_text() strips Message wrappers & ```json fences              │
│     • Reconstructs nested dict payload: {case_id, dhe_rule_version, document_data}│
│                         │                                                        │
│                         ▼                                                        │
│ [6. API Request]                                                                 │
│     • HTTP POST http://host.docker.internal:8000/verify-trade-documents          │
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
│ ├── 2. Deterministic Engine: run_deterministic_engine()                          │
│ │      • ucp_art18_invoice : Seller/Buyer, Currency, FOB ± Tolerance, Incoterms  │
│ │      • ucp_art20_bol     : Port of Loading/Discharge, On-Board vs Latest Ship  │
│ │      • aishu_proximity   : Matches on_board_date to vessel["snapshots"] +      │
│ │                            haversine_nm() vs PORT_PROXIMITY_THRESHOLD_NM (10NM)│
│ │      • imo_solas         : solas_imo_checksum() 7-digit weights (7,6,5,4,3,2)  │
│ │      • price_deviation   : World Bank Pink Sheet benchmark by hs_code          │
│ │      • dhe_sda           : Versioned rule check (FOB ≥ $250k, Hold Months,     │
│ │                            FX Conversion Cap, Himbara Bank & Reksus Account)   │
│ ├── 3. Engine Synthesis: _mock_synthesis() (MD5 cache) or _live_synthesis()      │
│ │      (IBM watsonx.ai ibm/granite-3-3-8b-instruct, temperature=0.0)             │
│ └── 4. Guardrail 2: guardrail_output()                                           │
│        • Verifies deviation_pct, distance_nm, and failed FX % appear verbatim    │
└─────────────────────────┬────────────────────────────────────────────────────────┘
                          │  JSON Response (findings, synthesis, guardrail warnings, roi_context)
                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Langflow Post-Processing (Nodes 7–9) ──► Returned to IBM Bob                     │
│                                                                                  │
│ [7. ⚖️ Sentinel Compliance Checker]                                              │
│     • _format_report(): Status icon, synthesis, numbered discrepancies,          │
│       check summary, and ROI (>99.9% cap when reduction >= 99.9% & time > 0)     │
│                         │                                                        │
│                         ▼                                                        │
│ [8. 📋 Report Formatter]                                                         │
│                         │                                                        │
│                         ▼                                                        │
│ [9. 📄 Compliance Report Output]                                                 │
│                         │                                                        │
│                         ▼                                                        │
│ IBM Bob Agent synthesizes final natural-language audit report (AGENT.md rules)   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Three Langflow Execution Topologies in the Codebase

In addition to the primary **9-Node MCP Orchestration Flow** (`TradeFlow Sentinel Compliance Tool.json`), the `tradeflow-sentinel/` directory includes two self-contained custom component topologies mounted via `docker-compose.yml`:

| Topology | Source Files | How It Works |
| :--- | :--- | :--- |
| **9-Node MCP Flow (Primary)** | `TradeFlow Sentinel Compliance Tool.json` + `langflow_sentinel_engine.py` | Exposed as MCP tool `tradeflow_sentinel_compliance`. Uses **Chat Input**, 3 parallel **Intent & Payload Extractor** nodes, **API Message Payload Builder**, **API Request** (`POST :8000/verify-trade-documents`), **⚖️ Sentinel Compliance Checker**, **📋 Report Formatter**, and **📄 Compliance Report Output**. |
| **3-Node Native Component Pipeline** | `component_input.py` → `component_engine.py` → `component_output.py` | Mounted to `/app/custom_components` in `docker-compose.yml`. Splits the pipeline into three native Langflow `Component` subclasses (`TradeDocumentInputComponent`, `ComplianceEngineComponent`, `ComplianceReportComponent`) passing `Data` objects in-process. |
| **1-Node All-in-One Component** | `langflow_component.py` | Single self-contained `TradeFlowSentinelComponent` class with all validation, synthesis, and guardrail logic inlined for zero-dependency execution inside Langflow's validator sandbox. |

### Role of IBM Bob & IBM watsonx Orchestrate

- **IBM Bob — Development Role (Spec-Driven Development):** Used to architect and validate the repository using the initial specification in `Docs/MARKDOWN/prompt for phase 1 to IBM Bob.md` and 7 custom developer skills inside `.bob/skills/` (`solution-architect`, `sop-builder`, `agentic-workflow-advisor`, `agent-instructions-evaluator`, `wxo-builder`, `wxo-analyzer`, `telemetry-analyzer`).
- **IBM Bob — Operational Role (Compliance Officer via MCP):** Configured via `.bob/mcp.json` (connecting to Langflow's MCP SSE/Streamable HTTP endpoint `/api/v1/mcp/project/990f7c71-46f7-4843-8c6f-736f9e7a754e/streamable` via `uvx mcp-proxy`) and governed by `tradeflow-sentinel/AGENT.md`. Bob invokes the Langflow MCP tool and formats the deterministic findings into an executive audit report while strictly obeying the **Passthrough Numerical Faithfulness** rules in Section 6 of `AGENT.md`.
- **IBM watsonx Orchestrate — Enterprise OpenAPI Skill:** `tradeflow-sentinel/orchestrate_skill_openapi.json` defines an OpenAPI 3.0.1 specification (`operationId: verifyTradeDocuments`, `healthCheck`) ready for one-click import into IBM watsonx Orchestrate so enterprise workflows or ERP webhooks can trigger the exact same `/verify-trade-documents` endpoint.

## 4. Repository Structure

```text
Hacktiv8---IBM-National-Hackathon/
├── README.md                                           # Comprehensive codebase & business documentation
├── .gitignore                                          # Root Git ignore rules
├── .bob/                                               # IBM Bob MCP configuration & developer skills
│   ├── mcp.json                                        # MCP proxy config connecting IBM Bob to Langflow (:7860)
│   └── skills/                                         # 7 IBM Bob skills for Spec-Driven Development & evaluation
│       ├── agent-instructions-evaluator/               # Evaluates AGENT.md quality & extract_agent_info.py
│       ├── agentic-workflow-advisor/                   # Analyzes Langflow JSON flows (extract_flow_info.py)
│       ├── solution-architect/                         # High-level solution architecture generation skill
│       ├── sop-builder/                                # Standard Operating Procedure generator skill
│       ├── telemetry-analyzer/                         # Trace analysis scripts for ADK & AgentOps
│       ├── wxo-analyzer/                               # IBM watsonx Orchestrate workflow analyzer
│       └── wxo-builder/                                # IBM watsonx Orchestrate skill/agent builder & references
├── Docs/                                               # Visual & Markdown project artifacts
│   ├── IMG/
│   │   ├── 01-workflow.png                             # Screenshot of 9-node Langflow MCP orchestration flow
│   │   ├── 02-ibm_bob-test_case_compliant.png          # IBM Bob audit output for compliant test case
│   │   ├── 03-ibm_bob-test_case_discrepancy.png        # IBM Bob audit output for discrepant test case
│   │   ├── 04-ibm_bob-prompt_example_compliant.png     # Live payload prompt example in IBM Bob
│   │   └── 05-Diagram arsitektur tradeflow-sentinel.png# End-to-end architecture diagram
│   └── MARKDOWN/
│       ├── prompt for phase 1 to IBM Bob.md            # Spec-Driven Development master prompt for Phase 1 MVP
│       └── test_case-result.md                         # Full transcripts of IBM Bob MCP tool calls & audit reports
├── tradeflow-sentinel/                                 # Core production backend, Langflow flow & Docker setup
│   ├── AGENT.md                                        # IBM Bob system instructions, UCP 600 & DHE SDA rules, passthrough guardrails
│   ├── TradeFlow Sentinel Compliance Tool.json         # 9-node Langflow MCP flow export (endpoint: tradeflow_sentinel_compliance)
│   ├── langflow_sentinel_engine.py                     # Core deterministic engine, Guardrails 1 & 2, FastAPI (:8000) & CLI
│   ├── component_input.py                              # 3-Node Topology Node 1: Trade Document Input + Guardrail 1
│   ├── component_engine.py                             # 3-Node Topology Node 2: Deterministic Compliance Engine
│   ├── component_output.py                             # 3-Node Topology Node 3: IBM Bob Synthesis + Guardrail 2 + ROI
│   ├── langflow_component.py                           # 1-Node Topology: Self-contained single-file Langflow component
│   ├── synthetic_data_and_rules.json                   # Versioned DHE SDA rules, AISHub snapshots, Pink Sheet & synthetic cases
│   ├── orchestrate_skill_openapi.json                  # OpenAPI 3.0.1 skill specification for IBM watsonx Orchestrate
│   ├── docker-compose.yml                              # Multi-container orchestration (tradeflow_langflow :7860 + tradeflow_sentinel_api :8000)
│   ├── .env.example                                    # Environment template (ports, limits, watsonx credentials, thresholds)
│   └── .gitignore                                      # Service-level Git ignore
└── archives/                                           # Iteration snapshots, test scripts & standalone node prototypes
    ├── test_api.py                                     # Automated HTTP test script for FastAPI /verify-trade-documents
    ├── test_engine.py                                  # Unit test script for deterministic engine functions
    └── test_case_execution.json                        # Recorded JSON execution trace
```

## 5. Deep Dive: Deterministic Engine & Dual Guardrails (`langflow_sentinel_engine.py`)

### 5.1 Guardrail 1 — Input Sanitization (`guardrail_input`)

Executed in `run_pipeline()` on free-text document fields (`commercial_invoice.goods_description` and `bill_of_lading.goods_description`) before any validation or synthesis:

- **Prompt Injection Blocking (`_INJECTION_PATTERNS`):** Scans input against compiled case-insensitive regex patterns (`ignore (previous|all) instructions`, `system: you are`, `<|im_start|>`, `\bDAN\b`, `forget (everything|your instructions)`, `pretend you are`, `act as if you have no restrict`). Raises `ValueError("GUARDRAIL_1_BLOCKED: ...")`, which FastAPI returns immediately as **HTTP 422 Unprocessable Entity**.
- **PII Masking (`_EMAIL_PATTERN`, `_ACCOUNT_PATTERN`):** Redacts email addresses to `[EMAIL_REDACTED]` and numeric sequences of 10–20 digits to `[ACCT_REDACTED_XXXX]` (retaining only the last 4 digits) while appending a trace entry to `guardrail_1_warnings`.

### 5.2 Six-Layer Deterministic Validation (`run_deterministic_engine`)

| Check Key in `findings.checks` | Standard / Source | Deterministic Logic Implemented in Code |
| :--- | :--- | :--- |
| `ucp_art18_invoice` | **ICC UCP 600 Art. 18** | Compares `commercial_invoice` against `lc_mt700_reference`: exact case-insensitive match on `seller == beneficiary` and `buyer == applicant`, exact match on `currency` and `incoterms`, and verifies `abs(total_fob_usd - amount) <= amount * tolerance_pct / 100`. |
| `ucp_art20_bol` | **ICC UCP 600 Art. 20** | Compares `bill_of_lading` against `lc_mt700_reference`: verifies `port_of_loading`, `port_of_discharge`, and string date comparison `on_board_date <= latest_shipment_date`, plus aggregates AISHub predated BoL failure. |
| `aishu_proximity` | **AISHub Historical Snapshots** | Matches `bill_of_lading.on_board_date` against the vessel's time-series `snapshots` array (falling back to `snapshots[0]` or static `lat`/`lon`), computes great-circle distance via `haversine_nm(vessel_lat, vessel_lon, port_lat, port_lon)` ($R = 3440.065\text{ NM}$), and flags **PREDATED BoL** if `distance_nm > PORT_PROXIMITY_THRESHOLD_NM` (`10.0 NM`). |
| `imo_solas` | **SOLAS Checksum** | Validates 7-digit IMO number via `solas_imo_checksum()`: computes $\left(\sum_{i=0}^{5} \text{digit}_i \times (7 - i)\right) \bmod 10$ and verifies equality with the 7th check digit (`computed_check_digit`). |
| `price_deviation` | **World Bank Pink Sheet** | Looks up commodity benchmark by `hs_code` (`1511.10` CPO = USD 910/MT ±5%; `2701.12` Thermal Coal = USD 72/MT ±10%), computes `round(((inv_price - wb_price) / wb_price) * 100, 2)`, and fails if `abs(deviation_pct) > tolerance_pct`. |
| `dhe_sda` | **Bank Indonesia DHE SDA** | Evaluates `dhe_sda_transaction` (or `exporter_instructions` mapped automatically in `run_pipeline`) against `dhe_sda_versions[rule_version]`. If `fob_usd < fob_threshold_usd` (`USD 250,000`), returns `NOT_APPLICABLE`. Otherwise verifies `hold_period_months >= min_hold_months`, `requested_fx_conversion_pct <= fx_conversion_to_idr_max_pct`, and under `PADG_16_2026` enforces `"Himbara"` / `"STATE_OWNED"` in `bank_category` and `"Reksus"` in `placement_type`. |

### 5.3 Versioned DHE SDA Rule Matrix (`synthetic_data_and_rules.json`)

| Rule Version Key | Legal Basis | Effective Date | FOB Threshold | Retention | Min Hold | Max FX to IDR | Eligible Bank & Account Placement |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `BASELINE_PRE_2025` | PP No. 36/2023 | 2023-07-01 | USD 250,000 | 30% | 3 months | 100% (No cap) | Any licensed Bank Devisa or LPEI |
| `PP_8_2025` | PP No. 8/2025 + PBI No. 3/2025 | 2025-03-01 | USD 250,000 | 100% | 12 months | 100% (No cap) | Any licensed Bank Devisa or LPEI |
| `PADG_16_2026` *(Active)* | PADG No. 16/2026 | 2026-06-01 | USD 250,000 | 100% | 12 months | **50% hard cap** | **Reksus DHE SDA at Himbara (BRI, BNI, Mandiri, BTN) only** |

### 5.4 Guardrail 2 — Output Numerical Faithfulness (`guardrail_output` & `AGENT.md`)

1. **Engine-Level Check (`guardrail_output`):** Scans the generated `synthesis` text to confirm that non-zero `price_deviation.deviation_pct`, `aishu_proximity.distance_nm`, and failed `dhe_sda.requested_fx_conversion_pct` appear **verbatim** as substrings. If any figure is missing or altered, appends a `⚠️ GUARDRAIL 2 WARNINGS (numerical faithfulness)` block and populates `guardrail_2_warnings`.
2. **Agent-Level Passthrough Constraint (`tradeflow-sentinel/AGENT.md`):** Instructs IBM Bob never to invent thresholds, tolerances, or numbers not present verbatim in the JSON findings (`tolerance_pct`, `fob_threshold_usd`, `min_hold_months`, `fx_conversion_to_idr_max_pct`).

## 6. Quick Start & Usage

### 6.1 Run with Docker Compose (Recommended)

```bash
cd tradeflow-sentinel
cp .env.example .env
# Edit .env to set LANGFLOW_SUPERUSER_PASSWORD and LANGFLOW_SECRET_KEY
docker-compose up --build
```

- **Langflow UI & MCP Server:** `http://localhost:7860`
- **Sentinel FastAPI Server:** `http://localhost:8000`
- **Interactive Swagger UI:** `http://localhost:8000/docs`
- **Health Check:** `curl http://localhost:8000/health` → `{"status": "ok", "use_mock_llm": true, "version": "1.0.0"}`

### 6.2 Mode 1: Regression Mode via `case_id` (REST API & CLI)

Evaluate pre-loaded synthetic cases from `synthetic_data_and_rules.json`:

```bash
# Case 1 — Compliant CPO Export (FOB USD 1,820,000 | MV BORNEO STAR 1.1 NM | Bank Mandiri Reksus | 40% FX)
curl -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE_1_COMPLIANT_CPO", "dhe_rule_version": "PADG_16_2026"}'

# Case 2 — Discrepant Coal Export under PADG_16_2026 (Returns 5 Discrepancies across 4 FAIL checks)
curl -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE_2_DISCREPANT_COAL", "dhe_rule_version": "PADG_16_2026"}'

# Runtime Version Switch Demo — Re-evaluate Case 2 under older PP_8_2025 (Drops from 5 to 2 Discrepancies)
curl -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE_2_DISCREPANT_COAL", "dhe_rule_version": "PP_8_2025"}'
```

Or run directly via the Python CLI without Docker:

```bash
cd tradeflow-sentinel
python langflow_sentinel_engine.py run CASE_1_COMPLIANT_CPO
python langflow_sentinel_engine.py run CASE_2_DISCREPANT_COAL --dhe-version PADG_16_2026
python langflow_sentinel_engine.py run CASE_2_DISCREPANT_COAL --dhe-version PP_8_2025 --json
python langflow_sentinel_engine.py serve --port 8000
```

### 6.3 Mode 2: Live Payload Mode via `document_data` (Dynamic OCR JSON)

`run_pipeline()` also accepts arbitrary live document payloads via `document_data` (supporting both `dhe_sda_transaction` and `exporter_instructions` keys, and matching `bill_of_lading.on_board_date` against vessel historical snapshots: e.g., `IMO9811000` is `209.97 NM` away on `2026-09-28` (`EN ROUTE / MID-SEA`), but `0.1 NM` at port on `2026-09-30` (`AT PORT / LOADING`)):

```bash
curl -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "LIVE_DEMO_COMPLIANT_COAL",
    "dhe_rule_version": "PADG_16_2026",
    "document_data": {
      "lc_mt700_reference": {
        "beneficiary": "PT KALIMANTAN COAL EXPORT",
        "applicant": "SHANGHAI ENERGY IMPORTS CO. LTD",
        "currency": "USD",
        "amount": 3750000,
        "tolerance_pct": 10,
        "incoterms": "FOB",
        "port_of_loading": "Tanjung Priok, Jakarta",
        "port_of_discharge": "Qingdao, China",
        "latest_shipment_date": "2026-09-30",
        "goods_description": "THERMAL COAL, HS 2701.12"
      },
      "commercial_invoice": {
        "invoice_number": "INV-2026-KCE-0805-REV",
        "seller": "PT KALIMANTAN COAL EXPORT",
        "buyer": "SHANGHAI ENERGY IMPORTS CO. LTD",
        "issue_date": "2026-09-30",
        "currency": "USD",
        "hs_code": "2701.12",
        "goods_description": "THERMAL COAL",
        "quantity_mt": 50000,
        "unit_price_usd_mt": 75,
        "total_fob_usd": 3750000,
        "incoterms": "FOB",
        "port_of_loading": "Tanjung Priok, Jakarta"
      },
      "bill_of_lading": {
        "bl_number": "BL-2026-KB-0805-REV",
        "vessel_name": "MV KALIMANTAN BULK",
        "imo_number": "9811000",
        "shipper": "PT KALIMANTAN COAL EXPORT",
        "consignee": "TO ORDER OF PT BANK BNI",
        "notify_party": "SHANGHAI ENERGY IMPORTS CO. LTD",
        "port_of_loading": "Tanjung Priok, Jakarta",
        "port_of_discharge": "Qingdao, China",
        "on_board_date": "2026-09-30",
        "goods_description": "THERMAL COAL, HS 2701.12",
        "quantity_mt": 50000,
        "freight_terms": "FREIGHT PREPAID"
      },
      "dhe_sda_transaction": {
        "fob_usd": 3750000,
        "nominated_bank": "PT Bank Mandiri",
        "bank_category": "STATE_OWNED_BANK",
        "placement_type": "Special FX Account (Reksus DHE SDA)",
        "requested_fx_conversion_pct": 50,
        "hold_period_months": 12
      }
    }
  }'
```

### 6.4 Mode 3: Langflow 9-Node Flow & IBM Bob MCP Integration

1. Import `tradeflow-sentinel/TradeFlow Sentinel Compliance Tool.json` into Langflow (`http://localhost:7860`).
2. Ensure `.bob/mcp.json` points to your Langflow project's MCP Streamable HTTP URL and API key.
3. In IBM Bob (with `tradeflow-sentinel/AGENT.md` loaded), prompt Bob with either a shorthand case string (`CASE_2_DISCREPANT_COAL PADG_16_2026`) or a natural-language request containing a raw JSON document payload (see full interactive examples in `Docs/MARKDOWN/test_case-result.md`).
4. Bob invokes `mcp__lf-starter_project__tradeflow_sentinel_compliance`, which triggers **Chat Input** → 3 parallel **Intent & Payload Extractor** nodes → **API Message Payload Builder** → **API Request** → **⚖️ Sentinel Compliance Checker** → **📋 Report Formatter** → **📄 Compliance Report Output**, and returns a structured Indonesian compliance report with UCP 600 article citations and corrective action tables.

## 7. Quantifiable ROI & Verified Benchmark Results

| Metric | Manual Process | TradeFlow Sentinel | Verified Codebase Result |
| :--- | :--- | :--- | :--- |
| **Document Examination Time** | 45 minutes (`2,700 s`) | **0.7 ms – 6.2 ms** | **>99.9% time reduction** (capped in `roi_context`) |
| **DHE SDA Regulatory Updates** | Manual SOP rewrite (hours/days) | Runtime `dhe_rule_version` parameter | **0 ms code downtime** (JSON config switch) |
| **Predated BoL Detection** | Manual AIS lookup (15–20 mins) | `haversine_nm()` + historical snapshot match | **Deterministic (`1.1 NM` PASS vs `209.97 NM` FAIL)** |
| **Price Manipulation Check** | Subjective analyst check | World Bank Pink Sheet lookup by HS code | **Deterministic (`0.0%` vs `+45.83%` FAIL)** |
| **Compute Cost per Audit** | Staf & operational overhead | `~$0.001` (mock/deterministic) / `~$0.012` (live Granite) | **>95% SaaS gross margin** |

## 8. Business Model & Market Sizing

### Pricing Tiers

| Tier | Model | Price | Target Segment |
| :--- | :--- | :--- | :--- |
| **Pay-Per-Audit** | Transaction-based | **USD 2.50 / audit** | SME commodity exporters & occasional L/C users |
| **Professional SaaS** | Monthly subscription | **USD 199 / month** (up to 500 audits/mo) | Mid-to-large commodity exporters (>10 L/Cs/month) |
| **Enterprise** | Annual contract | **USD 1,499 / month** (unlimited + ERP webhooks) | Major trading houses & multinational commodity groups |
| **Bank OEM (White-Label)** | API licensing / rev-share | **Custom (~USD 5,000 / mo)** | Trade Finance Operations at Bank Umum Devisa |

### Market Sizing (Indonesia Baseline: BPS Export Statistics USD 264B/yr)

- **TAM (USD 22M–26M / year):** Full SaaS penetration across national export-import documentary credit presentations (~42,000–52,000 L/C sets annually, representing USD 21B–26B in L/C-financed trade volume).
- **SAM (USD 13M–16M / year):** Mandatory DHE SDA commodity export segment (CPO, coal, nickel, rubber, mineral exports with FOB ≥ USD 250,000, accounting for ~62% of non-oil & gas exports).
- **SOM (USD 240,000 ARR Target in Year 1–2):** 50 mid-to-large commodity exporters on the Professional SaaS tier (`50 × $199/mo × 12 = $119,400/yr`) + 2 Bank Umum Devisa white-label OEM contracts (`2 × $5,000/mo × 12 = $120,000/yr`).

## 9. 3-Phase Product & Scalability Roadmap

- **Phase 1 — Stage 1 MVP (Completed ✅):**
  - Cross-check Commercial Invoice & Bill of Lading against LC MT700 under UCP 600 Art. 5, 18, and 20 + ISBP 745.
  - Multi-layer deterministic verification: SOLAS IMO checksum, AISHub time-series Haversine proximity, and World Bank Pink Sheet price deviation.
  - Versioned DHE SDA Compliance Engine (`BASELINE_PRE_2025`, `PP_8_2025`, `PADG_16_2026`), Dual Guardrails (`guardrail_input` & `guardrail_output`), 9-node Langflow MCP flow, IBM Bob `AGENT.md` integration, and import-ready watsonx Orchestrate OpenAPI 3.0.1 skill.
- **Phase 2 — Complex Trade Finance Edge Cases & Raw SWIFT Parser:**
  - Full parser for raw **SWIFT Category 7 (`MT700` / `MT707`)** messages and automated `MT734` Notice of Refusal drafting.
  - Support for complex documentary edge cases: **Charter Party Bills of Lading (UCP 600 Art. 22)**, **Combined/Multimodal Transport Documents (Art. 19)**, **multi-currency invoicing**, and **disguised HS code detection**.
- **Phase 3 — Enterprise ERP Webhooks, Bank White-Label & Cross-Border Regulatory Expansion:**
  - Automated webhook connectors for exporter/importer ERP systems (**SAP S/4HANA Global Trade Management** and **Odoo**).
  - White-label API integration with **Trade Finance Operations** divisions at national foreign-exchange banks (*Bank Umum Devisa*).
  - Horizontal expansion of the **Versioned Rule Engine** to other threshold-, percentage-, and entity-whitelist-based regulations beyond DHE SDA (customs valuation rules, EU CBAM carbon reporting, OECD transfer pricing thresholds, and regional foreign-exchange retention regimes).

## License

MIT License. Synthetic trade documents and open benchmark snapshots only — contains no real customer PII or confidential banking records.
