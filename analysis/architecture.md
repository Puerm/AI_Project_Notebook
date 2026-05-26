# AI_Project_Notebook — 架构分析

好的，没问题。作为资深软件架构师，我帮你把这份“AI_Project_Notebook”项目梳理清楚。

---

# AI_Project_Notebook 架构说明

嘿，新来的同事，欢迎！这份文档是我们项目的“活地图”，看完它，你就知道咱们代码仓库里到底藏了什么宝贝，每个部分是怎么分工协作的。

## 1. 一句话总结

这是一个“**AI 驱动的项目分析工作台**”。它自己本身也是个项目，但它的核心工作是帮你**分析任何一个你丢给它的项目**，输出三份报告：项目架构图、用户故事、潜在风险。如果它发现自己哪里做得不好，还会尝试“自我修复”。

简单说，它是个专业的“项目体检医生”，而且是个能给自己开药的医生。

- **技术栈补充**：核心是 Python 后端，通过调用 Claude 或 GPT 这样的 AI 模型来进行深度的、语义化的分析。

## 2. 模块地图

下面是项目的骨架，主要模块及其职责一目了然。

| 模块 | 路径 | 它做什么 | 关键文件 |
| :--- | :--- | :--- | :--- |
| **分析引擎 (核心大脑)** | `app/analyzer/` | 这是项目的**绝对核心**。它负责所有分析逻辑：扫描目标项目的目录、读取关键文件、调用 AI 模型进行分析，最后写出分析报告。 | `app/analyze_project.py` (主入口), <br>`app/analyzer/dimension_analyzer.py` (按维度分析), <br>`app/analyzer/digest_collector.py` (收集文件) |
| **Harness 框架 (可靠后勤)** | `harness/` | 这是一个**通用的项目管理、自动化、自我维护框架**。它不是只为我们的分析引擎服务，而是被设计成可以注入到任意项目里，帮助那个项目进行结构检查、规则管理和工作流跟踪。你可以把它理解成一个能自我演化的“项目管理助手”。 | `harness/scripts/check_structure.py` (结构检查), <br>`harness/scripts/init_project.py` (部署框架到新项目), <br>`harness/scripts/diagnose_and_fix.py` (自我诊断和修复) |
| **AI 角色定义** | `.claude/agents/` | 这是我们为 AI 助手（Claude）定义的**不同“身份”或“角色”**。比如`pm.md`是产品经理角色，`tester.md`是测试角色。AI 会通过阅读这些文件来了解在工作流中该如何思考和行动。 | `.claude/agents/pm.md` (产品经理), <br>`.claude/agents/generator.md` (代码生成器) |
| **工作流定义** | `.claude/commands/workflow/` | 定义了 AI 助手应该**遵循的“工作流程”**。比如“全流程（full-cycle）”或“快速修复（quick-fix）”。这些是你指挥AI完成任务的“指令手册”。 | `.claude/commands/workflow/full-cycle.md` (全流程), <br>`.claude/commands/workflow/quick-fix.md` (快速修复) |
| **运行时状态与反馈** | `harness/state/` & `harness/feedback/` | 这个模块是项目的“**病历本**”和“**工作日志**”。它记录了工作流的当前进度 (`current-workflow.json`)、AI 在运行中捕捉到的各种反馈信号 (`feedback-signals.json`)，以及历史上自我修复的记录 (`upgrade-history.json`)。 | `harness/state/feedback-signals.json` (反馈信号), <br> `harness/state/upgrade-history.json` (升级历史) |
| **配置中心** | `harness/config/` | “**保险柜**”，存放项目的关键配置信息。比如项目的基本描述 (`project.yaml`) 和控制自我修复行为的安全规则 (`self-upgrade.yaml`)。 | `harness/config/project.yaml` (项目配置), <br>`harness/config/self-upgrade.yaml` (自我升级配置) |

## 3. 模块之间的关系

这些模块不是孤立的，它们通过一个清晰的“**分析-反馈-修复**”循环协作。

1.  **开始分析**：`app/analyze_project.py` 启动，这是整个流程的入口。
2.  **扫描与收集**：分析引擎首先派出 `digest_collector.py` 和 `guiding_files.py` 去扫描目标项目，收集代码文件和配置文件。同时，`scanner.py` 会分析目录结构。
3.  **生成概要**：`domain_analyzer.py` 和 `overview.py` 能快速识别项目用的语言和可能的业务领域，形成初步判断。
4.  **AI 深度分析**：收集到的信息被组织一下，发给 AI 模型。`dimension_analyzer.py` 会分工协作：
    - 一个扮演“架构师”的角色，分析项目架构。
    - 一个扮演“产品经理”的角色，分析用户故事。
    - 一个扮演“安全专家”的角色，分析潜在风险。
    分析结果会写入 `analysis/` 目录下的三个文件中。
5.  **项目地图输出**：所有的分析结果最后会被 `map_writer.py` 汇总，生成一份图文并茂的 `project-map/project-overview.md` 报告。
6.  **反馈与自我修复 (Harness 的生命周期)**：
    - 在 AI 工作的过程中，**如果在任何规则或工作流中发现不对劲的地方，它就会记录一个“反馈信号”（`FeedbackSignal`）**，并存到 `harness/state/feedback-signals.json` 里。
    - `harness/scripts/diagnose_and_fix.py` 定时巡检这个“病历本”。如果某个规则反复报错（比如同一错误出现多次），它会判定这个规则可能需要优化。
    - 它会再次调用 AI，分析这个反复出现的错误，并生成一个“修复方案”（`fix_plan`）。
    - 根据 `self-upgrade.yaml` 的配置，这个修复可能是全自动的（比如修改一个简单的规则），也可能是半自动的（需要你确认）。所有成功的修复都会被记录到 `upgrade-history.json` 里。

**简单说**：核心分析引擎负责分析外部世界，而 Harness 框架则负责监控并优化分析引擎自身，形成一个能不断学习和进化的闭环。

## 4. 技术选型

| 技术组件 | 用途 | 证据 (文件/配置) |
| :--- | :--- | :--- |
| **Python 3** | 项目主语言，编写分析引擎、所有脚本和框架代码。 | `project.yaml` 中声明 `languages: - python` |
| **pytest** | 项目的测试框架。 | `project.yaml` 中声明 `test_framework: pytest` |
| **Claude / GPT (LLM)** | 进行高级、语义化的分析，如识别业务板块、理解代码逻辑、生成修复方案。这是“智能”的来源。 | `app/analyzer/llm_assistant.py` 中通过环境变量（如 `ANTHROPIC_API_KEY`）配置和调用。 |
| **codebase-digest (cdigest)** | 一个外部库，用于快速扫描项目目录，收集所有代码文件及其内容，为 AI 分析提供“食粮”。 | `app/analyzer/digest_collector.py` 中导入并调用 `codebase_digest`。 |
| **Git** | 用于实现“沙盒测试”。在自我修复时，它会创建一个 Git Worktree（一个隔离的分支）来应用修复方案，在确保测试通过后，再将修改合并回来。 | `harness/scripts/diagnose_and_fix.py` 中大量使用了 Git 命令 (`git worktree`, `git merge` 等)。 |

## 5. 值得注意的设计

-  **渐进式信息披露 (Progressive Disclosure)**：我们的分析引擎不是一股脑把所有代码都丢给 AI，而是**分步骤、有筛选地提供信息**。
    - **第1步，概览**：先用 `overview.py` 猜项目大概是什么。
    - **第2步，筛选**：`digest_collector.py` 里的 `filter_for_architecture`、`filter_for_user_stories`、`filter_for_risk` 这几个函数，会**根据不同的分析目标，只将最相关的文件分组打包**给不同的 AI 角色。
    - **为什么好？** 这样做非常高效。AI 模型对上下文的处理能力有限。一次性塞入整个项目的所有代码，AI 会“看不过来”，容易忽视细节。这种渐进式、分而治之的策略，能让 AI 的分析更聚焦、更准确，同时还能节省 API 调用的成本（因为不相关的代码没有传递出去）。

-  **“自举”的 Harness 框架**：`harness/` 这个目录本身就是一个独立的、可以自我演化的项目管理框架。神奇的是，它**也被用于管理它自身所在的这个项目**。
    - `harness/scripts/check_structure.py` 会检查项目自己的结构。
    - `harness/state/feedback-signals.json` 记录了项目自身工作流（角色协作）中的问题。
    - `harness/scripts/diagnose_and_fix.py` 可以尝试修复项目自己的规则文件（例如，修改 `.claude/agents/` 下的文件）。

    - **为什么好？** 这很酷。它实现了“**用自己的规则来管理自己**”的循环。当我们的工作流或角色定义有缺陷时，系统自己就能发现并尝试改进，这大大降低了项目维护的“熵增”，让规则和流程能随着项目一起生长，而不是等我们手动去同步。

-  **安全的“沙盒”验证机制**：在自我修复流程中，`diagnose_and_fix.py` 不会直接修改源代码。它会先创建一个 **Git Worktree**（本质上是一个隔离的工作副本），在副本中应用修复。
    - **为什么好？** 这是**防止 AI “好心办坏事”的关键**。如果 AI 生成的修复方案有 bug，导致测试失败，它**只会影响那个隔离的“沙盒”**，而不会破坏主项目的正常功能。只有沙盒里的所有测试都通过了，修复才会被合并。这个设计将自动化的风险降到了最低。

## 6. 可改进的地方

1.  **对 `codebase-digest` 的强依赖**：
    - **问题**：`digest_collector.py` 的核心功能强依赖于 `codebase-digest` 这个第三方库。如果它没有安装，项目虽然能运行，但会缺失深度的“AI聚焦分析”能力，直接退化到只输出一个基本的降级报告。这在项目的“降级”体验上做得还可以，但功能完整性上是个明显的短板。
    - **改进方向**：可以考虑增加一个纯 Python 的**降级实现**。当 `codebase-digest` 不存在时，分析引擎可以自己动手，用 `scanner.py` 和 `parser.py` 实现一个简化版的文件收集和筛选功能。这能保证项目在任何环境下都能提供完整的基础分析能力，而不仅仅是输出一个“未安装”的提示。

2.  **自我修复流程的“冗长”历史**：
    - **问题**：`harness/state/upgrade-history.json` 记录了非常多的历史修复尝试。其中有大量失败（`failed`）、降级（`degraded`）的记录。例如，对一个 `.claude/agents/pm.md` 文件，在短时间内就生成了超过 10 次失败或降级的修复记录。
    - **改进方向**：这暴露出自我修复的**成功率和稳定性还有提升空间**，或者是在决策逻辑上过于“乐观”了，导致反复尝试。可以考虑：
        - **引入冷静期**：当对一个 `signal_id` 的修复连续失败 N 次后，应该增加一个更长的“冷静期”（比如7天或14天），而不是24小时。因为24小时内反复尝试通常不会产生截然不同的结果。
        - **失败模式学习**：收集失败的原因（如 “沙盒验证失败”，“用户拒绝”），在下次生成修复方案时，作为负面例子提供给 AI，提示它“上次你这么修不行，换个思路”。

3.  **模块间耦合与 “Harness” 的边界**：
    - **问题**：虽然设计上是 Harness 框架管理自己，但我们看 `app/analyzer/dimension_analyzer.py` 和 `harness/scripts/diagnose_and_fix.py` 这个核心分析引擎和自愈引擎，它们之间共享了大量公共代码。例如，两个文件都实现了自己的 `_call_llm` 和 `_get_llm_config` 功能（只是实现略有不同）。
    - **改进方向**：可以考虑将这些**公共的 LLM 调用工具函数**从 `app/analyzer/llm_assistant.py` 中提升到一个更顶层的共享位置（比如项目根目录的 `utils/` 或 `lib/` 包中）。`Harness` 框架和 `App` 分析引擎都依赖这个公共库，而不是各自实现一套。这能减少代码重复，并使 LLM 的调用行为更加一致，便于统一维护和升级（比如统一添加重试逻辑、日志记录等）。