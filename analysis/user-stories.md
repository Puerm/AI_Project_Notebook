# AI_Project_Notebook — 用户故事

好的，作为资深产品经理，我已经仔细审阅了你提供的代码库子集和架构分析。现在，我将为你呈现一份从代码中反向重建的用户故事文档。

这份文档将系统性地解析 `AI_Project_Notebook` 如何通过其 Agent 工作流和 Harness 框架，为 AI 辅助开发提供一个完整、可迭代的协作闭环。

---

# AI_Project_Notebook 用户故事文档

## 1. 核心用户故事

以下故事按照开发流程的自然顺序排列，从项目分析到最终的自我修复，构成了一个完整的 AI 开发协作闭环。

### 故事 1：作为开发者，我希望系统能自动分析并理解一个新项目的结构和业务领域，以便我无需手动浏览整个代码库就能获得一份高质量的项目概览。

*   **优先级**: P0 (最高)
*   **价值**: 这是整个工具链的起点。快速、准确地理解一个陌生项目是进行后续所有操作的基础。

*   **代码证据**:
    *   `app/analyze_project.py`: CLI 入口，通过 `--digest` 参数触发聚焦分析。
    *   `app/analyzer/digest_collector.py`: 核心分析引擎，通过 `collect_digest()` 函数收集代码摘要，并通过 `filter_for_architecture()`, `filter_for_user_stories()`, `filter_for_risk()` 等函数按维度筛选文件。
    *   `app/analyzer/dimension_analyzer.py`: 包含 `_degraded_architecture()`, `_degraded_user_stories()`, `_degraded_risk()` 等降级分析函数，确保在无 LLM 时也能生成基础报告。
    *   `app/analyzer/domain_analyzer.py`: 负责 LLM 驱动的业务板块识别，并通过 `_degraded_domain_result()` 函数实现降级回退。
    *   `tests/test_analyze_project.py`: 测试 `--digest` 模式即使 LLM 调用失败，也能生成 `project-overview.md` 文件。

    ```python
    # tests/test_analyze_project.py
    def test_digest_always_generates_project_overview(self):
        """--digest 模式下即使 cdigest 不可用，仍生成 project-overview.md"""
        # ...
        result = subprocess.run(
            [sys.executable, CLI_SCRIPT, tmp, "--digest", "--quiet"],
            capture_output=True, encoding="utf-8", env=run_env,
        )
        assert result.returncode == 0
        overview_path = os.path.join(tmp, "harness", "project-map", "project-overview.md")
        assert os.path.isfile(overview_path)
    ```

### 故事 2：作为产品经理（PM），我希望能与 AI 讨论并澄清模糊或冲突的需求，以便在开发前修正软件规格说明书（Spec），减少后期返工。

*   **优先级**: P0
*   **价值**: 这是“以终为始”的核心。在规划（Planning）之前解决定义问题，能显著提升团队效率。

*   **代码证据**:
    *   `AI_Project_Notebook\.claude\commands\workflow\review-fix.md`: 定义了 `review-fix` 工作流。
    *   该工作流的执行说明中明确提到“阶段 0a: 第三类问题 → PM（你亲自执行）”。
    *   它要求 PM 角色阅读 `.claude/agents/pm.md`，并与用户逐项讨论澄清，更新 spec。完成后“释放 pm.md”。
    ```markdown
    # File: AI_Project_Notebook\.claude\commands\workflow\review-fix.md
    ### 阶段 0a: 第三类问题 → PM（你亲自执行）
    若有第三类问题，你阅读 `.claude/agents/pm.md`，扮演 PM 与用户逐项讨论澄清，更新 spec。完成后释放 pm.md。
    ```
    *   同样，在 `AI_Project_Notebook\.agents\skills\source-command-workflow-review-fix\SKILL.md` 中也定义了完全相同的逻辑，作为可调用的技能。

### 故事 3：作为规划工程师（Planner），我希望能根据澄清后的 Spec 生成一份详细的、可执行的开发计划，以便开发工作有章可循。

*   **优先级**: P0
*   **价值**: 计划是将需求转化为具体行动的关键一步，明确了“要做什么”和“怎么做”。

*   **代码证据**:
    *   `harness\workflow\review-fix.md` 的 YAML frontmatter `stages` 列表中，`planner-fix` 阶段被第一个列出（在条件满足时）。
    *   该阶段的输入包含了 Spec (`openspec/specs/{topic}.md`) 和审查报告 (`review.md`)，输出是 `fix-plan.md`。
    ```yaml
    # File: AI_Project_Notebook\harness\workflow\review-fix.md
    stages:
      - id: planner-fix
        agent: planner
        inputs:
          - "openspec/specs/{topic}.md"
          - "openspec/changes/{topic}/review.md"
          - "openspec/changes/{topic}/plan.md"
        outputs:
          - "openspec/changes/{topic}/fix-plan.md"
        condition: has_category_2_or_3
        pause: true
    ```

### 故事 4：作为代码生成器（Generator），我希望能根据计划和规范来修改代码，以便实现特定的功能或修复特定的缺陷。

*   **优先级**: P0
*   **价值**: 这是将计划落地为代码的核心环节。无论是实现新功能还是修复问题，都依赖于这一步骤。

*   **代码证据**:
    *   在 `harness\workflow\review-fix.md` 的 stages 中，`generator-fix` 阶段被定义，其输入为 `review.md` 和 `fix-plan.md`，输出为 `change-summary.md`。这清晰地表明 Generator 的职责是基于审查和计划进行代码变更。
    ```yaml
    # File: AI_Project_Notebook\harness\workflow\review-fix.md
      - id: generator-fix
        agent: generator
        inputs:
          - "openspec/changes/{topic}/review.md"
          - "openspec/changes/{topic}/fix-plan.md"
        outputs:
          - "openspec/changes/{topic}/change-summary.md"
        condition: has_any_category
    ```

### 故事 5：作为代码审查员（Reviewer），我希望对照规范和规则来审查代码变更，并自动对发现的问题进行分类，以便快速定位问题源头并分派给正确的角色。

*   **优先级**: P0
*   **价值**: 自动化的代码审查和问题分类是工作流中保证代码质量和责任清晰的关键。

*   **代码证据**:
    *   `AI_Project_Notebook\.claude\agents\reviewer.md` 详细定义了审查员的职责和分类标准。
    *   它明确将问题分为三类：第一类（小修问题，路由给 Generator）、第二类（实现偏差，路由给 Planner）、第三类（需求/spec 问题，路由给 PM）。
    ```markdown
    # File: AI_Project_Notebook\.claude\agents\reviewer.md
    ## 问题分类

    ### 第一类：小修问题 → Generator
    特征: 修改范围 ≤ 1 个文件，不影响接口和契约。

    ### 第二类：实现偏差 → Planner
    特征: 修改范围 > 1 个文件，或涉及接口变更。

    ### 第三类：需求/spec 问题 → PM
    特征: 问题的根因不在代码层面，而在需求定义层面。
    ```

### 故事 6：作为测试员（Tester），我希望能够在代码变更后自动进行自动化测试，并将测试结果以报告形式反馈，以便验证代码功能的正确性。

*   **优先级**: P0
*   **价值**: 自动化测试是保障代码质量的最后一道防线，确保新的改动不会引入回归性问题。

*   **代码证据**:
    *   在 `AI_Project_Notebook\.agents\skills\source-command-workflow-review-fix\SKILL.md` 和 `AI_Project_Notebook\.claude\commands\workflow\review-fix.md` 中，都定义了 “Tester 阻塞回环”。
    *   该回环描述表明，如果 Tester 产出的 `test-report.md` 结论为“阻塞”，则自动进入修复再测试的循环。
    *   `tests/` 目录下的大量测试文件（`test_*.py`）证明了存在一套可以运行和检查的测试框架，这正是 Tester agent 的任务目标。
    ```markdown
    # File: AI_Project_Notebook\.agents\skills\source-command-workflow-review-fix\SKILL.md
    ### Tester 阻塞回环 (tester -> generator-test-fix -> tester)
    - 若 tester 产出 `test-report.md` 且 `结论: 阻塞` 且 generator-test-fix 阶段存在：
      - 从 `test-report.md` 第一段提取 `失败测试数量`... 
      - 若返回 True（偏差缩小）：继续回环，spawn generator-test-fix 修复代码，再重新 spawn tester 验证
    ```

### 故事 7：作为系统维护者（Harness Maintainer），我希望系统能自动收集工作流中的反馈偏差，并生成规则演化建议，以便系统能持续学习和优化自身行为。

*   **优先级**: P1
*   **价值**: 这是整个系统的“自我进化”能力。通过分析历史数据发现重复模式，并提出规则变更建议，让工具越用越好用。

*   **代码证据**:
    *   `harness\scripts\generate_rule_evolution.py`: 该脚本的核心 `main()` 函数就是负责检查反馈信号并生成规则演化建议。
    *   `tests/test_generate_rule_evolution.py` 测试了该脚本的全部行为：无模式、有模式（生成 `rule-evolution-proposal.md`）、追加模式。
    ```python
    # tests/test_generate_rule_evolution.py
    def test_generates_proposal_when_pattern_exists(self):
        """存在 >=3 次重复模式时生成 rule-evolution-proposal.md。"""
        # ...
        engine = FeedbackEngine(signals_file=signals_file)
        for _ in range(3):
            engine.add_signal(_make_signal(rule_ref="coding-rules.md#4"))
        # ...
        main()
        assert os.path.exists(proposal_path)
        with open(proposal_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "变更理由" in content
        assert "待确认" in content
    ```

### 故事 8：作为 Harness 框架管理员，我希望系统能提供一个框架部署脚本，自动检测目标项目的技术栈，并生成个性化的适配建议，方便我将这套工作流快速应用到新项目中。

*   **优先级**: P1
*   **价值**: 这是框架通用化和扩展性的直接体现，降低了驱动其他项目的门槛。

*   **代码证据**:
    *   `harness\scripts\harness_deploy.py`: 项目的核心部署脚本。
    *   `tests/test_harness_deploy.py` 详细测试了各项功能，包括 `_detect_project_features` 函数能根据 `package.json` 识别出 `javascript`，根据 `go.mod` 识别出 `go` 等。
    ```python
    # tests/test_harness_deploy.py
    class TestDetectProjectFeatures:
        def test_detect_js_with_package_json(self):
            """包含 package.json 的目录正确识别为 javascript（spec 功能 A）。"""
            # ...
            features = _detect_project_features(tmp)
            assert "javascript" in features["languages"] or "typescript" in features["languages"]
    ```

## 2. 角色识别

从代码中可以识别出两个不同维度的角色：

| 角色 | 特征与证据 |
| :--- | :--- |
| **AI Agent (智能体)** | 系统内部由多个 AI Agent 扮演不同专业角色。证据：`.claude/agents/` 目录下定义了 `pm.md`, `planner.md`, `explorer.md`, `generator.md`, `reviewer.md`, `tester.md`, `harness_maintainer.md` 共7个Agent。每个Agent都有特定的职责和输出格式。 |
| **人类用户 (Human User)** | 系统的外部使用者。证据：`review-fix` 工作流中，当第三类问题出现时，要求 PM Agent 与“用户”进行逐项讨论；当 `should_continue_loop` 返回 `False` 时，要求“向用户展示...请用户决策” (`AI_Project_Notebook\.agents\skills\source-command-workflow-review-fix\SKILL.md`)。此外，`CLI_SCRIPT` (`app/analyze_project.py`) 的 `--help` 也面向人类用户。 |

## 3. 功能模块映射

| 故事 | 角色 | 模块路径 | HTTP 端点 | 证据文件 |
| :--- | :--- | :--- | :--- | :--- |
| **分析新项目 (故事1)** | 人类用户 | `app/analyzer/` | 无 (CLI) | `app/analyze_project.py`, `tests/test_analyze_project.py` |
| **需求澄清 (故事2)** | PM Agent | `AI_Project_Notebook\.claude\commands\workflow\review-fix.md`, `.claude/agents/pm.md` | 无 (AI工作流) | `review-fix.md`, `skill.md` (SKILL 文件) |
| **制定计划 (故事3)** | Planner Agent | `harness\workflow\review-fix.md` | 无 (AI工作流) | `review-fix.md` |
| **修改代码 (故事4)** | Generator Agent | `harness\workflow\review-fix.md` | 无 (AI工作流) | `review-fix.md` |
| **审查代码 (故事5)** | Reviewer Agent | `.claude/agents/reviewer.md` | 无 (AI工作流) | `reviewer.md` |
| **自动化测试 (故事6)** | Tester Agent | `.agents/skills/.../SKILL.md` | 无 (AI工作流) | `SKILL.md`, `tests/test_*.py` 文件 |
| **规则演化 (故事7)** | Harness Maintainer Agent | `harness\scripts\generate_rule_evolution.py` | 无 (CLI) | `generate_rule_evolution.py`, `test_generate_rule_evolution.py` |
| **框架部署 (故事8)** | 人类用户/Harness Maintainer Agent | `harness\scripts\harness_deploy.py` | 无 (CLI) | `harness_deploy.py`, `test_harness_deploy.py` |

## 4. 故事依赖关系

```mermaid
graph TD
    A[故事1: 分析新项目] --> B[故事8: 框架部署 (为新项目上下文)] 
    A --> C[故事2: 需求澄清与 Spec 修正]
    C --> D[故事3: 制定开发计划]
    D --> E[故事4: 修改代码]
    E --> F[故事5: 审查代码]
    F -- 第一类问题 --> E
    F -- 第二类问题 --> D
    F -- 第三类问题 --> C
    E --> G[故事6: 自动化测试]
    G -- 测试失败 --> E
    G -- 测试通过 --> H[故事7: 反馈收集与规则演化]
```

**总结**:
*   **故事1** 是所有工作的前提。
*   **故事8** 是框架通用化的前提。
*   故事2、3、4、5、6 构成了一个核心的“需求-计划-编码-审查-测试”闭环。这个闭环可以多次迭代，直到产出符合要求的代码。
*   **故事7** 是一个后台运行的、持续的“学习与优化”过程，它依赖于前面所有故事产出的数据和反馈。

## 5. 技术支持故事

### 故事 TS-1：作为系统，我希望在没有 LLM API Key 的情况下也能提供基础的项目分析，以保证核心功能的最低可用性。

*   **非功能性需求**: 可维护性 / 健壮性
*   **代码证据**:
    *   多个分析模块（如 `dimension_analyzer.py`, `domain_analyzer.py`, `overview.py`）都包含了 `_degraded_*` 降级函数。
    *   测试代码专门验证了降级模式，例如 `tests/test_dimension_analyzer.py` 中的 `TestDegradedArchitecture` 测试类。
    ```python
    # tests/test_dimension_analyzer.py
    class TestDegradedArchitecture:
        def test_analyze_architecture_degraded_when_no_key(self):
            from app.analyzer.dimension_analyzer import analyze_architecture
            with patch("app.analyzer.dimension_analyzer._check_llm_available", return_value=(False, {"api_key": None})):
                result = analyze_architecture("code text", "TestProject", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert "降级" in result["content"]
    ```

### 故事 TS-2：作为系统维护者，我希望工作流的自我升级行为是安全可控的，能够通过配置控制其自动程度、设置安全边界和去重窗口，以防止误操作或无限循环。

*   **非功能性需求**: 安全性 / 可配置性
*   **代码证据**:
    *   `harness/config/self-upgrade.yaml` (推测，根据 `diagnose_and_fix.py` 的 `_load_config` 函数推断)。
    *   `tests/test_diagnose_and_fix.py` 中的 `TestSafetyBoundary` 和 `TestDedup` 类。
    ```python
    # tests/test_diagnose_and_fix.py
    class TestSafetyBoundary:
        def test_insert_exceeds_limit_fails(self):
            """insert 51 行不通过。"""
            content = "\n".join(f"line_{i}" for i in range(51))
            passed, reason = _apply_safety_boundary(
                _make_fix_plan_simple("insert", content), self._safety()
            )
            assert

> 上下文引用: 参见 [architecture.md](architecture.md) 了解项目架构概览。