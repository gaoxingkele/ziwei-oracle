# 设备设置接口（Setting API）

> 客户端把用户选择/输入的设置项提交到服务器，服务器**直接校验 + 持久化**（不调 LLM）。适合滚轮选择器、表单输入、扫码等场景。

- **Base URL**：`http://<server>:8000/api/v1/setting`
- **认证**：在 `.env` 配置了 `API_TOKENS` 时需要，两种方式任选其一：
  - Header：`Authorization: Bearer <token>`
  - Query：`?token=<token>`
- **通用请求体**（除 name 外）：
  ```json
  { "device_id": "dev_xxx", "text": "<客户端已规范化的值>" }
  ```
- **通用响应封装**：
  ```json
  {
    "code": 0,
    "message": "success",
    "data": { "device_id": "...", "field": "birthday", "value": "1995-03-03", "raw": "...", "updated_at": "..." },
    "timestamp": 1700000000
  }
  ```

> **说明**：`value` 是服务器落库的值，`raw` 是客户端原始提交的 `text`。正常情况二者相等；`sex` / `birthtime` 会做归一化（例如 `7:40` → `07:40`、`男` → `1`）。

---

## 端点一览

| 方法 | 路径 | 字段 | 输入 → 存储 |
|------|------|------|-------------|
| POST | `/setting/birthday` | 生日（公历） | `"1995-03-03"` → `"1995-03-03"`（必须 `YYYY-MM-DD`） |
| POST | `/setting/birthtime` | 出生时间（24h） | `"07:40"` / `"7:40"` → `"07:40"`（必须 `H:MM` 或 `HH:MM`） |
| POST | `/setting/city` | 出生地点 | 任意字符串 → 原样保存（服务端不改写） |
| POST | `/setting/name` | 姓名 | 任意字符串 → 原样保存，`lang` 字段透传 |
| POST | `/setting/sex` | 性别 | `男` / `女` / `male` / `female` / `1` / `0` → 整数 `1` 或 `0` |
| GET  | `/setting?device_id=xxx` | 读全部 | — |

---

## 1. 生日 — `POST /setting/birthday`

**输入要求**：字符串 `YYYY-MM-DD`，年范围 1900~2100，月 1~12，日 1~31。格式不符返回 `40001`。

**请求**
```bash
curl -X POST http://<server>:8000/api/v1/setting/birthday \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"dev_001","text":"1995-03-03"}'
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "device_id": "dev_001",
    "field": "birthday",
    "value": "1995-03-03",
    "raw": "1995-03-03",
    "updated_at": "2026-04-15T07:12:45.123"
  }
}
```

---

## 2. 出生时间 — `POST /setting/birthtime`

**输入要求**：字符串 `H:MM` 或 `HH:MM`（24 小时制，小时 0~23，分钟 0~59）。允许全角冒号 `：`，服务端会补齐为两位小时（`7:40` → `07:40`）。

**请求**
```bash
curl -X POST http://<server>:8000/api/v1/setting/birthtime \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"dev_001","text":"07:40"}'
```

**响应**（节选）
```json
{ "code": 0, "data": { "field": "birthtime", "value": "07:40" } }
```

---

## 3. 出生地点 — `POST /setting/city`

**输入要求**：非空字符串。服务端**原样保存**（不做规范化），客户端可直接传 `"福建永安"` 或 `"福建省永安市"`，存什么返回什么。

**请求**
```bash
curl -X POST http://<server>:8000/api/v1/setting/city \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"dev_001","text":"福建永安"}'
```

**响应**（节选）
```json
{ "code": 0, "data": { "field": "city", "value": "福建永安" } }
```

---

## 4. 姓名 — `POST /setting/name`

**输入要求**：非空字符串。服务端**原样保存**。`lang` 字段作为标签一起回传（`"zh"` / `"en"`，默认 `"zh"`）。

**请求体**
```json
{ "device_id": "dev_001", "text": "林凡", "lang": "zh" }
```

**响应**（节选）
```json
{ "code": 0, "data": { "field": "name", "value": "林凡", "lang": "zh" } }
```

---

## 5. 性别 — `POST /setting/sex`

**输入映射**：

| 传入 `text` | 存储 `value` |
|-------------|--------------|
| `男` / `男生` / `男性` / `male` / `M` / `boy` / `1` / `1`(数字) | `1` |
| `女` / `女生` / `女性` / `female` / `F` / `girl` / `0` / `0`(数字) | `0` |
| 其他 | 返回 `40001` 错误 |

英文大小写不敏感（`MALE`、`Female` 都接受）。

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
    "birthday": "1995-03-03",
    "birthtime": "07:40",
    "city": "福建永安",
    "updated_at": "2026-04-15T07:12:45.123"
  }
}
```

若该 `device_id` 没有数据，各字段返回 `null`，**不是报错**。

---

## 错误码

| code | 含义 | 常见原因 |
|------|------|----------|
| `40001` | 参数校验失败 | 生日/时间格式不符；性别无法映射；字符串为空 |
| `41002` | Token 无效 | `API_TOKENS` 配置了但传的 token 不在列表 |
| `41003` | 缺少 Token | 未传 `Authorization` 头和 `token` query |

错误响应结构：
```json
{ "code": 40001, "message": "生日格式无效，需为 YYYY-MM-DD，收到: 95-3-3", "data": null, "timestamp": 1700000000 }
```

---

## 存储

- 默认 SQLite：`./ds_oracle.db`（表 `user_settings`，主键 `device_id`）
- 生产切 PostgreSQL：`SETTINGS_DB_URL=postgresql+asyncpg://user:pwd@host:5432/db`

---

## 设备端集成建议

1. **客户端先规范化再提交**：生日用滚轮选择器输出 `YYYY-MM-DD`，时间用滚轮输出 `HH:MM`。服务端校验失败 = 客户端 UI 有 bug。
2. **按字段提交**：用户只改了生日，就只调 `birthday`。接口独立，不需要凑齐 5 个。
3. **缓存本地**：成功后把返回的 `data` 存本地（localStorage / SharedPreferences）。
4. **启动同步**：启动时调 `GET /setting`，用非 null 字段覆盖本地（跨设备同步）。
5. **UI 反馈**：返回的 `value` 是真正存到库里的值，直接用它渲染 UI，别用客户端本地值。
6. **容错**：网络失败时暂存到本地重试队列；HTTP 4xx 提示用户检查输入；HTTP 5xx 允许重试。

---

## 审计日志

每次调用都会在 `logs/{device_id}/{YYYY-MM-DD}.jsonl` 生成事件：
- `request_in` / `response_out` —— HTTP 层
- `setting_update` —— 字段、原始输入、落库值、错误原因

同一次请求用相同 `trace_id` 串联：
```bash
grep '"trace_id":"abc123..."' logs/dev_001/$(date +%F).jsonl | jq .
```
