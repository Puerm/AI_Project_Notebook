# Change Summary: fix-harness-feedback-loop

## 修复内容

### 阻塞 bug: save_signals() 空操作

- **文件**: `harness/state/feedback_engine.py`
- **改动**: `__init__` 新增 `self._signals` 内存缓存；`add_signal()` 同步更新缓存；`save_signals()` 从 `pass` 替换为实际原子写入（加载缓存后调用 `_write_signals()` .tmp + os.replace）
- **问题**: `save_signals()` 方法体为 `pass`，删除 JSON 文件后调用无法重新持久化数据
- **验证**: `test_save_signals_actually_persists_data` 通过（20/20 test_feedback_engine 全绿，254/254 全量测试无回归）

### 第二类问题: 规则演化建议生成缺少原子写入

- **文件**: `harness/scripts/generate_rule_evolution.py`
- **改动**: 追加模式从直接 `open("a")` append 改为先读已有内容再整体原子写入（.tmp + os.replace）
- **验证**: test_generate_rule_evolution 10/10 全绿
