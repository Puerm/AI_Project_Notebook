# Workflow Rules

可执行的工作流规则。每条规则定义了特定场景下必须执行的操作。

## 任务启动

1. 每次开始新任务前必须阅读 `harness/project-map/overview.md` 了解项目当前状态
2. 评估任务影响范围，列出可能被修改的文件清单后再动手
3. 如果任务涉及多文件修改，先在 `harness/project-map/change-map.md` 记录变更意图
4. **如果是在工作流中被唤醒**（被轻量编排器通过 Agent 工具 spawn），任务和输入输出路径已由编排器在 prompt 中指定。按自己 agent 定义的流程执行即可，不需要阅读 workflow 编排文件

## 任务执行

4. 修改文件前先读文件，确认当前内容与预期一致
5. 一次只改一个关注点，不要夹带无关改动
6. 修改完成后立即更新相关的 `harness/project-map/` 文档

## 验证

7. 代码修改后运行 `python harness/scripts/check_structure.py`
8. 如果存在测试，运行 `python -m pytest tests/ -v`
9. 检查 `harness/rules/` 下是否有规则被命中，确认没有违反

## 错误处理

10. 遇到错误时记录到 `harness/feedback/error-log.md`，格式：
    - 时间戳
    - 错误现象
    - 触发条件（做了什么导致错误）
    - 根因（如果已知）
    - 解决方案（如果已解决）

## 改进

11. 发现规则不完善或缺失时记录到 `harness/feedback/improvement-log.md`
12. 规则改进后同步更新 `harness/rules/` 下对应的文件
13. 每次改进后检查是否有相关 `project-map` 文档需要同步更新

## 任务结束

14. 更新 `harness/project-map/change-map.md`，记录本次变更摘要
15. 如果引入了新的命令或工作流，更新 `README.md` 和 `CLAUDE.md`
