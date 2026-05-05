# 小智 ESP32 接入 DS-Oracle MCP 研究报告

## 1. 小智架构概览

小智（xiaozhi-esp32）是一款基于 ESP32 的 AI 语音助手，采用**设备 + 云服务器**的分体架构：

```
用户语音 → ESP32 设备 ←WebSocket→ xiaozhi-esp32-server ←WebSocket→ MCP Endpoint Server ←stdio/sse/http→ 外部 MCP 工具
                                        ↕
                                   LLM API (Qwen/DeepSeek等)
```

- **ESP32 设备端**：离线唤醒、音频采集、硬件控制
- **xiaozhi-esp32-server**：语音识别(ASR)、大模型推理(LLM)、语音合成(TTS)、工具调度
- **MCP Endpoint Server**：外部 MCP 工具的中继/注册中心

### 关键项目地址

| 项目 | 地址 | 说明 |
|------|------|------|
| 设备固件 | https://github.com/78/xiaozhi-esp32 | ESP32 C/C++ 固件 |
| 云端服务 | https://github.com/xinnan-tech/xiaozhi-esp32-server | Python 后端 |
| MCP 中继 | https://github.com/xinnan-tech/mcp-endpoint-server | MCP Endpoint 中继服务 |
| MCP 桥接 | https://github.com/78/mcp-calculator | mcp_pipe.py 桥接工具 |

---

## 2. 小智的 MCP 工具调用流程

小智支持 5 种工具执行器：

| 类型 | 说明 | 来源 |
|------|------|------|
| ServerPlugin | 服务端内置插件（天气、音乐等） | Python 代码 |
| ServerMCP | 服务端本地 MCP Server | 本地 stdio 进程 |
| DeviceIoT | 设备端 IoT 控制（音量、亮度等） | ESP32 固件 |
| DeviceMCP | 设备端 MCP 工具 | ESP32 固件 |
| **MCPEndpoint** | **外部 MCP 工具（我们的接入点）** | 远程服务 |

### 工具调用时序

```
用户："帮我看看明天适不适合搬家"
    ↓
ESP32 → 语音 → xiaozhi-server
    ↓
ASR 语音转文字
    ↓
LLM 收到文字 + 所有可用 tools 列表（含 DS-Oracle 的 jiri/almanac 等）
    ↓
LLM 决定调用 function: jiri(activity="搬家", start_date="2026-04-03")
    ↓
ToolManager 识别 tool_type=MCP_ENDPOINT → 路由到 MCPEndpointExecutor
    ↓
通过 WebSocket 发送 JSON-RPC tools/call 到 MCP Endpoint Server
    ↓
MCP Endpoint Server 转发到我们的 DS-Oracle MCP 工具进程
    ↓
DS-Oracle 计算结果返回
    ↓
LLM 收到计算结果，生成自然语言解读
    ↓
TTS 合成语音 → ESP32 播放
    ↓
用户听到："明天不太适合搬家哦，最近适合搬家的好日子是4月8号……"
```

### 工具发现机制

小智服务器启动时连接 MCP Endpoint Server，通过 JSON-RPC `tools/list` 自动发现所有注册的工具。工具定义会被转换为 OpenAI function-calling 格式传给 LLM：

```python
# 小智内部转换逻辑
{
    "type": "function",
    "function": {
        "name": "jiri",
        "description": "黄道吉日查询。在日期范围内查找适合特定事项的黄道吉日...",
        "parameters": {
            "type": "object",
            "properties": {
                "activity": {"type": "string", "description": "要查询的事项"},
                "start_date": {"type": "string", "description": "起始日期"},
                "end_date": {"type": "string", "description": "截止日期"}
            },
            "required": ["activity"]
        }
    }
}
```

LLM 根据用户意图自动决定是否调用工具，无需手动配置触发规则。

---

## 3. 接入步骤

### 第一步：部署 MCP Endpoint Server（中继服务）

小智不直接连接外部 MCP Server，而是通过一个 **MCP Endpoint Server** 做中继。

```bash
git clone https://github.com/xinnan-tech/mcp-endpoint-server.git
cd mcp-endpoint-server
docker compose -f docker-compose.yml up -d
docker logs -f mcp-endpoint-server
```

启动后日志会输出两个关键地址：

```
智控台MCP参数配置: http://192.168.1.25:8004/mcp_endpoint/health?key=<KEY>
单模块部署MCP接入点: ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=<TOKEN>
```

> 注意：如果用 Docker 部署，需要将 Docker 内部 IP 替换为宿主机的局域网 IP。

### 第二步：配置 xiaozhi-server 连接 Endpoint

编辑 `data/.config.yaml`：

```yaml
# 开启 function_call 意图模式
selected_module:
  Intent: function_call

Intent:
  function_call:
    type: function_call
    functions:
      - change_role
      - get_weather
      # MCP Endpoint 的工具不需要在这里列出，会自动发现

# MCP 接入点地址
mcp_endpoint: ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=<TOKEN>
```

### 第三步：将 DS-Oracle MCP 桥接到 Endpoint

小智使用 `mcp_pipe.py` 将外部 MCP 工具桥接到 Endpoint Server。支持三种连接方式：

#### 方式 A：stdio 模式（推荐，最简单）

```bash
# 设置 Endpoint 地址
export MCP_ENDPOINT=ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=<TOKEN>

# 直接桥接我们的 MCP Server
python mcp_pipe.py "python /path/to/ds-oracle-cli/mcp_server.py --transport stdio"
```

#### 方式 B：通过 mcp_config.json 配置

创建 `mcp_config.json`：

```json
{
  "mcpServers": {
    "ds-oracle": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/ds-oracle-cli/mcp_server.py", "--transport", "stdio"]
    }
  }
}
```

启动：

```bash
export MCP_ENDPOINT=ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=<TOKEN>
python mcp_pipe.py
```

#### 方式 C：远程 HTTP/SSE 模式

如果 DS-Oracle MCP 部署在远程服务器上：

```json
{
  "mcpServers": {
    "ds-oracle": {
      "type": "http",
      "url": "http://your-oracle-server:8811/mcp"
    }
  }
}
```

或 SSE 模式：

```json
{
  "mcpServers": {
    "ds-oracle": {
      "type": "sse",
      "url": "http://your-oracle-server:8811/sse"
    }
  }
}
```

### 第四步：验证

重启小智服务器，查看日志确认工具已注册：

```
MCP Endpoint connected, discovered 14 tools:
  - ziwei, bazi, meihua, liuyao, astrology, qimen, liuren, iching,
    qianwen, jiemeng, name_analysis, hehun, almanac, jiri
```

对小智说："帮我查一下今天的黄历"，如果 LLM 调用了 `almanac` 工具并返回解读，说明接入成功。

---

## 4. 兼容性详情

### 协议兼容性

| 维度 | DS-Oracle MCP | 小智 MCP Endpoint | 状态 |
|------|--------------|-------------------|------|
| MCP 协议 | JSON-RPC 2.0 | JSON-RPC 2.0 | 兼容 |
| 方法支持 | initialize, tools/list, tools/call | 相同 | 兼容 |
| Tool Schema | 标准 inputSchema | 转换为 OpenAI function format | 兼容 |
| 传输方式 | streamable-http / SSE / stdio | stdio（通过 mcp_pipe 桥接）| 兼容 |

### 注意事项

1. **工具命名**：小智会对工具名做 sanitize（只保留字母数字下划线），我们的工具名（ziwei, bazi 等）都是纯字母，无需担心。

2. **工具描述很重要**：LLM 根据 tool 的 `description` 判断是否调用。我们每个 tool 的描述已经写得很清晰（中文），与中文 LLM（Qwen、DeepSeek）配合良好。

3. **返回值格式**：我们的 tool 返回纯文本（text_summary），LLM 会基于这个文本生成口语化的语音回复，非常适合语音助手场景。

4. **认证**：MCP Endpoint Server 使用 WebSocket URL 中的 token 参数做认证，与我们的 API_TOKENS 是独立的两套机制，互不影响。

---

## 5. 推荐部署架构

### 同机部署（开发/测试）

```
同一台机器:
├── xiaozhi-esp32-server (port 8765 ws + 8003 http, 已避让)
├── mcp-endpoint-server  (port 8004)
├── DS-Oracle MCP        (stdio, 由 mcp_pipe 启动；或 streamable-http :8811)
└── DS-Oracle API        (port 8812, 可选)
```

### 分机部署（生产）

```
服务器A (小智服务):
├── xiaozhi-esp32-server
└── mcp-endpoint-server
    └── 连接到远程 DS-Oracle

服务器B (DS-Oracle):
├── mcp_server.py --transport sse --port 8811   (MCP for 小智)
├── uvicorn app.main:app --port 8812            (API for 小程序/H5)
```

mcp_config.json 配置远程连接：

```json
{
  "mcpServers": {
    "ds-oracle": {
      "type": "sse",
      "url": "http://服务器B-IP:8811/sse"
    }
  }
}
```

---

## 6. 语音交互示例场景

接入完成后，用户可以通过语音与小智进行以下对话：

| 用户说 | 调用的 MCP Tool | 小智回复示例 |
|--------|----------------|-------------|
| "帮我看看今天黄历" | `almanac` | "今天宜嫁娶、纳财、交易，忌开市、盖屋……" |
| "下个月有什么好日子适合搬家" | `jiri(activity="搬家")` | "下个月有3个适合搬家的好日子，分别是……" |
| "帮我算算八字" | `bazi` | "根据您的生辰，四柱为庚午、辛巳……日主属金……" |
| "抽个签吧" | `qianwen` | "您抽到观音灵签第35签，中签。签诗：衣冠重整旧家风……" |
| "昨晚梦到蛇了" | `jiemeng(keyword="蛇")` | "梦见蛇通常象征着……建议您近期……" |
| "帮我看看张伟这个名字好不好" | `name_analysis(name="张伟")` | "张伟这个名字，天格12属木，人格……" |
| "我和女朋友合不合适" | `hehun` | "根据双方八字，合婚评分82分，日干五合……" |
| "帮我起一卦问问工作" | `iching(question="工作")` | "为您起得本卦乾卦，之卦……卦辞说……" |

---

## 7. 参考链接

- 小智 MCP 协议文档：https://github.com/78/xiaozhi-esp32/blob/main/docs/mcp-protocol.md
- 小智 MCP 使用文档：https://github.com/78/xiaozhi-esp32/blob/main/docs/mcp-usage.md
- MCP Endpoint Server：https://github.com/xinnan-tech/mcp-endpoint-server
- MCP Pipe 桥接工具：https://github.com/78/mcp-calculator
- 小智服务端配置：https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/main/xiaozhi-server/config.yaml
- MCP Endpoint 接入文档：https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/mcp-endpoint-integration.md
