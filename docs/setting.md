# MazuKit 客户端 Setting API 调用清单

> 客户端（MazuKit / v1.44）实际向服务器发起的 Setting API 请求与预期响应对应关系。设备端开发和服务端联调参考。

## 通用配置

- **Base URL**：`http://117.50.48.22:8000/api/v1/setting`
- **device_id 生成规则**：`dev_` + MAC 地址去除冒号后前 12 字符
  - 示例：MAC `39:eb:47:21:84:c4` → `dev_39eb472184c4`
  - 同一设备（浏览器）跨会话保持不变（存 localStorage）
- **Headers**：
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`（如 `App.settings.authToken` 已配置）
- **CORS 绕过**：客户端运行在 `localhost` 时，所有请求走 `POST/GET /api/proxy?url=<encoded>` 由 `server.py` 转发

---

## 1. 姓名 · `POST /api/v1/setting/name`

### 请求

```http
POST /api/v1/setting/name HTTP/1.1
Content-Type: application/json
Authorization: Bearer a4hPBy2NCum1qiWp...
```

```json
{
  "device_id": "dev_39eb472184c4",
  "text": "姓双木林、名字叫平凡的凡",
  "lang": "zh"
}
```

**字段说明**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `device_id` | string | 设备唯一标识 |
| `text` | string | 语音识别原话，支持拆字（`双木林` / `耳东陈` / `弓长张`）、直接报名（`张三`）、英文名（`John Smith`） |
| `lang` | string | 客户端固定传 `"zh"`；可选 `"en"` |

### 预期响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "device_id": "dev_39eb472184c4",
    "field": "name",
    "value": "林凡",
    "raw": "姓双木林、名字叫平凡的凡",
    "lang": "zh",
    "updated_at": "2026-04-15T22:37:59.807"
  },
  "timestamp": 1713189479
}
```

**客户端处理**：写入 `App.settings.profile.name = data.value`

---

## 2. 生日 · `POST /api/v1/setting/birthday`

### 请求

```json
{
  "device_id": "dev_39eb472184c4",
  "text": "1995-03-03"
}
```

**字段说明**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | v1.42 起客户端使用滚轮选择，已规范化为 `YYYY-MM-DD` 字符串；服务端 fast-path 命中正则直接返回（无需调 LLM） |

> 注：如服务端想支持语音输入路径，`text` 也可能是 `"一九七零年四月十号"` 等非规范文本，服务端走 LLM 解析。

### 预期响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "device_id": "dev_39eb472184c4",
    "field": "birthday",
    "value": "1995-03-03",
    "raw": "1995-03-03",
    "updated_at": "2026-04-15T22:37:59.807"
  },
  "timestamp": 1713189479
}
```

**客户端处理**：写入 `App.settings.profile.birthday = data.value`；验证格式 `/^\d{4}-\d{2}-\d{2}$/`

---

## 3. 出生时间 · `POST /api/v1/setting/birthtime`

### 请求

```json
{
  "device_id": "dev_39eb472184c4",
  "text": "07:40"
}
```

**字段说明**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | v1.42 起客户端使用滚轮选择，已规范化为 `HH:MM` 24 小时制 |

### 预期响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "device_id": "dev_39eb472184c4",
    "field": "birthtime",
    "value": "07:40",
    "raw": "07:40",
    "updated_at": "2026-04-15T22:37:59.807"
  },
  "timestamp": 1713189479
}
```

**客户端处理**：写入 `App.settings.profile.birthtime = data.value`；验证格式 `/^\d{2}:\d{2}$/`

---

## 4. 出生地点 · `POST /api/v1/setting/city`

### 请求

```json
{
  "device_id": "dev_39eb472184c4",
  "text": "福建永安"
}
```

**字段说明**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 语音识别原话，服务端规范化为「省份+市」或「国家+城市」 |

### 预期响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "device_id": "dev_39eb472184c4",
    "field": "city",
    "value": "福建省永安市",
    "raw": "福建永安",
    "updated_at": "2026-04-15T22:37:59.807"
  },
  "timestamp": 1713189479
}
```

**客户端处理**：写入 `App.settings.profile.city = data.value`

---

## 5. 性别 · `POST /api/v1/setting/sex`

### 请求

```json
{
  "device_id": "dev_39eb472184c4",
  "text": "男"
}
```

**字段说明**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 语音识别原话，支持 `男` / `男生` / `male` / `1` 等 |

### 预期响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "device_id": "dev_39eb472184c4",
    "field": "sex",
    "value": 1,
    "raw": "男",
    "updated_at": "2026-04-15T22:37:59.807"
  },
  "timestamp": 1713189479
}
```

**字段值**：`value` 是**整数** `1`（男）或 `0`（女），不是字符串。

**客户端处理**：写入 `App.settings.profile.sex = data.value`

---

## 6. 读取全部设置 · `GET /api/v1/setting`

### 请求

```http
GET /api/v1/setting?device_id=dev_39eb472184c4 HTTP/1.1
Authorization: Bearer a4hPBy2NCum1qiWp...
```

### 预期响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "device_id": "dev_39eb472184c4",
    "name": "林凡",
    "sex": 1,
    "birthday": "1995-03-03",
    "birthtime": "07:40",
    "city": "福建省永安市",
    "updated_at": "2026-04-15T22:37:59.807"
  },
  "timestamp": 1713189479
}
```

**字段说明**：
- 若某字段未设置，服务端应返回 `null`（不是报错）
- `sex` 是数字 `1`/`0`/`null`，不是字符串

**客户端调用时机**：
1. 页面启动后 2 秒（startup 同步）
2. 每次进入「设置」屏时（后台刷新，若有变化则 re-render）

**客户端处理**：
```js
// 合并非 null 字段到本地 profile
if(d.name!=null)   profile.name      = d.name;
if(d.sex!=null)    profile.sex       = d.sex;
if(d.birthday!=null) profile.birthday = d.birthday;
if(d.birthtime!=null) profile.birthtime = d.birthtime;
if(d.city!=null)   profile.city      = d.city;
saveSettings();
```

---

## 错误响应

所有端点统一错误结构：

```json
{
  "code": 40001,
  "message": "解析失败: 无法解析生日: ...",
  "data": null,
  "timestamp": 1713189479
}
```

| code | 含义 | 客户端表现 |
|------|------|----------|
| `0` | 成功 | 保存 `data.value` 到 localStorage |
| `40001` | LLM 解析失败 | 显示"规范化失败 · 重录"，不写本地 |
| `41002` | Token 无效 | 显示 HTTP 401 或后端错误消息 |
| `41003` | 缺少 Token | 同上 |
| `50001` | LLM 服务异常 | 显示错误并允许重试 |

---

## 已知服务端未就绪的错误（实测）

截至 2026-04-15 22:37，服务端实际表现：

| 路径 | 实际响应 |
|------|----------|
| `GET /api/v1/setting?device_id=xxx` | `HTTP 200` body: `Server is running`（**非 JSON**） |
| `POST /api/v1/setting/birthday` | `HTTP 502` body: 空 |
| `POST /api/v1/setting/name` | `HTTP 502` body: 空 |

说明后端 setting 微服务尚未部署，nginx/网关路由未生效。客户端检测到 502/非 JSON 响应时：
- **本地暂存**规范化值到 localStorage（避免用户重录）
- 显示详细错误信息（含 HTTP 状态码和响应体预览）

---

## 客户端调用代码参考

```js
// helpers
function _settingDeviceId(){
  return 'dev_' + (App.settings.macAddress||'').replace(/[^a-zA-Z0-9]/g,'').slice(0,12);
}
function _settingHeaders(){
  const h={'Content-Type':'application/json'};
  if(App.settings.authToken) h['Authorization']='Bearer '+App.settings.authToken;
  return h;
}

// POST {field}
async function _callSettingAPI(field, text){
  const base = App.settings.settingApiBase; // http://117.50.48.22:8000/api/v1/setting
  const url  = base + '/' + field;
  const body = { device_id: _settingDeviceId(), text };
  if (field === 'name') body.lang = 'zh';

  const resp = await fetch(url, {
    method: 'POST',
    headers: _settingHeaders(),
    body: JSON.stringify(body),
  });
  const raw = await resp.text();
  if (!resp.ok) throw new Error('HTTP ' + resp.status);
  const json = JSON.parse(raw);
  if (json.code !== 0) throw new Error(json.message);
  return json.data; // { device_id, field, value, raw, updated_at }
}

// GET all
async function _fetchAllSettings(){
  const url = base + '?device_id=' + encodeURIComponent(_settingDeviceId());
  const resp = await fetch(url, { headers: _settingHeaders() });
  const json = await resp.json();
  if (json.code !== 0) return null;
  return json.data; // { device_id, name, sex, birthday, birthtime, city, updated_at }
}
```

---

## 设备端缓存策略

1. **写成功**：`value` 覆盖本地，同时保留服务器的 `updated_at`
2. **写失败（网络/502/LLM异常）**：规范化文本暂存本地 profile，不覆盖 `updated_at`，下次进入设置屏或启动时通过 GET 拉取远端真实值
3. **启动同步**：GET 返回的字段**非 null 才覆盖本地**，避免跨设备间单向同步导致数据覆盖
