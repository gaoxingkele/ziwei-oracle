# DS-Oracle CLI 功能扩展路线图

> 最后更新：2026-03-31

## 一、现有功能总览

| 系统 | 模块 | 依赖 | 能力 |
|------|------|------|------|
| 紫微斗数 | `ziwei.py` | py-iztro (pip) | 排盘（py-iztro）、十二宫解析、PNG 宫格图、MD 文本 |
| 梅花易数 | `meihua.py` | 无 | 时间起卦、互卦/变卦、体用关系、五行生克 |
| 六爻占卜 | `liuyao.py` | `app/najia` (本地) | najia 编译卦象、世应/六神/六亲/日干支提取 |
| 西洋占星 | `astrology.py` | kerykeion (pip) | Kerykeion 本命盘、八大行星宫位、SVG 星盘图 |
| 八字命理 | `bazi.py` | `app/lunar` (本地) | 四柱、十神、纳音、藏干、地势、命宫/身宫、胎元/胎息、旬空、大运 |
| 黄历择日 | `almanac.py` | `app/lunar` (本地) | 宜忌、吉凶神煞、天神值日、星宿、九星、方位、时辰宜忌 |
| AI 解读 | `kimi_client.py` | — | Kimi 多轮对话、多系统联合解读、姻缘分析 |
| 多 LLM | `config.py` | — | 预留 Kimi/OpenAI/Grok/Perplexity/Claude/Gemini |

### 本地化包

| 包 | 来源 | 体量 | 替代的外部依赖 |
|----|------|------|----------------|
| `app/lunar/` | 6tail/lunar-python (MIT) | 28 文件 / 6,287 行 | `lunar_python` |
| `app/najia/` | bopo/najia (MIT) | 4 文件 / 675 行 | `najia` + `arrow` + `jinja2` |

---

## 二、功能缺口与开源库匹配

### Phase 1：核心命理（已完成 ✅）

#### 1.1 八字独立排盘 ✅

- **已完成**：四柱排盘、十神、纳音、五行、藏干、长生十二宫、命宫/身宫、胎元/胎息、旬空、大运流年
- **实现方式**：本地化 `app/lunar` 包，无需 china-testing/bazi

#### 1.2 黄历择日 ✅

- **已完成**：宜忌、吉凶神煞、天神值日（黄道/黑道）、星宿、九星、建除十二值星、方位、物候、六曜、月相、日禄、时辰宜忌
- **实现方式**：本地化 `app/lunar` 包 + `@register("almanac")` 注册到 engine registry

---

### Phase 1.5：紫微斗数本地化（进行中 🔄）

#### 1.5.1 PureZiwei 纯 Python 紫微引擎

- **缺口**：py-iztro 依赖 pythonmonkey（SpiderMonkey JS 引擎），冷启动 1.2s、内存 +51MB
- **方案**：独立项目 `pureziwei/`，纯 Python 重写 iztro 排盘算法
- **状态**：开发计划已完成（`D:/BaiduSyncdisk/aicoding/pureziwei/PLAN.md`），10 步渐进实现
- **完成后**：集成到 `app/pureziwei/`，替代 `py_iztro` + `pythonmonkey`
- **预期效果**：冷启动 <50ms、内存 <3MB、调用 <5ms

---

### Phase 2：卜筮三式

#### 2.1 奇门遁甲

- **缺口**：时空决策术，适合择时择方、商业决策
- **推荐库**：[kentang2017/kinqimen](https://github.com/kentang2017/kinqimen)
  - Stars：46 | `pip install kinqimen` | 依赖 `sxtwl`
  - 能力：日家/时家/刻家三种排法，天干地支、八门九星八神、宫位，输出 dict/JSON
  - Streamlit Demo：kinqimen.streamlitapp.com
- **集成方案**：
  - 新建 `qimen.py`，封装排盘 + 文本描述生成
  - `prompts.py` 新增 `SYSTEM_QIMEN` + `PROMPT_QIMEN_READING`
  - `cli.py` 新增菜单项 + `/mode` 支持 `qimen`

#### 2.2 大六壬

- **缺口**：人事推断
- **推荐库**：[kentang2017/kinliuren](https://github.com/kentang2017/kinliuren)
  - Stars：79 | `pip install kinliuren` | MIT
  - 能力：四课三传、格局分类、神煞
  - Streamlit Demo：kinliuren.streamlit.app
- **集成方案**：
  - 新建 `liuren.py`
  - 集成模式与奇门类似

#### 2.3 周易原文检索

- **缺口**：64 卦 384 爻辞原文查询与释义
- **推荐库**：[kentang2017/ichingshifa](https://github.com/kentang2017/ichingshifa)
  - Stars：153 | PyPI 可安装
  - 能力：六十四卦、爻辞、京房易、大衍之数
- **备选库**：[JinyangWang27/ichingpy](https://github.com/JinyangWang27/ichingpy)（现代 OOP，`pip install ichingpy`）
- **集成方案**：
  - 新建 `iching.py`，支持按卦名/卦象查询原文
  - 作为六爻、梅花解读的经典依据补充

---

### Phase 3：签卜与解梦

#### 3.1 庙宇抽签 / 灵签

- **缺口**：庙宇常见的抽签解签系统
- **方法论**：随机抽签号 → 查表返回签文/解释，核心是数据不是算法
- **数据源**：

| 签种 | 签数 | 推荐数据源 | Stars | 数据格式 |
|------|-----:|-----------|------:|----------|
| 观音灵签 | 100 | [steventango/guan-yin-ling-qian](https://github.com/steventango/guan-yin-ling-qian) | — | JSON（含12类分类解读：事业/婚姻/财运/求子/官司/出行等） |
| 黄大仙灵签 | 100 | [dickwin2003/sign](https://github.com/dickwin2003/sign) | 2 | JSON：签号+签题+吉凶+签诗+解签+仙机+典故（含日文/繁体版） |
| 诸葛神算 | 384 | [sealdice/draw](https://github.com/sealdice/draw) | 47 | JSON：签号+吉凶+卦宫+签诗+解签 |
| 六十四卦卦辞 | 64 | [sealdice/draw](https://github.com/sealdice/draw) | 47 | JSON：卦名+卦辞+吉凶+象曰+事业/经商/婚恋/决策 |
| 关帝/妈祖/月老/车公/吕祖 | 各60-101 | [HajimeAIPlatform/HajimeAIWorkSpace](https://github.com/HajimeAIPlatform/HajimeAIWorkSpace) | — | JSON 5.3MB 全家桶（需清洗） |

- **每签数据结构**：
  ```
  签号 / 吉凶等级(上上/上/中/下/下下) / 签诗 / 解曰 / 圣意(仙机) / 典故 / 分类解读
  ```
- **集成方案**：
  ```
  app/engine/qianwen.py        # 抽签引擎（通用，@register("qianwen")）
  app/data/qianwen/            # 签文数据
  ├── guanyin.json              # 观音灵签 100 签
  ├── guandi.json               # 关帝灵签 100 签
  ├── huangdaxian.json          # 黄大仙灵签 100 签
  ├── mazu.json                 # 妈祖灵签 60 签
  ├── yuelao.json               # 月老灵签 101 签
  ├── chegong.json              # 车公灵签 96 签
  ├── lvzu.json                 # 吕祖灵签 100 签
  └── zhuge.json                # 诸葛神算 384 签
  ```
  - 输入：`ChartRequest.extra["qianwen_type"]` 指定签种
  - 输出：随机签号 + 完整签文数据 + 文本摘要
  - 与 LLM 联动：签诗 + 用户问题 → AI 个性化解读

#### 3.2 周公解梦

- **缺口**：梦境关键词查询 → 返回解梦释义
- **数据源**：

| 数据源 | 条目数 | 格式 | 特点 |
|--------|-------:|------|------|
| [saiwaiyanyu/tensorflow-bert-seq2seq-dream-decoder](https://github.com/saiwaiyanyu/tensorflow-bert-seq2seq-dream-decoder) (127⭐) | 33,000+ | JSON | 最大开源数据集，dream-decode 键值对 |
| CSDN SQL dump (百度网盘) | ~9,000 | MySQL SQL | 10 个分类（动物/植物/人物/自然/生活/鬼神/建筑/物品/情爱/身体） |
| [leochan2017/zgjm](https://github.com/leochan2017/zgjm) (216⭐) | — | JS (微信小程序) | 星数最高的周公解梦项目 |

- **每条数据结构**：
  ```
  分类(动物/植物/...) / 关键词(梦见蛇/梦见水/...) / 解梦内容 / 吉凶(从文本解析)
  ```
- **集成方案**：
  ```
  app/engine/jiemeng.py         # 解梦引擎（@register("jiemeng")）
  app/data/jiemeng/
  └── dreams.json               # 解梦数据库（合并多源去重后）
  ```
  - 输入：`ChartRequest.question` 为梦境描述
  - 逻辑：关键词匹配 → 返回相关解释列表
  - 与 LLM 联动：匹配结果 + 用户梦境描述 → AI 综合解读
  - 备选增强：用 bert-seq2seq 数据训练语义匹配（远期）

---

### Phase 4：相术

#### 4.1 姓名学（五格剖象）

- **缺口**：天格/地格/人格/外格/总格 + 三才配置
- **推荐库（取名）**：[JakLiao/GoodGoodName](https://github.com/JakLiao/GoodGoodName)
  - Stars：411 | 三才五格 + 喜用神起名
- **推荐库（测名）**：[peiss/chinese-name-score](https://github.com/peiss/chinese-name-score)
  - Stars：310 | 五格数理打分
- **集成方案**：
  - 新建 `name_analysis.py`，提取两个项目的五格计算核心
  - 功能 1：输入姓名 → 五格评分 + 三才配置 + 吉凶判断
  - 功能 2：输入姓氏 + 八字喜用神 → 推荐名字列表
  - 与八字模块联动（喜用神 → 起名用字）

#### 4.2 面相 AI

- **缺口**：五官分析、面相解读
- **推荐库（基座）**：[serengil/deepface](https://github.com/serengil/deepface)
  - Stars：22,200 | `pip install deepface`
  - 能力：年龄/性别/情绪/人种/面部特征提取
- **参考库**：[lincerely/Face-Reading](https://github.com/lincerely/Face-Reading)（唯一面相 CV 项目）
- **集成方案**：
  - 新建 `face_reading.py`
  - 用 deepface 提取面部特征（五官比例、脸型、额头、下巴等）
  - 将特征描述传给 LLM Vision（`KIMI_VISION_MODEL` 已预留）做面相解读
  - 支持拍照/上传照片输入

---

### Phase 5：进阶扩展

#### 5.1 太乙神数

- **推荐库**：[kentang2017/kintaiyi](https://github.com/kentang2017/kintaiyi)
  - Stars：28 | `pip install kintaiyi`
  - 能力：年/月/日/时/分五种计法，命法，四种经典公式
- **说明**：偏国运/大势预测，用户需求较小，优先级低

#### 5.2 风水/玄空飞星

- **现状**：**生态空白**，无专门 Python 库
- **参考**：china-testing/bazi 附带基础风水模块
- **集成方案**：
  - 新建 `fengshui.py`，自研玄空飞星排盘
  - 核心算法：九宫飞星（运星 + 山星 + 向星）、三元九运、坐向判断
  - 输入：经纬度（复用 `config.py` 的 `ASTRO_LNG/LAT`）+ 建造年份
  - 输出：九宫飞星盘 + 各宫吉凶 + 流年飞星叠加

#### 5.3 八字合婚

- **依赖**：Phase 1 的八字模块完成后（✅ 已就绪）
- **集成方案**：
  - 双人八字对比：日柱天合地合、五行互补、十神配对
  - 替代/增强现有的姻缘分析功能（目前仅靠 LLM 推断）

---

## 三、依赖汇总

```txt
# 已本地化（零外部依赖）
app/lunar/             # 原 lunar_python — 八字、黄历
app/najia/             # 原 najia — 六爻

# 待本地化
pureziwei/             # 替代 py-iztro — 紫微斗数（进行中）

# 保持 pip 依赖
kerykeion>=5.7.0       # 西洋占星（swisseph C 扩展，无法纯 Python 替代）
pydantic               # 数据模型

# Phase 2
kinqimen               # 奇门遁甲
kinliuren              # 大六壬
ichingshifa            # 周易原文
sxtwl                  # kin- 系列共同依赖

# Phase 3 — 签卜/解梦：纯数据，无外部依赖

# Phase 4
deepface               # 面相 AI 基座

# Phase 5
kintaiyi               # 太乙神数
```

---

## 四、文件结构规划

```
ds-oracle-cli/
├── cli.py                # 主入口（扩展菜单项 + /mode 命令）
├── config.py             # 配置（新增相关环境变量）
├── prompts.py            # 提示词（新增各系统 SYSTEM/PROMPT 模板）
├── kimi_client.py        # LLM 客户端
│
├── app/
│   ├── lunar/            # ✅ 本地化农历/八字/黄历计算库
│   ├── najia/            # ✅ 本地化六爻排盘库
│   ├── pureziwei/        # 🔄 本地化紫微排盘库（待完成）
│   │
│   ├── engine/
│   │   ├── ziwei.py      # ✅ 紫微斗数
│   │   ├── meihua.py     # ✅ 梅花易数
│   │   ├── liuyao.py     # ✅ 六爻占卜
│   │   ├── astrology.py  # ✅ 西洋占星
│   │   ├── bazi.py       # ✅ 八字命理
│   │   ├── almanac.py    # ✅ 黄历择日
│   │   ├── qianwen.py    # Phase 3 新增：抽签
│   │   ├── jiemeng.py    # Phase 3 新增：解梦
│   │   ├── qimen.py      # Phase 2 新增：奇门遁甲
│   │   ├── liuren.py     # Phase 2 新增：大六壬
│   │   ├── iching.py     # Phase 2 新增：周易原文
│   │   ├── name_analysis.py # Phase 4 新增：姓名学
│   │   ├── face_reading.py  # Phase 4 新增：面相 AI
│   │   ├── fengshui.py   # Phase 5 新增：风水
│   │   └── taiyi.py      # Phase 5 新增：太乙神数
│   │
│   └── data/
│       ├── qianwen/      # Phase 3：签文数据
│       │   ├── guanyin.json
│       │   ├── guandi.json
│       │   ├── huangdaxian.json
│       │   ├── mazu.json
│       │   ├── yuelao.json
│       │   ├── chegong.json
│       │   ├── lvzu.json
│       │   └── zhuge.json
│       └── jiemeng/      # Phase 3：解梦数据
│           └── dreams.json
│
├── output/               # 输出目录
├── requirements.txt      # 依赖清单（分阶段更新）
├── ROADMAP.md            # 本文件
└── README.md             # 用户文档
```

---

## 五、实施优先级与里程碑

| 阶段 | 模块 | 核心库/数据源 | 预期产出 | 状态 |
|------|------|--------------|----------|:----:|
| **Phase 1** | 八字 + 黄历 | app/lunar (本地) | 完整八字排盘 + 全量黄历查询 | ✅ |
| **Phase 1.5** | 紫微斗数本地化 | pureziwei (本地) | 纯 Python 紫微引擎，内存降 50 倍 | 🔄 |
| **Phase 2** | 奇门 + 六壬 + 周易 | kin- 系列, ichingshifa | 三式排盘解读 + 卦辞原文检索 | |
| **Phase 3** | 抽签 + 解梦 | GitHub JSON 数据 | 8 种灵签 + 33000+ 解梦条目 | |
| **Phase 4** | 姓名学 + 面相 AI | GoodGoodName, deepface | 五格测名/起名 + 面相解读 | |
| **Phase 5** | 太乙 + 风水 + 合婚 | kintaiyi, 自研 | 完整五术体系 | |

每个 Phase 完成后：
1. 更新 `requirements.txt`
2. 更新 `cli.py` 菜单 + `/mode` 命令
3. 更新 `prompts.py` 增加对应系统提示词
4. 更新 `README.md` 使用文档
