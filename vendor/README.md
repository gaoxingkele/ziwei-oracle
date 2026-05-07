# vendor/

本地参考用第三方源码副本。**不入 git**（已在根 .gitignore 排除 `vendor/`）。

## xiaozhi-esp32-server/

来源：[xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)
（叠加了本机自定义补丁，非纯净 upstream 状态）

复制时间：2026-05-07
原路径：`D:\aicoding\xiaozhi-esp32-server\`

### 排除清单（仅 .venv / node_modules / .git 三项）

| 目录 | 原大小 | 排除原因 |
|---|---:|---|
| `.venv/` | 2.7 GB | Python 虚拟环境（pip install -r 重建; 但留意 opus.dll 坑）|
| `node_modules/` | — | npm 依赖（npm install 重建）|
| `.git/` | — | 源仓库历史（vendor 不维护 git 历史）|

### 保留内容（约 1.97 GB）

| 路径 | 大小 | 说明 |
|---|---:|---|
| `main/xiaozhi-server/models/` | 1.8 GB | **VAD/ASR/Silero 模型权重** — funasr/silero/sense_voice_small 等，首次启动免下载 |
| `main/xiaozhi-server/test/` | 63 MB | 测试代码 + 音频样本 |
| `main/xiaozhi-server/music/` | 14 MB | 音乐播放素材 |
| `main/xiaozhi-server/tmp/` | 7 MB | 运行时缓存 |
| `main/xiaozhi-server/config/` | 3.5 MB | 默认配置模板 |
| `main/xiaozhi-server/core/` | 1.4 MB | **Python 后端核心** — connection / handle / providers |
| `main/xiaozhi-server/plugins_func/` | 0.2 MB | 插件函数 |
| `main/xiaozhi-server/data/` | 5 KB | ⚠ **含 .config.yaml 用户配置（可能有 API key/token）** |
| `main/manager-api/` | 2.2 MB | Java Spring 后端 |
| `main/manager-mobile/` | 3.9 MB | Flutter 移动端 |
| `main/manager-web/` | 73 MB | Vue 管理后台（不含 node_modules）|
| `docs/` | 13 MB | 项目文档 |

### ⚠ 安全注意事项

`vendor/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml` 通常包含：
- LLM API key（DeepSeek / Kimi / ChatGLM 等）
- TTS API key（EdgeTTS / 阿里云 / 火山等）
- mcp_endpoint token
- 数据库密码

**vendor/ 已在根 .gitignore 排除**，不会推到 GitHub。但本机这份副本仍存在，请注意：
- 屏幕分享/远程协助时不要展示这个文件
- 给别人发本项目压缩包时手动剔除 vendor/data/
- 文件原始位置在 `D:\aicoding\xiaozhi-esp32-server\main\xiaozhi-server\data\`，那里才是单一权威源

### 用途

仅供 ds-oracle 项目开发时**就地查阅** xiaozhi-server 源码（避免跨项目 cd 切换）。
**不要从这里运行 xiaozhi-server**——运行请回到原路径 `D:\aicoding\xiaozhi-esp32-server\`，那里有完整 venv + models + data。

### 同步策略

xiaozhi-server 原项目代码改动后，可重新跑 robocopy 同步：

```powershell
$src = 'D:\aicoding\xiaozhi-esp32-server'
$dst = 'D:\aicoding\ds-oracle-cli\vendor\xiaozhi-esp32-server'
$exclude = @('.venv','venv','__pycache__','models','tmp','node_modules','dist','build','.git','data','music')
robocopy $src $dst /E /XD $exclude /XF *.pyc *.pyo *.log *.bin /MT:8 /R:0
```
