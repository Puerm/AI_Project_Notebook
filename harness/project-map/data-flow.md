# Data Flow

项目中数据的产生、存储、流转路径。

## v0.1 数据流

```
用户输入（命令行参数/文件路径）
         │
         ▼
  ┌──────────────┐
  │  CLI 脚本     │  ← 读取 harness/rules/ 中的规则约束
  │  (scripts/)  │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  文件系统     │
  │              │
  │  • project-map/ → 读取/更新项目知识
  │  • feedback/    → 追加错误和改进记录
  │  • data/        → 用户数据（只读，保护）
  │  • app/         → 应用代码（可读写）
  └──────────────┘
```

## 数据文件格式

| 目录 | 文件格式 | 编码 |
| ---- | ---- | ---- |
| `harness/project-map/` | Markdown | UTF-8 |
| `harness/feedback/` | Markdown | UTF-8 |
| `harness/rules/` | Markdown | UTF-8 |
| `data/` | 任意（用户定义） | UTF-8 |
| `app/` | Python / Markdown | UTF-8 |

## 数据保护

- `data/` 目录不可被任何脚本自动删除
- `harness/feedback/` 只能追加，不能覆盖
- `harness/project-map/` 修改后必须通过 `check_structure.py` 验证

## 变更规则

- 增加新的数据文件格式后必须更新本文档
- 增加新的数据流路径后必须更新上图
- 修改数据结构（字段/格式）后必须更新本文档和相关模块
