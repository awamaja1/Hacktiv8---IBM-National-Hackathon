# 🛡️ TradeFlow Sentinel — Phase 2 Semifinal

**Adaptive Trade Finance & DHE SDA Compliance Automation**  
IBM SkillsBuild National Hackathon 2026 — *Financial / Productivity & Smart Business*

> **"From 45-minute manual review to sub-7 ms automated audit — zero L/C discrepancy fees, full DHE SDA legal compliance, and practitioner-validated ROI."**

---

## 🏆 Hackathon Context

| Attribute | Value |
|---|---|
| **Stage** | Phase 2 — Top 25 Semifinal |
| **Theme** | FINANCIAL (Primary) / PRODUCTIVITY & SMART BUSINESS (Secondary) |
| **IBM Stack** | IBM Bob + IBM Langflow (9-Node MCP Flow) + IBM watsonx.ai (`ibm/granite-3-3-8b-instruct`) + IBM watsonx Orchestrate (OpenAPI 3.0.1) |
| **Default Mode** | `USE_MOCK_LLM=true` — **0 Bobcoins consumed** for all demo/judging runs |

---

## 🎯 Business Problem

Indonesia's commodity exporters (CPO, Coal, Palm Oil) collectively lose **USD 100–150 per L/C presentation** due to documentary discrepancies under **UCP 600 Art. 16**, with **65–80% of global presentations failing on first submission** (ICC Banking Commission Briefing No. 3). Simultaneously, since 2026-06-01, all exporters with FOB ≥ USD 250,000 must comply with **PADG BI No. 16/2026** (exclusive Himbara Reksus placement + 50% FX cap) and **PMK No. 73/2023** (PEB blocking by DJBC) — with penalties including suspension of export services.

TradeFlow Sentinel eliminates this dual risk through a **sub-7 ms automated pre-submission audit** that checks 6 compliance dimensions simultaneously.

---

## 🧭 Dual-Track Change Management Strategy

*Based on John P. Kotter's **Leading Change** (Harvard Business School Press, 1996)*

### Track 1 — Leading by Enforce (Executive / CFO / Treasury Level)

**Urgency Signal:** Regulatory non-compliance is now existential, not optional.

| Regulation | Key Mandate | Enforcement |
|---|---|---|
| **PADG BI No. 16/2026 Pasal 21** | Export proceeds **must** be placed in Reksus DHE SDA accounts at Himbara banks only (BRI, BNI, Mandiri, BTN) — LPEI and all private/foreign banks **excluded** effective 2026-06-01 | Bank Indonesia monetary sanctions |
| **PADG BI No. 16/2026 Pasal 38A** | Maximum **50% FX conversion cap** — exporters may not convert more than half of retained proceeds to IDR; remainder must stay in foreign currency | BI real-time monitoring via SKNBI/RTGS |
| **PMK No. 73/2023 (DJBC Bea Cukai)** | Non-compliant DHE SDA exporters face **suspension of PEB (Pemberitahuan Ekspor Barang)** — effectively blocking all future export shipments | Automated DJBC system interlock |
| **UCP 600 Art. 16** | Banks **must** refuse non-compliant document presentations — no discretion, no workaround | Issuing bank refuses payment; exporter bears demurrage + re-submission cost |

**KPI Enforcement:**
- Eliminate **USD 100–150 per-shipment L/C discrepancy fee** (Art. 16 refusal cost)
- Achieve **100% first-presentation compliance rate** for documents prepared with TradeFlow Sentinel
- Reduce DHE SDA regulatory risk to **zero documented violations** per quarter

**Executive Pitch (30 seconds):** *"Each rejected L/C costs your company USD 100–150 in bank fees, 3–7 days of demurrage, and reputational risk with the issuing bank. Our system catches every discrepancy in under 7 milliseconds — before you print a single document. The ROI is 99.9%+ on time alone."*

---

### Track 2 — Leading by Comfortable (Operational Exim Staff Level)

**Urgency Signal:** Manual review is 45 minutes of error-prone eye-strain per shipment set.

**TradeFlow Sentinel removes friction at every step:**

| Manual Process | With TradeFlow Sentinel |
|---|---|
| 45-min manual cross-check of LC MT700 vs Invoice vs BoL fields | **< 7 ms** 1-click audit with colour-coded Pass/Fail cards |
| Excel spreadsheet for DHE SDA eligibility check | **Zero-JSON form** — just fill Seller/Bank/FX% and click |
| Calling compliance team for DHE rule version question | **1-click hot-swap dropdown** — PADG_16_2026 / PP_8_2025 / BASELINE_PRE_2025 |
| Manual calculation of World Bank price deviation | **Automatic** ± deviation % vs real benchmark, shown in Remediation Table |
| No feedback loop when BoL is predated | **AISHub Haversine alert** — vessel position verified to 2 decimal NM precision |
| Waiting for IBM Bob IDE access | **Portable Web UI** — works on any phone, tablet, or laptop at `http://<VPS_IP>:8000/` |

**Staff Benefit Statement:** *"You'll never need to open a JSON file or remember which DHE rule is active today. Just fill the form, click Audit, and you get a printable compliance report in under one second."*

---

## 🏗️ Architecture

```
Browser / Phone / Tablet
        │
        ▼ HTTP GET /  (Portable Web UI — Tab 1/2/3)
┌─────────────────────────────────────────────────┐
│  TradeFlow Sentinel FastAPI  (:8000)             │
│  ┌─────────────────────────────────────────────┐ │
│  │ POST /verify-trade-documents                │ │
│  │ GET  /presets                               │ │
│  │ POST/GET /validation-feedback               │ │
│  │ GET  /health                                │ │
│  │                                             │ │
│  │  Guardrail 1 → Deterministic Engine →       │ │
│  │  IBM Bob Synthesis → Guardrail 2            │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
        ▲
        │ HTTP POST (via extra_hosts: host.docker.internal)
        │
┌─────────────────────────────────────────────────┐
│  IBM Langflow  (:7860)                           │
│  9-Node MCP Flow:                               │
│  [Intent & Payload Extractor x3] →              │
│  [API Message Payload Builder] →                │
│  [API Request] →                                │
│  [⚖️ Sentinel Compliance Checker] →             │
│  [📋 Report Formatter] →                        │
│  [📄 Compliance Report Output]                  │
└─────────────────────────────────────────────────┘
        │
        ▼ (USE_MOCK_LLM=false only)
┌─────────────────────────────────────────────────┐
│  IBM watsonx.ai — ibm/granite-3-3-8b-instruct   │
│  temperature=0.0 | max_new_tokens=1024          │
│  Guardrail 2 anchored numerics in prompt        │
└─────────────────────────────────────────────────┘
```

---

## 🔬 Compliance Engine — 6 Checks

| # | Check | Standard | Deterministic |
|---|---|---|---|
| 1 | **UCP 600 Art. 18** | Commercial Invoice vs LC MT700 | ✅ Python |
| 2 | **UCP 600 Art. 20** | Bill of Lading vs LC MT700 | ✅ Python |
| 3 | **AISHub Haversine** | Vessel position on on-board date (NM) | ✅ Python `haversine_nm()` |
| 4 | **SOLAS IMO Checksum** | 7-digit IMO mod-10 validation | ✅ Python `solas_imo_checksum()` |
| 5 | **World Bank Pink Sheet** | Unit price deviation % vs 2025-Q4 benchmark | ✅ Python |
| 6 | **Versioned DHE SDA** | `PADG_16_2026` / `PP_8_2025` / `BASELINE_PRE_2025` | ✅ Python |

---

## 🧪 Test Cases

### CASE 1 — Compliant CPO Export (All 6 checks PASS)
| Field | Value |
|---|---|
| Commodity | Crude Palm Oil (HS 1511.10) |
| L/C Amount | USD 1,820,000 |
| Vessel | MV BORNEO STAR (IMO 9315460) |
| AISHub Distance | **1.1 NM** from Tanjung Perak |
| Price Deviation | **0.0%** (USD 910/MT = World Bank benchmark) |
| DHE SDA | Bank Mandiri Reksus, 40% FX (≤ 50% cap) ✅ |

### CASE 2 — Discrepant Coal Export (4 checks FAIL)
| Check | Finding |
|---|---|
| AISHub Proximity | MV KALIMANTAN BULK was **209.97 NM** from Tanjung Priok on declared BoL date — PREDATED |
| World Bank Price | USD 105/MT vs benchmark USD 72/MT → **+45.83% deviation** (tolerance ±10%) |
| DHE Bank | PT Bank CIMB Niaga (PRIVATE_BANK) — not Himbara under PADG_16_2026 |
| DHE FX Cap | **80% requested** > 50% maximum cap under PADG_16_2026 Pasal 38A |

---

## 🚀 Quick Start

### Local (Development)
```bash
cd tradeflow-sentinel
cp .env.example .env
# Edit .env — set LANGFLOW_SUPERUSER_PASSWORD

docker compose up -d --build
# Portable UI: http://localhost:8000/
# API Docs:   http://localhost:8000/docs
# Langflow:   http://localhost:7860/
```

### IDCloudHost Cloud VPS (Production)
```bash
cd tradeflow-sentinel
chmod +x deploy_idcloudhost.sh
./deploy_idcloudhost.sh
# → Automatically generates LANGFLOW_SECRET_KEY (Fernet 32-byte)
# → Sets LANGFLOW_SSRF_PROTECTION_ENABLED=false
# → Starts containers, waits for health checks
# → Prints public access URLs
```

### CLI Smoke Test (0 Docker)
```bash
cd tradeflow-sentinel
pip install fastapi uvicorn pydantic

# CASE 1 — Compliant CPO
python langflow_sentinel_engine.py run CASE_1_COMPLIANT_CPO

# CASE 2 — Discrepant Coal
python langflow_sentinel_engine.py run CASE_2_DISCREPANT_COAL

# CASE 2 with alternate DHE rule
python langflow_sentinel_engine.py run CASE_2_DISCREPANT_COAL --dhe-version PP_8_2025

# JSON output
python langflow_sentinel_engine.py run CASE_1_COMPLIANT_CPO --json | python -m json.tool
```

### API Test (requires running server)
```bash
# Health
curl http://localhost:8000/health

# Case 1 — Compliant CPO
curl -s -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{"case_id":"CASE_1_COMPLIANT_CPO","dhe_rule_version":"PADG_16_2026"}' \
  | python3 -m json.tool

# Case 2 — Discrepant Coal
curl -s -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{"case_id":"CASE_2_DISCREPANT_COAL","dhe_rule_version":"PADG_16_2026"}' \
  | python3 -m json.tool

# Hot-swap DHE rule (no restart)
curl -s -X POST http://localhost:8000/verify-trade-documents \
  -H "Content-Type: application/json" \
  -d '{"case_id":"CASE_2_DISCREPANT_COAL","dhe_rule_version":"PP_8_2025"}' \
  | python3 -m json.tool

# Presets (for Web UI dynamic loading)
curl http://localhost:8000/presets | python3 -m json.tool

# Submit practitioner feedback
curl -s -X POST http://localhost:8000/validation-feedback \
  -H "Content-Type: application/json" \
  -d '{"name_initials":"BW","role_title":"Trade Finance Manager","company_type":"Bank Trade Finance (BUMN)","scenario_tested":"CASE_2_DISCREPANT_COAL","usability_score":5,"benefit_score":5,"testimonial":"Sangat membantu mendeteksi predated BoL yang tidak terlihat secara manual"}' \
  | python3 -m json.tool

# Retrieve all feedback
curl http://localhost:8000/validation-feedback | python3 -m json.tool
```

---

## 📁 File Structure

```
tradeflow-sentinel/
├── langflow_sentinel_engine.py          # ✅ Core engine + FastAPI (Phase 2 upgraded)
├── tradeflow_sentinel_portable_ui.html  # ✅ NEW — Portable Web UI (Tab 1/2/3)
├── synthetic_data_and_rules.json        # Test cases, DHE rules, benchmarks, AISHub data
├── TradeFlow Sentinel Compliance Tool.json  # 9-node Langflow MCP flow
├── langflow_component.py                # Langflow CustomComponent wrapper
├── component_input.py                   # Langflow input component
├── component_engine.py                  # Langflow engine component
├── component_output.py                  # Langflow output component
├── orchestrate_skill_openapi.json       # watsonx Orchestrate OpenAPI 3.0.1 skill
├── docker-compose.yml                   # ✅ Phase 2 upgraded (extra_hosts, UI mount)
├── .env.example                         # ✅ Phase 2 upgraded (SSRF=false, UI_FILE)
├── deploy_idcloudhost.sh                # ✅ NEW — 1-command IDCloudHost VPS deploy
├── AGENT.md                             # IBM Bob agent persona & guardrail definitions
└── validation_feedback_log.json         # Auto-created on first feedback submission
```

---

## 🔒 Security & Guardrails

### Guardrail 1 — Input Sanitisation
- **PII Masking:** Bank account numbers (≥10 digits) → `[ACCT_REDACTED_XXXX]`, emails → `[EMAIL_REDACTED]`
- **Prompt Injection Blocking:** DAN, role-override, `<|im_start|>` patterns → HTTP 422 rejection
- Test: enter `ignore previous instructions` in Goods Description field → see GUARDRAIL_1_BLOCKED

### Guardrail 2 — Output Numerical Faithfulness
- All key figures (Haversine distance NM, price deviation %, FX conversion %) must appear **verbatim** in synthesis
- Post-synthesis scan appends `⚠️ GUARDRAIL 2 WARNINGS` if any anchor number is missing
- Temperature `0.0` on live Granite model to minimise hallucination

---

## 💰 ROI Calculation

| Metric | Value |
|---|---|
| Manual baseline | 45 min = 2,700 seconds per shipment |
| TradeFlow Sentinel | < 7 ms |
| Time reduction | > 99.9% |
| L/C discrepancy fee avoided | USD 100–150 per presentation (ICC Art. 16) |
| DHE penalty avoided | PEB suspension (DJBC) + BI monetary sanction |
| Scale (Indonesia 2025) | ~500,000 L/C presentations/year × 65% first-fail rate |

---

## 🌐 DHE SDA Regulatory Timeline

| Version | Legal Basis | Effective | Retention | Hold | FX Cap | Eligible Banks |
|---|---|---|---|---|---|---|
| `BASELINE_PRE_2025` | PP No. 36/2023 | 2023-07-01 | 30% | 3 months | None (100% free) | Any Bank Devisa / LPEI |
| `PP_8_2025` | PP No. 8/2025 + PBI 3/2025 | 2025-03-01 | 100% | 12 months | None (100% free) | Any Bank Devisa / LPEI |
| `PADG_16_2026` (**Active**) | PADG No. 16/2026 | 2026-06-01 | 100% | 12 months | **Max 50% to IDR** | **Reksus DHE SDA — Himbara only** (BRI, BNI, Mandiri, BTN) |

---

## 🤝 Practitioner Validation (Komdigi Evidence)

Phase 2 includes an in-app **Practitioner Validation Feedback Collector** (Tab 3 of the Portable Web UI) that:
- Captures: Name/Initials, Role/Title, Company Type, Scenario Tested, Usability Score (1–5), Benefit Score (1–5), Testimonial
- Submits to `POST /validation-feedback` (saved to `validation_feedback_log.json`)
- Generates a **ready-to-paste Markdown table row** for the Practitioner Validation Matrix in the Komdigi consultation report

---

## 📞 Team & Acknowledgements

**IBM SkillsBuild National Hackathon 2026 — Phase 2 Semifinal Submission**  
Powered by: IBM Bob · IBM Langflow · IBM watsonx.ai (Granite 3.3 8B Instruct) · IBM watsonx Orchestrate  
Regulatory Framework: ICC UCP 600 · ISBP 745 · PADG BI No. 16/2026 · PMK No. 73/2023 · PP No. 8/2025 · World Bank Pink Sheet
