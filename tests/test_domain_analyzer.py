# test_domain_analyzer.py — LLM 业务板块识别测试 (TST-3)

import os
import sys
import json

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.analyzer.domain_analyzer import (
    analyze_business_domains,
    _build_domain_analysis_prompt,
    _parse_domain_response,
    _normalize_result,
    _degraded_domain_result,
)


# ===========================================================================
# TST-3: analyze_business_domains & helpers
# ===========================================================================

class TestDomainAnalyzer:

    # --- degraded mode (no API key) ---

    def test_degraded_mode_no_api_key(self):
        """无 API Key 时返回降级结果（不崩溃）"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        try:
            result = analyze_business_domains(
                {"found": [], "missing": []},
                "项目根: test",
                "test-project",
                enable_dotenv=False,
            )
            assert result["source"] == "degraded"
            assert "one_liner" in result
            assert "domains" in result
            assert len(result["domains"]) == 1
        finally:
            for k, v in saved.items():
                os.environ[k] = v

    def test_degraded_result_has_all_fields(self):
        """降级结果包含全部必需字段"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        try:
            result = _degraded_domain_result("myapp")
            assert "one_liner" in result
            assert "tech_stack" in result
            assert "domains" in result
            assert "relationships" in result
            assert "next_steps" in result
            assert "source" in result
            assert result["source"] == "degraded"
            assert len(result["next_steps"]) == 3
        finally:
            for k, v in saved.items():
                os.environ[k] = v

    def test_degraded_confidence_is_low(self):
        """降级结果中 domain 置信度为 '低'"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        try:
            result = _degraded_domain_result("p")
            for d in result["domains"]:
                assert d["confidence"] == "低"
        finally:
            for k, v in saved.items():
                os.environ[k] = v

    def test_degraded_one_liner_contains_project_name(self):
        """降级 one_liner 包含项目名称"""
        result = _degraded_domain_result("MyCoolProject")
        assert "MyCoolProject" in result["one_liner"]

    # --- prompt building ---

    def test_prompt_contains_guiding_file_content(self):
        """prompt 包含引导文件的内容文本"""
        guiding = {
            "found": [
                {"file_path": "README.md", "content": "# Hello World",
                 "label": "项目自述文档"},
            ],
            "missing": [],
        }
        prompt = _build_domain_analysis_prompt(guiding, "根: test", "testproj")
        assert "Hello World" in prompt
        assert "README.md" in prompt
        assert "testproj" in prompt

    def test_prompt_contains_missing_labels(self):
        """prompt 包含缺失引导文件的标注"""
        guiding = {
            "found": [],
            "missing": ["Node.js 依赖与脚本", "Python 打包配置"],
        }
        prompt = _build_domain_analysis_prompt(guiding, "根: test", "p")
        assert "Node.js 依赖与脚本" in prompt
        assert "Python 打包配置" in prompt
        assert "缺失的引导文件" in prompt

    def test_prompt_contains_dir_summary(self):
        """prompt 包含目录结构摘要"""
        prompt = _build_domain_analysis_prompt(
            {"found": [], "missing": []},
            "项目根: myapp\n├── src/\n│   └── utils/\n└── tests/",
            "myapp",
        )
        assert "项目根: myapp" in prompt
        assert "src/" in prompt
        assert "tests/" in prompt

    def test_prompt_contains_output_format_spec(self):
        """prompt 包含 JSON 输出格式说明和约束规则"""
        prompt = _build_domain_analysis_prompt(
            {"found": [], "missing": []}, "根: test", "test"
        )
        assert "one_liner" in prompt
        assert "domains" in prompt
        assert "relationships" in prompt
        assert "next_steps" in prompt
        assert "约束规则" in prompt
        assert "5-20" in prompt

    def test_prompt_empty_guiding_files_shows_placeholder(self):
        """无引导文件时 prompt 包含占位文字"""
        guiding = {"found": [], "missing": ["项目自述文档"]}
        prompt = _build_domain_analysis_prompt(guiding, "根: test", "p")
        assert "未找到任何引导文件" in prompt

    # --- JSON parsing ---

    def test_parse_valid_json(self):
        """正常 JSON 解析：返回标准化结果"""
        valid = json.dumps({
            "one_liner": "A test app",
            "tech_stack": ["Python"],
            "domains": [
                {"name": "Core", "description": "核心功能",
                 "evidence": "README", "paths": ["src"], "confidence": "高"},
            ],
            "relationships": [],
            "next_steps": ["Step 1"],
        })
        result = _parse_domain_response(valid)
        assert result is not None
        assert result["one_liner"] == "A test app"
        assert len(result["domains"]) == 1
        assert result["domains"][0]["confidence"] == "高"

    def test_parse_json_with_fence_wrapper(self):
        """```json 包裹的 JSON 正确解析"""
        wrapped = '```json\n' + json.dumps({
            "one_liner": "Wrapped app",
            "tech_stack": [],
            "domains": [
                {"name": "A", "description": "a", "evidence": "e",
                 "paths": ["a"], "confidence": "中"},
            ],
            "relationships": [],
            "next_steps": [],
        }) + '\n```'
        result = _parse_domain_response(wrapped)
        assert result is not None
        assert result["one_liner"] == "Wrapped app"

    def test_parse_json_with_fence_no_lang_label(self):
        """``` (无 json 标签) 包裹也能解析"""
        wrapped = '```\n' + json.dumps({
            "one_liner": "No label app",
            "tech_stack": [],
            "domains": [],
            "relationships": [],
            "next_steps": [],
        }) + '\n```'
        result = _parse_domain_response(wrapped)
        assert result is not None
        assert result["one_liner"] == "No label app"

    def test_parse_malformed_json_fallback(self):
        """畸形 JSON 返回 None（不抛异常）"""
        result = _parse_domain_response("这不是 JSON，是一段废话文字 { 没有结束")
        assert result is None

    def test_parse_json_missing_fields_gets_defaults(self):
        """JSON 缺少字段时由 _normalize_result 补全默认值"""
        incomplete = json.dumps({"one_liner": "minimal"})
        result = _parse_domain_response(incomplete)
        assert result is not None
        assert result["one_liner"] == "minimal"
        assert result["tech_stack"] == []
        assert result["domains"] == []
        assert result["relationships"] == []
        assert result["next_steps"] == []

    def test_parse_empty_string(self):
        """空字符串返回 None"""
        assert _parse_domain_response("") is None

    def test_parse_json_with_extra_text_before(self):
        """JSON 前有额外文字时仍能提取"""
        text = 'Here is the analysis result:\n' + json.dumps({
            "one_liner": "Extra text before",
            "tech_stack": [],
            "domains": [],
            "relationships": [],
            "next_steps": [],
        })
        result = _parse_domain_response(text)
        assert result is not None
        assert result["one_liner"] == "Extra text before"

    def test_parse_json_with_extra_text_after(self):
        """JSON 后有额外文字时仍能提取"""
        text = json.dumps({
            "one_liner": "Extra text after",
            "tech_stack": [],
            "domains": [],
            "relationships": [],
            "next_steps": [],
        }) + '\nSome notes...'
        result = _parse_domain_response(text)
        assert result is not None
        assert result["one_liner"] == "Extra text after"

    # --- normalize_result ---

    def test_normalize_adds_missing_fields(self):
        """空 dict 补充全部默认字段"""
        result = _normalize_result({})
        assert result["one_liner"] == ""
        assert result["tech_stack"] == []
        assert result["domains"] == []
        assert result["relationships"] == []
        assert result["next_steps"] == []

    def test_normalize_preserves_existing_fields(self):
        """已有字段不被覆盖"""
        result = _normalize_result({"one_liner": "custom", "tech_stack": ["Go"]})
        assert result["one_liner"] == "custom"
        assert result["tech_stack"] == ["Go"]
        assert result["domains"] == []
        assert result["relationships"] == []

    # --- analyze_business_domains with fake key (LLM call fails -> degraded) ---

    def test_with_fake_api_key_returns_degraded_not_crash(self):
        """配置假 API Key 时 LLM 调用失败返回降级结果（不崩溃）"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        os.environ["LLM_API_KEY"] = "fake-test-key-that-does-not-exist"
        # Use a non-routable endpoint for instant failure
        os.environ["LLM_API_BASE"] = "http://127.0.0.1:1"

        try:
            result = analyze_business_domains(
                {"found": [], "missing": []},
                "项目根: test",
                "test-proj",
                enable_dotenv=False,
            )
            # Should return degraded (LLM call failed with connection error)
            assert "source" in result
            # Either degraded or LLM (unlikely when endpoint is bad)
            assert result["source"] in ("degraded", "llm")
            assert len(result["domains"]) >= 1
        finally:
            for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE",
                      "LLM_MODEL"):
                os.environ.pop(k, None)
            for k, v in saved.items():
                os.environ[k] = v
