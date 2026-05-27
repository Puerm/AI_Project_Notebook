# Spec: 修复 LLM 检测成功判断逻辑

## 1. 要解决什么问题

`harness_deploy.py` 个性化部署时，LLM 检测即使调用成功也会显示"LLM 检测失败，降级为静态检测"。根因是成功判断条件 `"languages" in llm_result` 与 focus_fields 模式的返回字段不匹配。

## 2. 版本目标

修复判断逻辑，使 LLM 检测成功/失败的状态正确反映实际情况。

## 3. 功能清单

### 本版本实现

| 功能 | MVP 描述 | 验收标准 |
| ---- | -------- | -------- |
| 修复成功判断条件 | `detect_project()` 中根据是否使用 focus_fields 调整成功判断：focus_fields 模式检查返回的字段是否包含请求的字段；完整模式保持检查 `languages` | 1) baseline + focus_fields 时 LLM 成功返回 → 显示"LLM 检测成功"；2) 完整模式行为不变 |
| 增强错误输出 | `_llm_detect_project` 失败时打印具体原因（API 错误码、JSON 解析失败等），方便排查 | stderr 包含失败原因 |

### 暂不实现

- 不修改 `_load_dotenv` 的路径逻辑（那是独立的健壮性问题）
- 不修改 LLM API 调用本身

## 4. 风险与未决问题

- `_llm_detect_project` 的 except 吞掉了异常细节（line 298: `except Exception: return None`），可能隐藏了真正的 API 错误。本次修复需保留异常信息到 stderr。
