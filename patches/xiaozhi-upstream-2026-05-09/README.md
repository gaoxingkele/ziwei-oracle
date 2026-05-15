# xiaozhi-server 升级备份 — 2026-05-09

升级目标：`D:\aicoding\xiaozhi-esp32-server\`（同步至 `vendor/xiaozhi-esp32-server/`）
升级方向：`upstream@2026-04-17 + 本地补丁` → `upstream@1e6f0fd（2026-05-08 拉取） + 本地补丁`
upstream 来源：https://github.com/xinnan-tech/xiaozhi-esp32-server （`main` 分支 HEAD `1e6f0fd`，PR#3162）

## 目录结构

- `A-new-files/` — 仅本地存在、上游不存在的整文件
- `B-edits/` — 对上游文件的修改（unified diff）
- `B-snapshots/` — 每个 B-edit 文件的 LOCAL + UPSTREAM 完整快照（用于手工合并）
- `C-kept-files/` — 上游已删但保留备用的文件

## A. 本地新增文件

| 文件 | 说明 |
|---|---|
| `core/handle/textHandler/systemMessageHandler.py` | 处理 `{"type":"system","text":"..."}` 运行时 prompt addon；同时缓存 addon 到 `conn._system_prompt_addon` 供 receiveAudioHandle 读取（mazu 命理首轮 augment 用） |

## B. 对上游文件的本地修改（12 处）

### 简单可机械重应用（upstream 该文件几乎未动 / 仅本地附加）
- `textMessageType.py` — 添加 `SYSTEM = "system"` 枚举
- `textMessageHandlerRegistry.py` — import + 注册 SystemTextMessageHandler
- `helloHandle.py` — hello 消息里读 `system_prompt_addon` 并应用
- `receiveAudioHandle.py` — 两件事：(1) `if conn.is_exiting: return` 早返回；(2) **mazu 首轮 server-side augment**：`_augment_profile`（八字/紫微/西方占星 抽档案+设备ID）+ `_augment_hexagram`（六爻/梅花 抽卦码字面量），仅命理类首轮拼结构化 query 喂 LLM
- `intentHandler.py` — `is_exiting` 不被打断 + 告别后置位
- `abortHandle.py` — `is_exiting` 早返回 + 去掉 `close_after_chat = False` 重置
- `core/providers/asr/base.py` — `is_exiting` 时关闭连接
- `core/providers/asr/fun_local.py` — **修上游 bug** (B12, 2026-05-11)：`lang_tag_filter` 在无标签短音频/噪音输入时返回 str（不是 dict），caller 一律按 dict 取 `["content"]` 触发 `string indices must be integers`。改成 `isinstance` 分流，并把 return 类型从 dict-or-str 收敛到 str（caller 类型注解就是 str）
- `plugins_func/functions/handle_exit_intent.py` — 设 `is_exiting = True`，简化 close_after_chat 守卫
- `core/providers/tools/server_mcp/mcp_manager.py` — MCP 初始化超时 10s → 60s（ngrok/公网必需）

### 上游同时大改、需要手工合并
- `core/connection.py` — 上游 +157/-281 大重构。我们仅追加 2 处：
  1. `__init__` 里加 `self.is_exiting = False  # 标记是否正在执行退出流程`
  2. `_route_message` 顶部加 `if self.is_exiting: return`（含注释 `# 退出状态丢弃所有消息`）
- `config.yaml` — 上游删了 linkerai/ttson 配置块、改了 GizwitsTTS 等。我们仅追加：
  - 在 chat / agent prompt 区段加 "工具调用硬规则" 6 行（命理话题强制 tool_calls，禁口语过渡，禁凭记忆排盘）

## C. 上游已删但本地保留

| 文件 | 是否在用 | 决定 |
|---|---|---|
| `core/providers/tts/linkerai.py` | 否（当前 TTS 是 EdgeTTS） | 保留备用 |
| `core/providers/tts/ttson.py` | 否 | 保留备用 |
| `xiaozhi-server/.claude/settings.local.json` | Claude Code 项目配置 | 保留 |

## 重应用流程

```bash
# 假设刚把官方 main.tar.gz 解压到 xiaozhi-esp32-server 目录后

PATCH_ROOT=D:/aicoding/ds-oracle-cli/patches/xiaozhi-upstream-2026-05-09
TARGET=D:/aicoding/xiaozhi-esp32-server

# 1. 还原 A 新增文件
cp $PATCH_ROOT/A-new-files/systemMessageHandler.py \
   $TARGET/main/xiaozhi-server/core/handle/textHandler/

# 2. 还原 C 保留文件
cp $PATCH_ROOT/C-kept-files/linkerai.py $TARGET/main/xiaozhi-server/core/providers/tts/
cp $PATCH_ROOT/C-kept-files/ttson.py    $TARGET/main/xiaozhi-server/core/providers/tts/
cp -r $PATCH_ROOT/C-kept-files/dot-claude $TARGET/main/xiaozhi-server/.claude

# 3. 重应用 B 简单补丁（9 个）
cd $TARGET
for p in $PATCH_ROOT/B-edits/*.patch; do
  case "$p" in
    *connection.py.patch|*config.yaml.patch) continue ;;  # 这俩手工合并
  esac
  patch -p3 < "$p"   # -p3 跳过 /tmp/xiaozhi-new/ 前缀
done

# 4. 手工合并 connection.py 和 config.yaml
#    参考 B-snapshots/*.LOCAL（我方版本）和 *.UPSTREAM（上游版本）
```
