# scripts/

云端运维脚本。

## deploy.sh — 一键部署

**首次部署**（云端没有 venv）：
```bash
git clone https://github.com/gaoxingkele/ziwei-oracle.git ds-oracle
cd ds-oracle
chmod +x scripts/deploy.sh
./scripts/deploy.sh --full      # 首次必须 --full，会建 venv + pip install
```

**日常更新**（每次 git push 后）：
```bash
cd /path/to/ds-oracle
./scripts/deploy.sh             # 默认: pull + 测试 + 重启
```

**依赖有变更时**（修了 requirements.txt 后）：
```bash
./scripts/deploy.sh --full
```

## 脚本做了什么

1. `git pull origin master`（已是最新会跳过）
2. 检测 ephem/ichingshifa 装没装，缺则跑 `pip install -r requirements.txt`（或 `--full` 强制）
3. `pytest tests/` 跑回归测试，失败中止部署
4. `systemctl restart ds-oracle-mcp` + `ds-oracle-api`
5. `curl` 健康检查 :8811 和 :8000

## systemd 服务定义

`/etc/systemd/system/ds-oracle-mcp.service`:
```ini
[Unit]
Description=DS-Oracle MCP Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/ds-oracle
ExecStart=/path/to/ds-oracle/venv/bin/python mcp_server.py --port 8811
Restart=always
Environment=PYTHONIOENCODING=utf-8

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/ds-oracle-api.service`：把 ExecStart 改成 `uvicorn app.main:app --host 0.0.0.0 --port 8000` 即可。

启用：
```bash
sudo systemctl enable --now ds-oracle-mcp ds-oracle-api
```

## 一键自动部署（GitHub Actions 推送后云端自动 pull）

如果想 push 之后云端自动部署，需 SSH key + Actions secret，简单方案见 `.github/workflows/deploy.yml`（如未启用，部署仍是手工 ssh）。
