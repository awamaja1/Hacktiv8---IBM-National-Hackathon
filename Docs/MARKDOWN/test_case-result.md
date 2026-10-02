# Hai Bob, tolong jalankan audit kepatuhan untuk dokumen pengapalan batu bara ini menggunakan aturan PADG_16_2026. Fokus pada validasi instrumen DHE SDA.

{
  "case_id": "TEST_BUG_HUNTER",
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
      "nominated_bank": "PT Bank Mandiri",
      "bank_category": "STATE_OWNED_BANK",
      "placement_type": "Special FX Account (Reksus DHE SDA)",
      "requested_fx_conversion_pct": 50,
      "hold_period_months": 3
    }
  }
}

---

**Status:** active  **Date:** 2026-10-01

---

### 👤 User

Hai Bob, tolong jalankan audit kepatuhan untuk dokumen pengapalan batu bara ini menggunakan aturan PADG_16_2026. Fokus pada validasi instrumen DHE SDA.

{
  "case_id": "TEST_BUG_HUNTER",
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
      "nominated_bank": "PT Bank Mandiri",
      "bank_category": "STATE_OWNED_BANK",
      "placement_type": "Special FX Account (Reksus DHE SDA)",
      "requested_fx_conversion_pct": 50,
      "hold_period_months": 3
    }
  }
}

---

### 🤖 Assistant

> 🔧 called: mcp__lf-starter_project__tradeflow_sentinel_compliance



> 🔧 **mcp__lf-starter_project__tradeflow_sentinel_compliance** — {
  "case_id": "TEST_BUG_HUNTER",
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
      "nominated_bank": "PT Bank Mandiri",
      "bank_category": "STATE_OWNED_BANK",
      "placement_type": "Special FX Account (Reksus DHE SDA)",
      "requested_fx_conversion_pct": 50,
      "hold_period_months": 3
    }
  }
}

### 🤖 Assistant

Berikut ringkasan sintesis kepatuhan penuh berdasarkan hasil audit deterministik dari TradeFlow Sentinel.

---

## ❌ Audit Kepatuhan — `TEST_BUG_HUNTER` | Status: **DISCREPANT**

> **Aturan aktif:** DHE SDA `PADG_16_2026` · **Waktu proses:** 18.3 ms · **Diskrepansi ditemukan:** 3

---

### ✅ Pemeriksaan yang Lulus

| Standar | Detail | Status |
|---|---|---|
| **UCP 600 Art. 18** | Commercial Invoice — format, pihak, mata uang, nilai FOB sesuai | ✅ PASS |
| **SOLAS** | IMO Number `9811000` — checksum valid | ✅ PASS |

---

### ❌ Diskrepansi yang Ditemukan

#### 1. 🚢 Predated Bill of Lading — Pelanggaran UCP 600 Art. 20

- **Temuan:** Kapal **MV KALIMANTAN BULK** (IMO `9811000`) tercatat berada **209.97 NM dari Tanjung Priok, Jakarta** pada tanggal *on-board* yang tertera di BoL (`2026-09-28`). Verifikasi posisi melalui AISHub membuktikan kehadiran fisik kapal di pelabuhan muat **tidak mungkin terjadi** pada tanggal tersebut.
- **Implikasi UCP 600 Art. 20:** BoL harus menunjukkan tanggal *on-board* yang otentik sesuai posisi aktual kapal. BoL yang predated merupakan dokumen cacat dan **tidak dapat diterima** di bawah L/C.
- **Tindakan:** Minta koreksi tanggal *on-board* yang sesuai dengan posisi AIS aktual kapal, atau konfirmasi manifest pelabuhan secara independen.

---

#### 2. 💰 Deviasi Harga Melampaui Toleransi — Pelanggaran ISBP 745 / World Bank Pink Sheet

- **Temuan:** Harga faktur **USD 105/MT** versus harga benchmark World Bank Pink Sheet **USD 72/MT** — deviasi **+45.83%**, jauh melampaui toleransi L/C **±10%**.
- **Implikasi:** Di bawah ISBP 745, harga yang tidak wajar dibandingkan harga pasar internasional dapat mengindikasikan *over-invoicing*, yang berpotensi melanggar regulasi devisa dan ketentuan anti-pencucian uang.
- **Tindakan:** Sediakan justifikasi harga (quality certificate, independent surveyor report, atau kontrak jangka panjang) atau sesuaikan harga ke kisaran yang dapat dibuktikan.

---

#### 3. 🏦 Periode Penempatan DHE SDA Tidak Memenuhi Syarat — Pelanggaran PADG No. 16/2026

- **Temuan:** Periode penempatan DHE SDA yang diajukan adalah **3 bulan**, sedangkan regulasi **PADG No. 16/2026** mewajibkan **minimum 12 bulan**.
- **Implikasi:** Eksportir SDA (termasuk batu bara HS 2701.12) **wajib menempatkan** Devisa Hasil Ekspor di Rekening Khusus DHE SDA pada bank devisa teregulasi selama minimal 12 bulan. Penempatan 3 bulan **tidak sah** dan dapat mengakibatkan sanksi administratif dari Bank Indonesia.
- **Catatan tambahan:** Walaupun bank penerima (**PT Bank Mandiri**, kategori *State-Owned Bank*) sudah sesuai, dan jenis penempatan (*Special FX Account / Reksus DHE SDA*) juga tepat, **durasi 3 bulan harus dikoreksi menjadi 12 bulan**.

---

### ⚠️ Guardrail Warning

> **GUARDRAIL_2 — Numerical Faithfulness:** Parameter `requested_fx_conversion_pct: 50%` tidak dikonfirmasi secara eksplisit dalam output sintesis. Nilai ini perlu divalidasi secara terpisah terhadap ketentuan konversi minimum yang berlaku di PADG No. 16/2026.

---

### 📋 Rekomendasi Akhir

Sesuai **UCP 600 Art. 16**, bank penerbit **berhak menolak** presentasi dokumen ini karena terdapat diskrepansi material. Langkah-langkah wajib sebelum re-presentasi:

1. **Perbaiki tanggal on-board BoL** — sinkronkan dengan data posisi AIS aktual kapal.
2. **Dukung atau koreksi harga USD 105/MT** — sertakan bukti kontrak atau laporan surveyor independen.
3. **Perpanjang periode penempatan DHE SDA menjadi 12 bulan** — sesuai kewajiban regulatoris PADG No. 16/2026.

---

*Diproses oleh TradeFlow Sentinel · IBM watsonx Orchestrate + Langflow + IBM Bob · Waktu manual ~45 menit → Sentinel 18.3 ms (pengurangan >99.9%)*

---

### 👤 User

Bob, saya baru saja menerima ekstraksi data OCR dokumen pengapalan batu bara. Tolong periksa apakah data ini patuh terhadap aturan PADG_16_2026 dan cek proksimitas AIS kapalnya.

{
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

---

### 🤖 Assistant

> 🔧 called: mcp__lf-starter_project__tradeflow_sentinel_compliance



> 🔧 **mcp__lf-starter_project__tradeflow_sentinel_compliance** — {
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

### 🤖 Assistant

## ❌ Audit Kepatuhan — `LIVE_DEMO_COAL` | Status: **DISCREPANT**

> **Aturan aktif:** DHE SDA `PADG_16_2026` · **Waktu proses:** 5.1 ms · **Diskrepansi ditemukan:** 5

---

### ✅ Pemeriksaan yang Lulus

| Standar | Detail | Status |
|---|---|---|
| **UCP 600 Art. 18** | Commercial Invoice — format, pihak, mata uang, nilai FOB sesuai | ✅ PASS |
| **SOLAS** | IMO Number `9811000` — checksum valid | ✅ PASS |

---

### ❌ Mendeteksi 5 Pelanggaran Kritis secara simultan

---

#### 1. 🚢 Predated Bill of Lading — Pelanggaran UCP 600 Art. 20 + AISHub

- **Temuan:** Kapal **MV KALIMANTAN BULK** (IMO `9811000`) terdeteksi berada **209.97 NM dari Tanjung Priok, Jakarta** pada tanggal *on-board* yang tercantum di BoL. Verifikasi AIS membuktikan kehadiran fisik kapal di pelabuhan muat **tidak mungkin terjadi** pada `2026-09-28`.
- **Implikasi:** BoL yang memuat tanggal *on-board* palsu atau prematur adalah dokumen cacat di bawah **UCP 600 Art. 20** dan **wajib ditolak** oleh bank penerbit sesuai Art. 16.
- **Tindakan:** Validasi posisi AIS aktual kapal dan perbaiki tanggal *on-board* dengan bukti fisik yang dapat diverifikasi.

---

#### 2. 💰 Deviasi Harga Melampaui Toleransi — Pelanggaran ISBP 745 / World Bank Pink Sheet

- **Temuan:** Harga faktur **USD 105/MT** vs. benchmark World Bank Pink Sheet **USD 72/MT** — deviasi **+45.83%**, jauh di atas toleransi L/C **±10%**.
- **Implikasi:** Deviasi harga ekstrem mengindikasikan risiko *over-invoicing* yang dapat melanggar regulasi anti-pencucian uang dan ketentuan devisa.
- **Tindakan:** Lampirkan dokumen pendukung harga (kontrak jangka panjang, laporan surveyor independen, atau sertifikat kualitas) yang membenarkan harga tersebut.

---

#### 3. 💱 Persentase Konversi FX Melebihi Batas — Pelanggaran PADG No. 16/2026

- **Temuan:** `requested_fx_conversion_pct` yang diajukan adalah **80%**, sedangkan **PADG No. 16/2026 menetapkan batas maksimum 50%**.
- **Implikasi:** Permintaan konversi FX di atas 50% tidak sesuai dengan ketentuan repatriasi devisa hasil ekspor SDA.
- **Tindakan:** Koreksi persentase konversi FX menjadi **≤ 50%** sesuai ketentuan regulatoris.

---

#### 4. 🏦 Bank Penerima Bukan Bank Himbara — Pelanggaran PADG No. 16/2026

- **Temuan:** Bank yang dinominasikan adalah **PT Bank CIMB Niaga Tbk** dengan kategori `PRIVATE_BANK`. PADG No. 16/2026 **secara eksklusif** membatasi penempatan DHE SDA hanya pada bank-bank Himbara berikut:
  - PT Bank Rakyat Indonesia (BRI)
  - PT Bank Negara Indonesia (BNI)
  - PT Bank Mandiri
  - PT Bank Tabungan Negara (BTN)
- **Implikasi:** Penempatan di bank swasta **tidak sah** dan tidak memenuhi kewajiban repatriasi DHE SDA.
- **Tindakan:** Ganti bank penerima dengan salah satu dari empat bank Himbara di atas.

---

#### 5. 📄 Jenis Rekening Tidak Sesuai — Pelanggaran PADG No. 16/2026

- **Temuan:** Jenis penempatan yang diajukan adalah `"Regular FX Account"`, bukan rekening khusus yang diwajibkan. PADG No. 16/2026 mensyaratkan penempatan pada **Rekening Khusus DHE SDA (Reksus DHE SDA)**.
- **Implikasi:** Rekening biasa tidak memberikan proteksi regulatoris dan tidak memenuhi persyaratan pelacakan devisa hasil ekspor SDA oleh Bank Indonesia.
- **Tindakan:** Ganti jenis penempatan menjadi **"Special FX Account (Reksus DHE SDA)"**.

---

### 📊 Ringkasan Scorecard

| Pemeriksaan | Standar | Status |
|---|---|---|
| UCP 600 Art. 18 — Commercial Invoice | UCP 600 | ✅ PASS |
| UCP 600 Art. 20 — Bill of Lading | UCP 600 | ❌ FAIL |
| AISHub Vessel Proximity | Fisik / AIS | ❌ FAIL |
| SOLAS IMO Checksum | SOLAS | ✅ PASS |
| World Bank Pink Sheet — Harga | ISBP 745 | ❌ FAIL |
| DHE SDA Bank + Rekening + FX % | PADG_16_2026 | ❌ FAIL |

---

### 📋 Matriks Koreksi Wajib

| # | Masalah | Data Saat Ini | Koreksi yang Diperlukan |
|---|---|---|---|
| 1 | Tanggal on-board BoL | `2026-09-28` (tidak valid secara AIS) | Sesuaikan dengan posisi AIS aktual |
| 2 | Harga batu bara | USD 105/MT (+45.83%) | Justifikasi atau koreksi ke ≤ USD ~79/MT |
| 3 | Konversi FX | 80% | ≤ 50% |
| 4 | Nama bank | PT Bank CIMB Niaga Tbk | BRI / BNI / Mandiri / BTN |
| 5 | Jenis rekening | Regular FX Account | Reksus DHE SDA |

> ⚠️ **Dokumen ini tidak dapat dipresentasikan di bawah L/C** hingga seluruh 5 diskrepansi di atas diselesaikan. Presentasi ulang baru dapat dilakukan setelah semua perbaikan diverifikasi.

---

*Diproses oleh TradeFlow Sentinel · IBM watsonx Orchestrate + Langflow + IBM Bob · Waktu manual ~45 menit → Sentinel 5.1 ms (pengurangan >99.9%)*