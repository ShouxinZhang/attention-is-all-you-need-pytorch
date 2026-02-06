# 仓库清理与架构文档重写

**时间**: 2026-02-06 (操作完成)

## 变更内容

### 1. 删除冗余文件

| 操作 | 路径 | 大小 | 说明 |
|------|------|------|------|
| 删除 | `old_files/` | 49MB | 旧版脚本及旧数据集（已备份至 `/tmp/old_files_backup_20260206.tar.gz`） |
| 删除 | `__pycache__/`（根目录） | 28K | 旧脚本（apply_bpe、learn_bpe）搬走后遗留的 pyc 缓存 |

### 2. 重写 `docs/architecture/repository-structure.md`

**改进点**:
- 新增项目概述（说明项目是什么、做什么）
- 分 3 层组织：核心代码 → 配置/元数据 → 本地生成产物
- 补全缺失项：`.gitignore`、`.vscode/`、`docs/ref/`、`output/`
- 移除已删除的 `old_files/` 条目
- 新增模块依赖关系图
- transformer/ 模块每个文件增加业务语义说明

## 修改文件清单

| 文件 | 操作 |
|------|------|
| `docs/architecture/repository-structure.md` | 全文重写 |
| `old_files/` | 整个目录删除（备份在 `/tmp/old_files_backup_20260206.tar.gz`） |
| `__pycache__/`（根目录） | 删除 |
