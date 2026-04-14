# 设备设置接口（Setting API）

> 给设备端开发同学：语音识别的文本原样 POST 上来，服务器用 LLM 校准成规范化格式，存 SQLite（按 `device_id` 键），并回传你，由设备端本地缓存一份。

- **Base URL**：`http://<server>:8000/api/v1/setting`
- **认证**：在 `.env` 配置了 `API_TOKENS` 时需要，两种方式任选其一：
  - Header：`Authorization: Bearer <token>`
  - Query：`?token=<token>`
- **通用请求体**（除 name 外）：
  ```json
  { "device_id": "dev_xxx", "text": "用户原始输入（可能是语音识别）" }
  ```
- **通用响应封装**：
  ```json
  {
    "code": 0,
    "message": "success",
    "data": { "device_id": "...", "field": "birthday", "value": "1970-04-10", "raw": "...", "updated_at": "..." },
    "timestamp": 1700000000
  }
  ```

---

## 端点一览

| 方法 | 路径 | 字段 | 输入示例 → 输出 |
|------|------|------|----------------|
| POST | `/setting/birthday` | 生日（公历） | `"一九七零年四月十号"` / `"1970-4-10"` → `"1970-04-10"` |
| POST | `/setting/birthtime` | 出生时间（24h） | `"早上七点四十"` / `"辰时"` / `"07:40"` → `"07:40"` |
| POST | `/setting/city` | 出生地点 | `"福建永安"` → `"福建省永安市"` |
| POST | `/setting/name` | 姓名（支持拆字） | `"姓双木林、名字叫平凡的凡"` → `"林凡"` |
| POST | `/setting/sex` | 性别 | `"男"` / `"male"` / `"1"` → `1`；`"女"` → `0` |
| GET  | `/setting?device_id=xxx` | 读全部 | — |

---

## 1. 生日 — `POST /setting/birthday`

**输入格式（常见）**：`1970-04-10` / `1970/4/10` / `1970年4月10日` / `一九七零年四月十号` / `70年四月十号`（二位年份由 LLM 判断 19xx 或 20xx）

**请求**
```bash
curl -X POST http://<server>:8000/api/v1/setting/birthday \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"dev_001","text":"一九七零年四月十号"}'
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "device_id": "dev_001",
    "field": "birthday",
    "value": "1970-04-10",
    "raw": "一九七零年四月十号",
    "updated_at": "2026-04-14T03:12:45.123"
  }
}
```

---

## 2. 出生时间 — `POST /setting/birthtime`

**输入格式（常见）**：`07:40` / `7:40` / `早上七点四十` / `下午三点` / `晚上十一点` / `子时`~`亥时`（时辰默认取起始整点：子=23:00 / 丑=01:00 / 寅=03:00 / 卯=05:00 / 辰=07:00 / 巳=09:00 / 午=11:00 / 未=13:00 / 申=15:00 / 酉=17:00 / 戌=19:00 / 亥=21:00）

**请求**
```bash
curl -X POST http://<server>:8000/api/v1/setting/birthtime \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"dev_001","text":"早上七点四十"}'
```

**响应**（节选）
```json
{ "code": 0, "data": { "field": "birthtime", "value": "07:40" } }
```

---

## 3. 出生地点 — `POST /setting/city`

**输出规范**：
- 中国：`省份+市`（如 `福建省永安市`、`北京市`、`新疆维吾尔自治区乌鲁木齐市`）
- 国外：`国家+城市`（如 `日本东京都`、`美国纽约市`）

**请求**
```bash
curl -X POST http://<server>:8000/api/v1/setting/city \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"dev_001","text":"福建永安"}'
```

**响应**（节选）
```json
{ "code": 0, "data": { "field": "city", "value": "福建省永安市" } }
```

---

## 4. 姓名 — `POST /setting/name`

**支持的表达方式**：
- 直接报：`张三`、`李平凡`
- 拆字：`姓双木林、名字叫平凡的凡` → `林凡`；`耳东陈、安全的安` → `陈安`；`弓长张，三横王的王` → `张王`
- 同音确认：`我姓王，三横王`、`草字头的苏`
- 英文名：`My name is John Smith` → `John Smith`

**请求体**（额外支持 `lang`）
```json
{ "device_id": "dev_001", "text": "姓双木林、名字叫平凡的凡", "lang": "zh" }
```
`lang` 可选值：`zh`（默认，纯中文）、`en`（英文，保留空格）

**响应**（节选）
```json
{ "code": 0, "data": { "field": "name", "value": "林凡", "lang": "zh" } }
```

---

## 5. 性别 — `POST /setting/sex`

**输入**：`男` / `男生` / `男性` / `male` / `m` / `boy` / `1` → `1`；`女` / `female` / `0` → `0`

**请求**
```bash
curl -X POST http://<server>:8000/api/v1/setting/sex \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"dev_001","text":"男"}'
```

**响应**（节选）
```json
{ "code": 0, "data": { "field": "sex", "value": 1 } }
```

---

## 6. 读取全部设置 — `GET /setting`

**请求**
```bash
curl "http://<server>:8000/api/v1/setting?device_id=dev_001" \
  -H "Authorization: Bearer $TOKEN"
```

**响应**
```json
{
  "code": 0,
  "data": {
    "device_id": "dev_001",
    "name": "林凡",
    "sex": 1,
    "birthday": "1970-04-10",
    "birthtime": "07:40",
    "city": "福建省永安市",
    "updated_at": "2026-04-14T03:12:45.123"
  }
}
```

若该 `device_id` 没有数据，各字段返回 `null`，不是报错。

---

## 错误码

| code | 含义 | 常见原因 |
|------|------|----------|
| `40001` | 解析失败 | LLM 识别不出输入想表达的内容（文本太离谱、歧义无法消除） |
| `41002` | Token 无效 | `API_TOKENS` 配置了但传的 token 不在列表 |
| `41003` | 缺少 Token | 未传 `Authorization` 头和 `token` query |
| `50001` | LLM 调用异常 | Kimi API 网络/鉴权/超时，稍后重试 |

错误响应结构：
```json
{ "code": 40001, "message": "解析失败: 无法解析生日: ...", "data": null, "timestamp": 1700000000 }
```

---

## 设备端集成建议

1. **缓存本地**：首次调用成功后，把返回的 `data` 整体存到设备本地（LocalStorage / SharedPreferences / 文件）。
2. **按字段提交**：用户只改了生日，就只调 `birthday` 接口。接口是独立的，不需要凑齐 5 个再一次性提交。
3. **展示 raw 帮助校验**：返回的 `raw` 是用户原话，`value` 是服务器理解的规范化值。UI 上可以显示「您说了：『一九七零年四月十号』，已保存为：1970-04-10」让用户确认。
4. **启动时拉一次**：设备启动时调 `GET /setting`，拿到服务器最新的设置并覆盖本地（跨设备同步场景）。
5. **容错**：网络失败时，设备端把原始语音文本暂存在本地队列，联网后重试。

---

## 性能说明

- **快速路径**：如果设备端传来的文本已经是规范格式（`1970-04-10`、`07:40`、`男`、`1`），服务器走正则直接返回，**不调 LLM**，延迟 < 50ms。
- **LLM 路径**：未命中正则时调用 Kimi，典型 500ms ~ 2s（视网络和 prompt 长度）。
- **token 成本**：每次 LLM 调用 < 200 tokens，成本可忽略。

---

## 审计日志

每次调用都会在 `logs/{device_id}/{YYYY-MM-DD}.jsonl` 生成事件，方便调试：
- `request_in` / `response_out` —— HTTP 层
- `setting_update` —— 字段、原始输入、解析值、错误原因
- `llm_request` / `llm_response` —— LLM 调用详情（model、token 消耗、耗时、内容预览）

同一次请求用相同 `trace_id` 串联，查询某次异常时很好用：
```bash
grep '"trace_id":"abc123..."' logs/dev_001/$(date +%F).jsonl | jq .
```
