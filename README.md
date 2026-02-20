# DS-Oracle 命令行版

基于 [DeepSeek-Oracle 玄学核心功能说明](../DS-Oracle/docs/ORACLE-CORE-FEATURES.md) 实现的命令行可运行程序，智能体部分使用 **Kimi (Moonshot)** API。

## 功能

1. **紫微排盘**：阳历生日 + 时辰，输出排盘文本与本地 PNG 图  
2. **梅花易数起卦**：占题 + 时间，输出卦象（本卦/互卦/变卦/体用）  
3. **紫微长线解读**：排盘 + 问题，调用 Kimi 生成解读，输出 MD  
4. **梅花易数解读**：起卦 + 调用 Kimi 解读，输出 MD  
5. **姻缘分析**：排盘 + 三类分析（婚姻道路、困难挑战、伴侣性格），Kimi 解读，输出 MD  
6. **智能体多轮咨询**：多轮对话，可选填出生信息，Kimi 保持上下文连续回答，每轮追加保存 MD；输入 `/menu` 或 `0` 或 `exit` 返回。  

**默认启动**：运行程序后直接按回车即进入「智能体多轮咨询」；输入 `m` 进入主菜单。  

所有文本结果会保存到 `output/` 目录（Markdown），并在终端回显；排盘图保存为 PNG。

## 环境

- Python 3.10+
- 依赖：`py-iztro`、`openai`、`Pillow`（见 `requirements.txt`）

## 配置（.env）

所有模型 API 均在项目根目录的 **`.env`** 中配置，启动时通过 `python-dotenv` 自动加载。

- 首次使用：复制 `.env.example` 为 `.env`，按需填入各厂商的 API Key 和模型名。
- **当前 CLI 使用的 LLM**：由 `LLM_PROVIDER` 决定（默认 `kimi`）；目前仅实现了 Kimi 调用。
- **Kimi**：在 `.env` 中设置 `KIMI_API_KEY`（或 `MOONSHOT_API_KEY`），可选 `KIMI_BASE_URL`、`KIMI_MODEL`、`KIMI_VISION_MODEL`。
- 其他厂商（OpenAI、Grok、Perplexity、Claude、Gemini）的变量已在 `config.py` 中预留，便于后续扩展。

## 安装与运行

```bash
cd D:\BaiduSyncdisk\aicoding\ds-oracle-cli
cp .env.example .env
# 编辑 .env，填入 KIMI_API_KEY 等
pip install -r requirements.txt
python cli.py
```

（Windows 下可复制 `.env.example` 为 `.env` 再编辑。）

若终端中文乱码，可在运行前执行：`chcp 65001`（PowerShell 下设为 UTF-8）。

## 项目结构

```
ds-oracle-cli/
├── cli.py          # 主入口与菜单
├── config.py       # 输出目录、Kimi 配置
├── ziwei.py        # 紫微排盘（py-iztro）+ 文本 + 排盘图
├── meihua.py       # 梅花易数起卦
├── kimi_client.py  # Kimi API 客户端
├── prompts.py      # 提示词模板
├── requirements.txt
├── output/         # 运行后生成的 MD 与 PNG
└── README.md
```

## 说明

- 排盘图使用 Pillow 绘制 12 宫格，若系统无中文字体可能乱码，可安装微软雅黑或黑体。  
- 未设置 API Key 时，仅排盘与起卦可用，解读与咨询会提示配置 Key。
