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
| Review time per transaction set | 45 min (2,700 s) | < 5 s | **> 99% reduction** |
| Exact measured reduction | — | 2,700 s → ~0.004 s engine | **99.8% time efficiency gain** |
| DHE SDA rule version switches | Manual policy lookup (hours) | Runtime parameter (`dhe_rule_version`) | Instant |
| Predated BoL detection | Manual AIS cross-check (15–20 min) | Automated Haversine + AISHub snapshot | < 1 s |
| Price manipulation detection | Analyst judgement (subjective) | World Bank Pink Sheet deviation ± tolerance | Deterministic |

**ROI Calculation (exact):**
```
Baseline:          2,700 seconds per transaction set
Sentinel engine:   ~0.004 seconds (4 ms measured)
Reduction:         (2,700 - 0.004) / 2,700 × 100 = 99.9998% ≈ 99.8% (conservative claim)
```

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
- `CASE_2_DISCREPANT_COAL` — HS 2701.12, FOB USD 5,250,000, IMO9811000, 353.4 NM from Tanjung Priok (predated BoL), $105/MT vs $72/MT benchmark (+45.8%), non-Himbara bank, 80% FX → **DISCREPANT** (4 simultaneous violations)

---

## 6. Repository Structure

```
tradeflow-sentinel/
├── AGENT.md                        # IBM Bob Agent role, UCP 600 Art. 5/18/20 rules, 2 Guardrails
├── README_AND_BUSINESS_MODEL.md    # This file
├── orchestrate_skill_openapi.json  # OpenAPI 3.0.1 spec for IBM watsonx Orchestrate custom skill
├── synthetic_data_and_rules.json   # Versioned DHE SDA rules + 2 synthetic cases + benchmarks
├── langflow_component.py           # Langflow custom component (v1 API — loaded by Langflow UI)
├── _sentinel_engine.py             # Deterministic engine + FastAPI endpoint + IBM Bob synthesis
├── .env                            # Active environment config (not committed)
├── .env.example                    # Template — copy to .env and fill in secrets
└── docker-compose.yml              # Zero-cost local Docker: Langflow :7860 + Sentinel API :8000
```

> **Note on file layout:** `langflow_component.py` is the only file Langflow's component scanner
> processes. `_sentinel_engine.py` is placed in the `deactivated/` subdirectory inside the
> container (Langflow skips that folder) and imported lazily at runtime by the component.

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

Expected: `"overall_status": "DISCREPANT"`, `"discrepancy_count": 4`

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

### Run in Langflow UI (Visual Canvas Demo)

Three flows are pre-built and available at **http://localhost:7860** once the stack is running.

| Flow | Case | DHE Rule | Expected |
|---|---|---|---|
| TradeFlow Sentinel — Case 1: Compliant CPO (PADG 16/2026) | `CASE_1_COMPLIANT_CPO` | `PADG_16_2026` | ✅ COMPLIANT — 0 violations |
| TradeFlow Sentinel — Case 2: Discrepant Coal (PADG 16/2026) | `CASE_2_DISCREPANT_COAL` | `PADG_16_2026` | ❌ DISCREPANT — 5 violations |
| TradeFlow Sentinel — Case 2: Regulatory Comparison (PP 8/2025 vs PADG 16/2026) | `CASE_2_DISCREPANT_COAL` | `PP_8_2025` | ❌ DISCREPANT — 2 violations (bank + FX violations removed by older rule) |

**Step-by-step:**

1. Open **http://localhost:7860** — log in with `admin` / `sentinel2025`
2. From the home screen, click any of the three **TradeFlow Sentinel** flows
3. On the canvas you will see two connected nodes:
   ```
   [ TradeFlow Sentinel ] ──► [ Chat Output ]
   ```
4. Click the **▶ Run** button on the **TradeFlow Sentinel** node (top-right corner of the component card) — do **not** use the Playground chat box; this is a source component driven by its own dropdown fields, not by a chat message
5. A green checkmark appears on both nodes when execution completes
6. Click the **Chat Output** node to expand it and read the full compliance report: overall status, discrepancy list, DHE SDA assessment, IBM Bob synthesis, and ROI metrics

**Live regulatory version-switch demo (hackathon highlight):**

1. Open the **Case 2: Regulatory Comparison** flow
2. In the **TradeFlow Sentinel** node, change the `DHE SDA Rule Version` dropdown from `PP_8_2025` to `PADG_16_2026` directly in the component panel
3. Click **▶ Run** again — the violation count increases from 2 to 5 as the stricter PADG 16/2026 bank restriction and FX cap rules activate instantly, with no restart or code change required

**What each violation means in Case 2 (PADG 16/2026):**

| # | Check | Finding |
|---|---|---|
| 1 | UCP 600 Art. 20 | Predated BoL — vessel 209.97 NM from Tanjung Priok on declared on-board date |
| 2 | AISHub proximity | Vessel physically impossible at loading port (> 10 NM threshold) |
| 3 | World Bank price | Invoice $105/MT deviates +45.83% from benchmark $72/MT (tolerance ±10%) |
| 4 | DHE SDA bank | PT Bank CIMB Niaga is not Himbara; PADG 16/2026 mandates BRI/BNI/Mandiri/BTN only |
| 5 | DHE SDA FX cap | Requested 80% FX conversion exceeds PADG 16/2026 maximum 50% |

### CLI (no Docker)
```bash
pip install fastapi uvicorn ibm-watsonx-ai
python _sentinel_engine.py run CASE_1_COMPLIANT_CPO
python _sentinel_engine.py run CASE_2_DISCREPANT_COAL
python _sentinel_engine.py serve --port 8000
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
- Indonesia's trade finance documentary credit volume: approximately **USD 18–22 billion** per year (estimated 8–10% of total export value as LC-financed, consistent with Asian Development Bank trade finance gap data for Southeast Asia).
- Average transaction value: ~USD 500,000 per LC.
- Estimated LC presentations: **~40,000–44,000 per year**.
- At USD 2.50 per audit: **TAM ≈ USD 100,000–110,000 per year** (pay-per-audit only) | **TAM ≈ USD 22M–26M per year** (full SaaS penetration of all presentations).

### SAM — Serviceable Addressable Market
**Definition:** LC presentations involving commodity exports (CPO, coal, nickel, mineral) where DHE SDA compliance is mandatory (FOB ≥ USD 250,000).
- BPS 2025: Top-5 commodity export categories account for ~62% of total non-oil & gas export value.
- Estimated DHE SDA-subject LC presentations: **~25,000–27,000 per year**.
- **SAM ≈ USD 13.5M–15M per year** (SaaS pricing).

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

### Phase 2 — Edge Case Hardening (Months 4–9)
**Scope:** Handle complex LC structures and advanced fraud detection

| Feature | Description |
|---|---|
| Charter Party Bills of Lading | UCP 600 Art. 22 — standalone BoL vs. charterparty BoL detection; ISBP 745 para. E1-E27 |
| Combined Transport Documents | Art. 19 — multimodal BoL where port-of-loading is a CY/CFS, not a vessel |
| Multi-currency invoicing | FX rate normalisation for non-USD LC amounts; tolerance checking in base currency |
| Disguised HS code detection | ML-based HS code vs. goods description consistency scoring (flag likely mis-classification) |
| Partial shipment & transhipment | Automated accumulation check across multiple presentations under the same LC |
| SWIFT MT700 field parser | Direct ingestion of raw SWIFT MT700 message format (fields 31C, 32B, 43P, 43T, 44E/F/B/C) |

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
| ISO 20022 output | Generate `pain.013` (creditor payment activation) pre-filled from compliant findings |

---

## License

MIT License. Synthetic data only — no real customer PII or actual trade documents.

---

*TradeFlow Sentinel — Built for the Hacktiv8 × IBM National Hackathon 2025.*
*Financial Theme (Primary) · Productivity & Smart Business (Secondary).*
*IBM watsonx Orchestrate + Langflow + IBM Bob.*
