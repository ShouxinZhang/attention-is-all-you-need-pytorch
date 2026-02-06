# Repository Structure

> **Attention Is All You Need** — PyTorch 实现  
> 基于论文 *Vaswani et al., NIPS 2017* 的 Transformer 模型，用于序列到序列的机器翻译任务（德语 → 英语）。  
> 当前版本已针对 2026 年现代硬件（RTX 5090 / sm_120）和工具链（PyTorch 2.10+、Spacy pipeline）进行全面优化。

---

## 1. 核心代码（Git 跟踪）

### 1.1 入口脚本（根目录）

| 文件 | 说明 |
|------|------|
| `preprocess_modern.py` | 数据预处理：下载 Multi30k 数据集，使用 Spacy tokenizer 构建词表并序列化为 pkl |
| `train_modern.py` | 模型训练：支持 RTX 5090/sm_120 优化、TensorBoard 日志、断点续训 |
| `check_errors.sh` | 自动化质量门禁：模式匹配检查（类型、未绑定变量、未使用导入、无效 __all__）+ 全仓库静态类型检查 |

### 1.2 `transformer/` — Transformer 模型核心模块

| 文件 | 说明 |
|------|------|
| `__init__.py` | 包初始化，对外暴露公共接口 |
| `Constants.py` | 全局常量定义（PAD token 等） |
| `Modules.py` | 基础构建块：缩放点积注意力（Scaled Dot-Product Attention） |
| `SubLayers.py` | 子层实现：多头注意力（Multi-Head Attention）、前馈网络（Position-wise FFN） |
| `Layers.py` | Transformer 层：编码器层 / 解码器层，组合子层 + 残差连接 |
| `Models.py` | 完整模型定义：Encoder、Decoder、Transformer、位置编码（Positional Encoding） |
| `Optim.py` | 优化器包装器：实现论文中的学习率预热调度（Warmup Scheduler） |
| `Translator.py` | 推理模块：Beam Search 翻译逻辑，使用注册张量缓冲区 |
| `modern_data.py` | 现代数据管道：Dataset 和 Vocabulary 叶子模块，配合 Spacy tokenizer |

### 1.3 `docs/` — 项目文档

| 路径 | 说明 |
|------|------|
| `docs/architecture/repository-structure.md` | 本文件 — 仓库架构与模块结构定义 |
| `docs/dev_logs/` | 开发周期日志，按日期分文件夹，用于变更追溯和回滚参考 |
| `docs/ref/` | 参考资料（含原论文 PDF） |

### 1.4 `tools/` — 工程工具模块

| 路径 | 说明 |
|------|------|
| `tools/check_errors/` | `check_errors.sh` 的实现模块：通用未使用导入 AST 扫描 + `__all__` 运行时校验 |

### 1.5 配置与元数据（Git 跟踪）

| 文件 | 说明 |
|------|------|
| `.gitignore` | Git 忽略规则 |
| `.vscode/settings.json` | VS Code 工作区设置 |
| `requirements.txt` | Python 依赖清单 |
| `AGENTS.md` | AI Agent 工作指令（英文） |
| `AGENTS_zh-cn.md` | AI Agent 工作指令（中文） |
| `README.md` | 项目概览与使用说明 |
| `LICENSE` | 项目许可证 |

---

## 2. 本地生成产物（Git 忽略，不入库）

以下目录/文件由 `.gitignore` 排除，仅存在于本地开发环境中。

| 路径 | 说明 |
|------|------|
| `venv/` | Python 虚拟环境（PyTorch 2.10.0+cu130） |
| `.data/multi30k/` | 原始 Multi30k 数据集（由 `preprocess_modern.py` 自动下载） |
| `multi30k_de_en_modern.pkl` | 预处理后的序列化数据集 |
| `output/` | 训练产物，每次训练一个子目录，包含模型检查点（`.chkpt`）和 TensorBoard 日志 |

---

## 3. 模块依赖关系

```
preprocess_modern.py ──→ transformer/modern_data.py ──→ transformer/Constants.py
                                                    
train_modern.py ──→ transformer/Models.py ──→ transformer/Layers.py ──→ transformer/SubLayers.py ──→ transformer/Modules.py
                 ──→ transformer/Optim.py
                 ──→ transformer/Translator.py ──→ transformer/Models.py
                 ──→ transformer/modern_data.py
```
