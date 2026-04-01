# Code Review: 重构签数据构建脚本 + 新增 CLI 星相/六爻模块

**分支**: `feature/unified-api-phase1`
**日期**: 2026-04-01 12:00
**改动来源**: 未提交更改（5 个文件修改/删除 + 2 个新文件）+ 已提交 11 个 commit vs master

## 关联文档

无关联设计文档

## 改动概览

### 代码文件

| 文件 | 增/删 | 改动摘要 |
|------|:---:|------|
| app/data/qianwen/build_data.py | +132/-329 | 大幅简化签数据构建脚本，提取通用工具函数，精简三个 build 函数 |
| app/data/qianwen/guanyin.json | ~1582 行变动 | 重新生成的观音灵签数据 |
| app/data/qianwen/huangdaxian.json | ~1600 行变动 | 重新生成的黄大仙灵签数据 |
| app/data/qianwen/zhuge.json | ~5376 行变动 | 重新生成的诸葛神算数据 |
| app/data/qianwen/zhuge_raw.json | -400 | 删除不再需要的中间文件 |
| astrology.py (新) | +145 | CLI 用星相排盘模块，封装 kerykeion 调用 |
| liuyao.py (新) | +111 | CLI 用六爻排盘模块，封装 najia 调用 |

## Review 结果

### 1. 业务目标
**通过** — 两部分改动目标清晰：(1) 简化签数据构建脚本并重新生成数据；(2) 为 CLI 提供星相和六爻排盘的独立模块。

### 2. 架构适配
**注意** — `astrology.py` 和 `liuyao.py` 放在项目根目录，而 `app/engine/` 下已有同名文件。根目录的版本是 CLI (`cli.py`) 专用，与 app/engine 的 API 版本平行存在。这种双轨结构可以工作，但需注意未来维护时两边逻辑是否会分化。当前 `cli.py` 已通过 `from astrology import ...` 和 `from liuyao import ...` 引用根目录版本，路径依赖成立。

### 3. Bug 检查
**注意** — 
- `liuyao.py:20` 硬编码了本地路径 `D:\BaiduSyncdisk\aicoding\najia` 作为 fallback，在其他环境会静默失败（不会报错，只是 fallback 路径不存在），可接受但不理想。
- `astrology.py` 从 `config` 导入 ASTRO_* 常量，依赖根目录的 `config.py`，与 `app/config.py` 中同名常量并行存在，无冲突但需知晓。
- `build_data.py:45` 中使用了 Unicode 转义字符串作为 dict key（`\u7c64X\u7c64` 等），实际是 JSON 源数据的中文 key，逻辑正确。

### 4. 代码清晰度
**通过** — `build_data.py` 重构后从 329 行精简到 228 行，提取了 `chinese_num_to_int`、`extract_guanyin_level`、`clean_html` 等工具函数，可读性显著提升。`astrology.py` 和 `liuyao.py` 结构清晰，函数职责明确。

### 5. KISS 原则
**通过** — 重构方向正确，删除了冗余的 `zhuge_raw.json`，简化了数据获取流程。新模块代码量适度，无过度设计。

### 6. 单一职责
**通过** — `build_data.py` 负责数据构建，`astrology.py` 负责星相排盘，`liuyao.py` 负责六爻排盘，职责划分清晰。

### 7. 配置一致性
**通过** — 配置项（ASTRO_* 常量）在 `config.py` 中定义，`astrology.py` 正确引用。无新增配置文件变动。

## 总结

改动整体质量良好，无"问题"级发现。两个"注意"项：(1) 根目录与 `app/engine/` 下存在同名模块的双轨结构，后续维护需留意；(2) `liuyao.py` 中硬编码的本地 fallback 路径仅在开发环境有效。这些均为已知的开发期权衡，不阻塞提交。
