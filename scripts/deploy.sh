#!/usr/bin/env bash
# DS-Oracle 云端一键部署脚本
# 用法: 在云端 ds-oracle 目录下执行 ./scripts/deploy.sh [--full]
#   默认: git pull + 重启服务（90% 场景够用）
#   --full: 同时跑 pip install -r requirements.txt（依赖有变更时用）

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${PROJECT_DIR}/venv"
SERVICE_MCP="ds-oracle-mcp"
SERVICE_API="ds-oracle-api"

cd "${PROJECT_DIR}"

echo "▶ DS-Oracle 部署 @ $(date '+%Y-%m-%d %H:%M:%S')"
echo "  项目: ${PROJECT_DIR}"

# 1. 拉代码
BEFORE=$(git rev-parse --short HEAD)
git fetch --quiet origin master
AFTER=$(git rev-parse --short origin/master)
if [ "${BEFORE}" = "${AFTER}" ]; then
    echo "  代码已是最新 (${BEFORE})，跳过 pull"
else
    echo "  ${BEFORE} → ${AFTER}"
    git pull --ff-only origin master
fi

# 2. 依赖（仅 --full 模式）
if [ "${1:-}" = "--full" ] || ! "${VENV}/bin/python" -c "import ephem, ichingshifa" 2>/dev/null; then
    echo "▶ 安装/更新 Python 依赖"
    if [ ! -d "${VENV}" ]; then
        python3 -m venv "${VENV}"
    fi
    "${VENV}/bin/pip" install --quiet -r requirements.txt
fi

# 3. 跑测试（保护性，失败则中止）
if [ -d tests ]; then
    echo "▶ 跑回归测试"
    if ! "${VENV}/bin/python" -m pytest tests/ -q 2>/dev/null; then
        echo "✗ 测试失败，部署中止" >&2
        exit 1
    fi
fi

# 4. 重启服务
echo "▶ 重启 systemd 服务"
for svc in "${SERVICE_MCP}" "${SERVICE_API}"; do
    if systemctl list-unit-files | grep -q "^${svc}.service"; then
        sudo systemctl restart "${svc}"
        sleep 1
        if systemctl is-active --quiet "${svc}"; then
            echo "  ✓ ${svc} 已重启"
        else
            echo "  ✗ ${svc} 启动失败，最近日志:" >&2
            sudo journalctl -u "${svc}" --no-pager -n 20 >&2
            exit 1
        fi
    else
        echo "  - ${svc} 未配置 systemd，跳过"
    fi
done

# 5. 健康检查
echo "▶ 健康检查"
if curl -sf -m 5 "http://127.0.0.1:8811/" -o /dev/null; then
    echo "  ✓ MCP :8811 响应正常"
else
    echo "  ⚠ MCP :8811 未响应（首次启动可能需 5~10 秒）"
fi
if curl -sf -m 5 "http://127.0.0.1:8812/api/v1/chart/systems" -H "X-API-Token: ${API_TOKEN:-}" -o /dev/null; then
    echo "  ✓ API :8812 响应正常"
else
    echo "  ⚠ API :8812 未响应或鉴权失败（看 .env 的 API_TOKENS）"
fi

echo "▶ 部署完成"
