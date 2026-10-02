# TradeFlow Sentinel
## Adaptive Trade Finance & DHE SDA Compliance Automation

> **Hackathon Theme:** Financial (Primary) · Productivity & Smart Business (Secondary)
> **IBM Stack:** IBM watsonx Orchestrate + Langflow + IBM Bob

---

## Table of Contents
1. [The Problem](#1-the-problem)
2. [Solution Overview](#2-solution-overview)
3. [Architecture](#3-architecture)
4. [Quantifiable ROI](#4-quantifiable-roi)
5. [Stage 1 MVP Scope](#5-stage-1-mvp-scope)
6. [Repository Structure](#6-repository-structure)
7. [Quick Start](#7-quick-start)
   - [Docker Compose](#run-with-docker-compose)
   - [Langflow UI — Visual Demo](#run-in-langflow-ui-visual-canvas-demo)
   - [REST API (curl)](#test-case-1--compliant-cpo)
   - [IBM watsonx Orchestrate](#import-into-ibm-watsonx-orchestrate)
   - [CLI](#cli-no-docker)
8. [Business Model](#8-business-model)
9. [Market Sizing](#9-market-sizing)
10. [3-Phase Roadmap](#10-3-phase-roadmap)

---

## 1. The Problem

Indonesian commodity exporters — in sectors like crude palm oil, coal, nickel ore, and rubber — collectively process thousands of Letter of Credit (LC) documentary presentations per year. Each presentation requires a compliance officer to manually cross-check:

- **Commercial Invoice vs. Bill of Lading** for quantity, HS code, port, and price consistency.
- **LC MT700 terms** (UCP 600 Art. 18 and Art. 20) for discrepancies that could trigger a refusal under Art. 16.
- **SOLAS vessel IMO validity** and AIS position data to detect predated Bills of Lading.
- **Indonesia DHE SDA regulations** — a rapidly evolving framework that changed three times between 2023 and 2026 — to ensure export proceeds are deposited in compliant bank accounts within the correct hold period and FX conversion caps.

**Manual review average: 45 minutes (2,700 seconds) per transaction set.** Errors cause LC refusals, delayed payments, interest losses, and regulatory penalties under Bank Indonesia enforcement.

---

## 2. Solution Overview

TradeFlow Sentinel is a deterministic-first, AI-augmented compliance automation system. The engine computes verifiable, rule-based findings in milliseconds. IBM Bob then synthesises those findings into a clear compliance narrative. IBM watsonx Orchestrate exposes the pipeline as an enterprise skill accessible from any business workflow.

**Core Differentiator:** The deterministic engine is the source of truth. The LLM synthesises — it never invents numbers. Guardrail 2 enforces this numerically on every output.

**Adaptive Regulatory Architecture:** The versioned rule engine is regulation-agnostic by design. Indonesia's DHE SDA (export proceeds retention) is the Stage 1 showcase, but the same version-switching mechanism — rule parameters loaded from a JSON config, evaluated at runtime, switchable without restart or code change — applies to **any** regulation that evolves over time: OECD BEPS transfer pricing thresholds, EU CBAM carbon tariffs, FATF AML screening rules, or country-specific customs valuation regimes. If DHE SDA were repealed tomorrow, the engine continues to serve every other compliance dimension already built in (UCP 600 Art. 18/20, SOLAS IMO, price benchmarking), and a new regulatory module is added by extending the JSON config — zero engine code changes required.

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│              IBM watsonx Orchestrate (Skill Layer)                   │
│                                                                      │
│   User / ERP / BPM  ──►  Custom Skill (orchestrate_skill_openapi)   │
│                           POST /verify-trade-documents               │
│                                ▼                                     │
│              [case_id, dhe_rule_version]                             │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │  HTTP (OpenAPI 3.0.1)
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  Langflow (Orchestration Layer)                      │
│                                                                      │
│   TradeFlowSentinelComponent (Custom Component)                      │
│   ├── Guardrail 1: Input PII masking + injection blocking            │
│   ├── Deterministic Engine:                                          │
│   │    ├── UCP 600 Art. 18  — Commercial Invoice cross-check         │
│   │    ├── UCP 600 Art. 20  — Bill of Lading + SOLAS IMO checksum    │
│   │    ├── AISHub Haversine — Vessel proximity (predated BoL)        │
│   │    ├── World Bank Pink Sheet — Unit price deviation              │
│   │    └── Versioned DHE SDA Evaluator (3 rule versions)            │
│   └── FastAPI endpoint  :8000                                        │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │  Findings dict (structured JSON)
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   IBM Bob (Synthesis Layer)                          │
│                                                                      │
│   AGENT.md role + UCP 600 Art. 5/18/20 rules + Guardrails           │
│   ├── IBM Granite 3.3 (8B Instruct) — watsonx.ai                    │
│   │    or Mock/Cached mode (USE_MOCK_LLM=true, zero Bobcoins)        │
│   ├── Structured Synthesis (Case ID, Status, Discrepancies,         │
│   │    DHE SDA Assessment, Recommendation)                           │
│   └── Guardrail 2: Numerical faithfulness verification               │
└──────────────────────────────────────────────────────────────────────┘
```

**Data flow in plain English:**
1. **Orchestrate** receives a trigger (case_id + optional DHE rule version) from a human analyst, an ERP webhook, or another Orchestrate agent.
2. **Langflow** runs the deterministic Python engine — no LLM cost, no hallucination risk at the fact-extraction stage.
3. **IBM Bob** synthesises the structured findings into a professional compliance report. Guardrail 2 verifies every number before the report is returned.

---

## 4. Quantifiable ROI

| Metric | Manual Process | TradeFlow Sentinel | Delta |
|---|---|---|---|
| Review time per transaction set | 45 min (2,700 s) | < 5 s | **> 99.9% reduction** |
| Exact measured reduction | — | 2,700 s → ~0.004 s engine | **99.9998% time efficiency gain** |
| DHE SDA rule version switches | Manual policy lookup (hours) | Runtime parameter (`dhe_rule_version`) | Instant |
| Predated BoL detection | Manual AIS cross-check (15–20 min) | Automated Haversine + AISHub snapshot | < 1 s |
| Price manipulation detection | Analyst judgement (subjective) | World Bank Pink Sheet deviation ± tolerance | Deterministic |

**ROI Calculation (exact):**
```
Baseline:          2,700 seconds per transaction set
Sentinel engine:   ~0.004 seconds (4 ms measured)
Reduction:         (2,700 - 0.004) / 2,700 × 100 = 99.9998%
```
- **Execution Time:** 
  - **~0.7 ms** (Cached / Regression Mode via `case_id`)
  - **2.0 - 4.5 ms** (Live Payload Mode via `document_data` with dynamic AISHub coordinate generation)
- **Time Reduction:** >99.9% compared to 45-minute manual document examination.


---

## 5. Stage 1 MVP Scope

**In Scope (live end-to-end execution):**
- Commercial Invoice ↔ Bill of Lading cross-check under LC MT700 reference
- UCP 600 Art. 5 (document-only examination principle), Art. 18 (Commercial Invoice), Art. 20 (Bill of Lading)
- ISBP 745 alignment for goods description and HS code consistency
- SOLAS 7-digit IMO checksum validation
- AISHub Haversine vessel proximity check (predated BoL detection)
- World Bank Pink Sheet price deviation benchmark
- Versioned DHE SDA evaluator: `BASELINE_PRE_2025` / `PP_8_2025` / `PADG_16_2026`

**Synthetic Test Cases:**
- `CASE_1_COMPLIANT_CPO` — HS 1511.10, FOB USD 1,820,000, IMO9315460, Tanjung Perak, $910/MT CPO, Himbara Reksus, 40% FX → **COMPLIANT**
- `CASE_2_DISCREPANT_COAL` — HS 2701.12, FOB USD 5,250,000, IMO9811000, 209.97 NM from Tanjung Priok (predated BoL), $105/MT vs $72/MT benchmark (+45.8%), non-Himbara bank, 80% FX, Regular FX Account → **DISCREPANT** (5 simultaneous violations)

---

## 6. Repository Structure

```
Hackathon Project Root/
├── README.md                       # This file (Project Overview & Business Model)
├── Docs/                           # Project Artifacts
│   ├── IMG/Screenshot 2026-09-27 201719.png       # Screenshot of the Langflow architecture
│   └── MARKDOWN/prompt for phase 1 to IBM Bob.md  # Original prompt guiding this MVP
├── tradeflow-sentinel/             # Core Backend & Langflow Setup
│   ├── component_input.py          # Node 1: Document Input & Guardrail 1
│   ├── component_engine.py         # Node 2: Deterministic Compliance Engine
│   ├── component_output.py         # Node 3: IBM Bob Synthesis & Guardrail 2
│   ├── Adaptive Trade Finance & DHE SDA Compliance Flow.json  # Langflow Flow Export
│   ├── synthetic_data_and_rules.json   # DHE SDA rules + synthetic cases + benchmarks
│   ├── orchestrate_skill_openapi.json  # OpenAPI 3.0.1 spec for watsonx Orchestrate
│   ├── langflow_sentinel_engine.py     # Standalone FastAPI endpoint
│   ├── .env.example                    # Template — copy to .env and fill in secrets
│   └── docker-compose.yml              # Zero-cost local Docker: Langflow :7860 + Sentinel API :8000
```

---

## 7. Quick Start

### Prerequisites
- Docker Desktop (or Docker Engine + Compose plugin)
- No API keys required for mock mode

### Run with Docker Compose
```bash
git clone <repo>
cd tradeflow-sentinel
docker-compose up --build
```

Services:
- Langflow UI: http://localhost:7860
- Sentinel API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Test Case 1 — Compliant CPO
```bash
curl -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE_1_COMPLIANT_CPO", "dhe_rule_version": "PADG_16_2026"}'
```

Expected: `"overall_status": "COMPLIANT"`, `"discrepancy_count": 0`

### Test Case 2 — Discrepant Coal
```bash
curl -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE_2_DISCREPANT_COAL", "dhe_rule_version": "PADG_16_2026"}'
```

Expected: `"overall_status": "DISCREPANT"`, `"discrepancy_count": 5`

### Demo: DHE SDA Version Switch (Live Hackathon Demo)
```bash
# Re-evaluate Case 2 under the older PP 8/2025 rule (bank restriction not yet active)
curl -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE_2_DISCREPANT_COAL", "dhe_rule_version": "PP_8_2025"}'
```

Expected: Bank restriction and FX cap violations disappear (PP_8_2025 allows any Bank Devisa and 100% FX). Remaining discrepancies: predated BoL + price deviation.

### Enable Live IBM watsonx (optional)
```bash
# Edit docker-compose.yml environment section:
USE_MOCK_LLM=false
WATSONX_API_KEY=your_api_key
WATSONX_PROJECT_ID=your_project_id
```

### Import into IBM watsonx Orchestrate
1. Open IBM watsonx Orchestrate → Skills → Import skill
2. Upload `orchestrate_skill_openapi.json`
3. Set Server URL to your Sentinel API endpoint
4. Skill `verifyTradeDocuments` is now available to all Orchestrate agents

### Run in Langflow UI (Visual Canvas Demo & MCP-Ready)

To see the full MCP-ready API orchestration pipeline in action, you can import the pre-built flow configuration:

1. Open **http://localhost:7860** (no login required for local mock mode)
2. On the main dashboard, click **Import** 
3. Select and upload the [`tradeflow-sentinel/TradeFlow Sentinel Compliance Tool.json`]( tradeflow-sentinel/TradeFlow%20Sentinel%20Compliance%20Tool.json) file included in this repository.
4. Click on the imported flow to open it. You will see the complete orchestration architecture:
   ```text
   [Chat Input] ──► [Regex Extractors] ──► [API Body Builder] ──► [API Request]
                                                                        │
   [Chat Output] ◄── [Report Formatter] ◄── [Sentinel Checker] ◄────────┘
   ```
   ![Langflow Architecture](Docs/IMG/Screenshot%202026-10-01%20211545.png)
5. To execute the compliance check, click the **Playground** button at the bottom right of the canvas.
6. Type the case parameters in the chat input. For example, to run Test Case 1:
   ```text
   CASE_1_COMPLIANT_CPO PADG_16_2026
   ```
7. The flow will parse the input, orchestrate the API call, and stream the formatted markdown report back to the chat interface.

**Live regulatory version-switch demo (hackathon highlight):**

1. In the Playground, test how the engine reacts to different regulatory regimes on the exact same document set.
2. Type and send: `CASE_2_DISCREPANT_COAL PP_8_2025`
   *(Expected: 2 violations—predated BoL + price deviation).*
3. Now type and send: `CASE_2_DISCREPANT_COAL PADG_16_2026`
   *(Expected: Violation count instantly jumps to 5. The stricter PADG 16/2026 bank restriction and FX cap rules activate immediately, with no restart or code change required).*

**What each violation means in Case 2 (under PADG 16/2026):**

| # | Check | Discrepancy |
|---|---|---|
| 1 | UCP 600 Art. 20 + AISHub | Predated BoL — vessel MV KALIMANTAN BULK (IMO 9811000) was 209.97 NM from Tanjung Priok on declared on-board date |
| 2 | World Bank Pink Sheet | Price deviation +45.83% exceeds ±10% tolerance (invoice $105/MT vs benchmark $72/MT) |
| 3 | DHE SDA FX cap | Requested 80% FX conversion exceeds PADG 16/2026 maximum 50% |
| 4 | DHE SDA bank | PT Bank CIMB Niaga is not Himbara; PADG 16/2026 mandates BRI/BNI/Mandiri/BTN only |
| 5 | DHE SDA placement | Regular FX Account is not a Reksus DHE SDA account as required by PADG 16/2026 |

> **Note:** The API returns 6 checks (4 FAIL, 2 PASS) but 5 discrepancies. This is because `ucp_art20_bol` and `aishu_proximity` are two checks evaluating the same event (vessel not at port) — they share one discrepancy. Meanwhile, `dhe_sda` is one check with 3 individual issues. Total: 1 + 1 + 3 = 5 discrepancies from 4 FAIL checks.

### Sample Output Report
You can view a complete generated sample report here: [test_case-result.md](Docs/MARKDOWN/test_case-result.md)

### CLI (no Docker)
```bash
pip install fastapi uvicorn ibm-watsonx-ai
python langflow_sentinel_engine.py run CASE_1_COMPLIANT_CPO
python langflow_sentinel_engine.py run CASE_2_DISCREPANT_COAL
python langflow_sentinel_engine.py serve --port 8000
```

---

## 8. Business Model

### Target Payers
**Primary:** Mid-to-large commodity exporters in Indonesia (palm oil, coal, nickel, rubber, coffee) with annual export value ≥ USD 3M who process ≥ 10 LC presentations per month.

**Secondary:** Trade Finance Operations teams at Indonesian and regional banks (Bank Devisa) processing LC document examinations under UCP 600.

### Pricing Tiers

| Tier | Model | Price | Target Segment |
|---|---|---|---|
| **Pay-Per-Audit** | Per-transaction SaaS | **USD 2.50 / audit** | SME exporters, occasional users |
| **Professional** | Monthly SaaS | **USD 199 / month** (up to 500 audits/mo) | Mid-size exporters, >10 LCs/month |
| **Enterprise** | Annual contract | **USD 1,499 / month** (unlimited + ERP webhook integration) | Large commodity trading houses, banks |
| **Bank OEM** | White-label API | Custom (revenue share) | Bank Devisa trade finance operations |

### Unit Economics (Pay-Per-Audit)
- Cost per audit (mock/deterministic only): ~$0.001 compute
- Cost per audit (with watsonx Granite live): ~$0.012 (6 IBM Bobcoins @ $0.002/Bobcoin est.)
- **Gross margin: 95%+ (mock mode) / 79%+ (live LLM mode)**

---

## 9. Market Sizing

> *Macro baseline: BPS "Statistik Perdagangan Luar Negeri Indonesia Ekspor 2025"*
> Indonesia total export value 2024: approximately **USD 264 billion** (non-oil & gas dominated by CPO, coal, nickel, rubber)

### TAM — Total Addressable Market
**Definition:** All LC-based trade finance documentary presentations in Indonesia annually.
- Indonesia's trade finance documentary credit volume: approximately **USD 21–26 billion** per year (estimated 8–10% of total export value of USD 264B as LC-financed, consistent with Asian Development Bank trade finance gap data for Southeast Asia).
- Average transaction value: ~USD 500,000 per LC.
- Estimated LC presentations: **~42,000–52,000 per year** (= USD 21–26B ÷ USD 500K).
- At USD 2.50 per audit (pay-per-audit): **TAM ≈ USD 105,000–130,000 per year**.
- At blended SaaS rate (~USD 500/mo effective per active account, weighted across Professional & Enterprise tiers): **TAM ≈ USD 22M–26M per year** (full SaaS penetration across all exporter accounts processing ≥1 LC/month).

### SAM — Serviceable Addressable Market
**Definition:** LC presentations involving commodity exports (CPO, coal, nickel, mineral) where DHE SDA compliance is mandatory (FOB ≥ USD 250,000).
- BPS 2025: Top-5 commodity export categories account for ~62% of total non-oil & gas export value.
- Estimated DHE SDA-subject LC presentations: **~26,000–32,000 per year** (~62% of TAM presentations).
- At blended SaaS rate (~USD 500/mo effective per active account): **SAM ≈ USD 13M–16M per year**.

### SOM — Serviceable Obtainable Market (3-Year Target)
**Definition:** Realistic market capture given direct sales to mid-to-large exporters and two bank OEM partnerships within 36 months.
- Target: 50 mid-large exporter accounts (Professional tier) + 2 Bank Devisa OEM partnerships.
- 50 × USD 199/mo × 12 = **USD 119,400/year**
- 2 bank OEM × USD 5,000/mo × 12 = **USD 120,000/year**
- **SOM Year 3 ARR ≈ USD 240,000**

---

## 10. 3-Phase Roadmap

### Phase 1 — Stage 1 MVP (Current) ✅
**Scope:** Invoice-BoL Cross-Check & Versioned DHE SDA Compliance

| Deliverable | Status |
|---|---|
| Deterministic UCP 600 Art. 18/20 engine | ✅ Complete |
| SOLAS IMO checksum + AISHub Haversine | ✅ Complete |
| World Bank Pink Sheet price deviation | ✅ Complete |
| Versioned DHE SDA evaluator (3 versions) | ✅ Complete |
| IBM Bob synthesis with dual guardrails | ✅ Complete |
| IBM watsonx Orchestrate OpenAPI skill | ✅ Complete |
| Langflow custom component | ✅ Complete |
| Zero-cost Docker Compose setup | ✅ Complete |

**Target Customer:** 5 pilot commodity exporter accounts by end of Phase 1.

---

### Phase 2: Advanced Integration (Q1 2027)
- **SWIFT MT700 Series Parser:** Native ingestion of raw SWIFT Category 7 messages (MT700/707) to automate L/C clause extraction without intermediary OCR.
- **Vessel Tracking API Integration:** Direct live-feed integration with MarineTraffic / AISHub commercial APIs for real-time geospatial validation.
- **Automated MT734 Generation:** Auto-drafting standard SWIFT Notice of Refusal messages directly from Sentinel's discrepancy matrix.

---

### Phase 3 — Enterprise Integration (Months 10–18)
**Scope:** Production-grade ERP & Core Banking integration

| Feature | Description |
|---|---|
| SAP Trade Finance connector | Webhook integration with SAP S/4HANA Global Trade Management (GTM) module |
| Core banking API (BRI/Mandiri/BNI) | Pre-debit validation before DHE SDA account placement — zero-penalty compliance |
| Bank Indonesia BI-FAST/SKNBI reporting | Automated Laporan DHE SDA pre-filled from Sentinel findings |
| Multi-tenant SaaS architecture | Isolated per-customer rule sets, audit trail, SOC 2 Type II-ready logging |
| Realtime AIS stream integration | Replace AISHub snapshots with live MarineTraffic/AISHub stream subscription |
| Portfolio-level dashboard | Aggregated compliance KPIs per exporter: LC acceptance rate, DHE SDA variance, price trend vs. benchmark |

---

## License

MIT License. Synthetic data only — no real customer PII or actual trade documents.

---

*TradeFlow Sentinel — Built for the Hacktiv8 × IBM National Hackathon 2026.*
*Financial Theme (Primary) · Productivity & Smart Business (Secondary).*
*IBM watsonx Orchestrate + Langflow + IBM Bob.*
