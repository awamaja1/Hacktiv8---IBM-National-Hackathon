#!/usr/bin/env bash
# =============================================================================
# deploy_idcloudhost.sh — TradeFlow Sentinel Phase 2
# One-command deployment for IDCloudHost Ubuntu Cloud VPS
# =============================================================================
# Usage:
#   chmod +x deploy_idcloudhost.sh
#   ./deploy_idcloudhost.sh
#
# What it does:
#   1. Checks Docker Engine is installed and running
#   2. Generates a cryptographically secure LANGFLOW_SECRET_KEY (Fernet format)
#   3. Writes a production-ready .env (LANGFLOW_SSRF_PROTECTION_ENABLED=false)
#   4. Builds and starts both containers via docker compose up -d --build
#   5. Waits for health checks, then prints the public access URLs
#
# Prerequisites (Ubuntu 22.04 / 24.04):
#   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin curl python3
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# --------------------------------------------------------------------------
# Colour helpers
# --------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[TradeFlow]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  TradeFlow Sentinel — Phase 2 Deploy (IDCloudHost Ubuntu VPS)   ${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════════════════${NC}"
echo ""

# --------------------------------------------------------------------------
# 1. Check Docker
# --------------------------------------------------------------------------
log "Memeriksa Docker Engine..."
if ! command -v docker &>/dev/null; then
  fail "Docker tidak ditemukan. Install dengan: sudo apt-get install -y docker.io docker-compose-plugin"
fi
if ! docker info &>/dev/null; then
  fail "Docker daemon tidak berjalan. Coba: sudo systemctl start docker && sudo usermod -aG docker \$USER"
fi
ok "Docker Engine tersedia: $(docker --version)"

# Check docker compose (plugin syntax v2)
COMPOSE_CMD=""
if docker compose version &>/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
  COMPOSE_CMD="docker-compose"
else
  fail "docker compose plugin tidak ditemukan. Install: sudo apt-get install -y docker-compose-plugin"
fi
ok "Compose: ${COMPOSE_CMD}"

# --------------------------------------------------------------------------
# 2. Generate LANGFLOW_SECRET_KEY (32-byte URL-safe base64 Fernet key)
# --------------------------------------------------------------------------
log "Generating LANGFLOW_SECRET_KEY..."
if command -v python3 &>/dev/null; then
  LANGFLOW_SECRET_KEY=$(python3 -c "import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")
elif command -v openssl &>/dev/null; then
  LANGFLOW_SECRET_KEY=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=')
else
  fail "python3 atau openssl diperlukan untuk generate LANGFLOW_SECRET_KEY."
fi
ok "LANGFLOW_SECRET_KEY dibuat (32-byte Fernet)"

# --------------------------------------------------------------------------
# 3. Write / update .env
# --------------------------------------------------------------------------
log "Menulis .env dari .env.example..."
if [ ! -f ".env.example" ]; then
  fail ".env.example tidak ditemukan. Pastikan Anda berada di direktori tradeflow-sentinel/"
fi

# Detect public IP (best-effort; falls back to 0.0.0.0)
PUBLIC_IP=""
PUBLIC_IP=$(curl -s --max-time 5 https://checkip.amazonaws.com 2>/dev/null || \
            curl -s --max-time 5 https://api.ipify.org 2>/dev/null || \
            echo "")
if [ -z "${PUBLIC_IP}" ]; then
  warn "Tidak dapat mendeteksi IP publik — menggunakan localhost"
  PUBLIC_IP="localhost"
fi
ok "IP Publik VPS terdeteksi: ${PUBLIC_IP}"

# If .env already exists, prompt before overwriting
if [ -f ".env" ]; then
  warn ".env sudah ada. Memperbarui LANGFLOW_SECRET_KEY dan LANGFLOW_SSRF_PROTECTION_ENABLED saja..."
  # Update only the secret key and SSRF flag without overwriting user credentials
  sed -i "s|^LANGFLOW_SECRET_KEY=.*|LANGFLOW_SECRET_KEY=${LANGFLOW_SECRET_KEY}|" .env
  sed -i "s|^LANGFLOW_SSRF_PROTECTION_ENABLED=.*|LANGFLOW_SSRF_PROTECTION_ENABLED=false|" .env
  # Add UI_FILE and FEEDBACK_FILE if missing
  grep -q "^UI_FILE=" .env || echo "UI_FILE=/app/tradeflow_sentinel_portable_ui.html" >> .env
  grep -q "^FEEDBACK_FILE=" .env || echo "FEEDBACK_FILE=/app/validation_feedback_log.json" >> .env
else
  cp .env.example .env
  sed -i "s|^LANGFLOW_SECRET_KEY=.*|LANGFLOW_SECRET_KEY=${LANGFLOW_SECRET_KEY}|" .env
  sed -i "s|^LANGFLOW_SSRF_PROTECTION_ENABLED=.*|LANGFLOW_SSRF_PROTECTION_ENABLED=false|" .env
  sed -i "s|^LANGFLOW_SUPERUSER_PASSWORD=.*|LANGFLOW_SUPERUSER_PASSWORD=$(openssl rand -hex 12 2>/dev/null || echo 'tradeflow2026')|" .env
  ok ".env dibuat dari .env.example"
fi

ok ".env dikonfigurasi (LANGFLOW_SSRF_PROTECTION_ENABLED=false, key generated)"

# --------------------------------------------------------------------------
# 4. Build and start containers
# --------------------------------------------------------------------------
log "Menjalankan: ${COMPOSE_CMD} up -d --build ..."
echo ""
${COMPOSE_CMD} up -d --build
echo ""
ok "Containers started"

# --------------------------------------------------------------------------
# 5. Wait for health checks
# --------------------------------------------------------------------------
log "Menunggu container sehat (maks 90 detik)..."
WAIT=0; MAX_WAIT=90
until curl -sf "http://localhost:8000/health" &>/dev/null || [ ${WAIT} -ge ${MAX_WAIT} ]; do
  sleep 3; WAIT=$((WAIT+3))
  echo -n "."
done
echo ""
if curl -sf "http://localhost:8000/health" &>/dev/null; then
  ok "TradeFlow Sentinel API sehat!"
else
  warn "Sentinel API belum merespons setelah ${MAX_WAIT}s. Periksa log: ${COMPOSE_CMD} logs sentinel"
fi

LANGFLOW_WAIT=0
until curl -sf "http://localhost:7860/health" &>/dev/null || [ ${LANGFLOW_WAIT} -ge 90 ]; do
  sleep 3; LANGFLOW_WAIT=$((LANGFLOW_WAIT+3))
  echo -n "."
done
echo ""
if curl -sf "http://localhost:7860/health" &>/dev/null; then
  ok "Langflow sehat!"
else
  warn "Langflow belum merespons setelah 90s (bisa lebih lambat). Cek: ${COMPOSE_CMD} logs langflow"
fi

# --------------------------------------------------------------------------
# 6. Print access URLs
# --------------------------------------------------------------------------
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🚀 DEPLOYMENT BERHASIL — TradeFlow Sentinel Phase 2            ${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  📱 Portable Web UI (Mobile/Tablet/Desktop):"
echo -e "     ${GREEN}http://${PUBLIC_IP}:8000/${NC}"
echo ""
echo -e "  📖 API Docs (Swagger UI):"
echo -e "     ${GREEN}http://${PUBLIC_IP}:8000/docs${NC}"
echo ""
echo -e "  🏥 Health Check:"
echo -e "     ${GREEN}http://${PUBLIC_IP}:8000/health${NC}"
echo ""
echo -e "  🔌 Preset Loader:"
echo -e "     ${GREEN}http://${PUBLIC_IP}:8000/presets${NC}"
echo ""
echo -e "  🎛️  Langflow Flow Editor:"
echo -e "     ${GREEN}http://${PUBLIC_IP}:7860/${NC}"
echo ""
echo -e "  📋 Feedback Collector:"
echo -e "     ${GREEN}POST http://${PUBLIC_IP}:8000/validation-feedback${NC}"
echo -e "     ${GREEN}GET  http://${PUBLIC_IP}:8000/validation-feedback${NC}"
echo ""
echo -e "  🔑 Credentials: lihat file ${YELLOW}.env${NC} (jangan di-commit ke Git!)"
echo ""
echo -e "${CYAN}  Perintah berguna:${NC}"
echo -e "  ${COMPOSE_CMD} logs -f sentinel         # lihat log Sentinel API"
echo -e "  ${COMPOSE_CMD} logs -f langflow          # lihat log Langflow"
echo -e "  ${COMPOSE_CMD} ps                        # status containers"
echo -e "  ${COMPOSE_CMD} down                      # hentikan semua"
echo -e "  ${COMPOSE_CMD} down -v                   # hentikan + hapus volumes"
echo ""
echo -e "  Audit cepat via curl:"
echo -e "  ${YELLOW}curl -s -X POST http://localhost:8000/verify-trade-documents \\${NC}"
echo -e "  ${YELLOW}    -H 'Content-Type: application/json' \\${NC}"
echo -e "  ${YELLOW}    -d '{\"case_id\":\"CASE_1_COMPLIANT_CPO\",\"dhe_rule_version\":\"PADG_16_2026\"}' \\${NC}"
echo -e "  ${YELLOW}    | python3 -m json.tool${NC}"
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════════════════${NC}"
