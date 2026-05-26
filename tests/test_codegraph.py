# test_codegraph.py — TST-1: CodeGraph 集成核心模块 + TST-3: tool-use LLM 调用测试

import os
import sys
import json
import sqlite3
import tempfile
import shutil
from unittest.mock import patch, MagicMock

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.analyzer.codegraph import (
    detect_codegraph_db,
    connect_codegraph_db,
    extract_schema_summary,
    execute_query,
    format_schema_for_llm,
)
from app.analyzer.llm_assistant import _call_llm_with_tools, _get_llm_config


def _make_tmpdir():
    return tempfile.mkdtemp()


def _create_test_db(db_path):
    """Create a test SQLite db with symbols and calls tables."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE symbols (id INTEGER PRIMARY KEY, name TEXT, kind TEXT, language TEXT)"
    )
    conn.execute("CREATE TABLE calls (caller_id INTEGER, callee_id INTEGER)")
    conn.execute("INSERT INTO symbols VALUES (1, 'main', 'function', 'python')")
    conn.execute("INSERT INTO symbols VALUES (2, 'helper', 'function', 'python')")
    conn.execute("INSERT INTO calls VALUES (1, 2)")
    conn.execute("CREATE INDEX idx_symbols_kind ON symbols(kind)")
    conn.commit()
    conn.close()


def _open_readonly_conn(db_path):
    """Open a read-only connection to db, with proper URI handling."""
    # Normalize path: convert backslashes to forward slashes for URI
    db_path_normalized = db_path.replace("\\", "/")
    uri = f"file:{db_path_normalized}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ========================================================================
# TST-1: detect_codegraph_db
# ========================================================================


class TestDetectCodegraphDb:
    """detect_codegraph_db — 数据库检测"""

    def test_db_exists_returns_path(self):
        """存在 .codegraph/codegraph.db 时返回完整路径"""
        tmp = _make_tmpdir()
        try:
            db_dir = os.path.join(tmp, ".codegraph")
            os.makedirs(db_dir)
            db_path = os.path.join(db_dir, "codegraph.db")
            with open(db_path, "w") as f:
                f.write("")
            result = detect_codegraph_db(tmp)
            assert result == db_path
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_db_not_exists_returns_none(self):
        """目标目录下无 .codegraph/codegraph.db 返回 None"""
        tmp = _make_tmpdir()
        try:
            result = detect_codegraph_db(tmp)
            assert result is None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_codegraph_dir_exists_but_no_db_returns_none(self):
        """.codegraph/ 目录存在但无 codegraph.db 返回 None"""
        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, ".codegraph"))
            result = detect_codegraph_db(tmp)
            assert result is None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_path_not_directory_returns_none(self):
        """目标路径不是目录时返回 None"""
        result = detect_codegraph_db("/nonexistent/path/12345")
        assert result is None

    def test_path_is_file_returns_none(self):
        """目标路径是文件时返回 None"""
        tmp = _make_tmpdir()
        try:
            fp = os.path.join(tmp, "file.txt")
            with open(fp, "w") as f:
                f.write("hello")
            result = detect_codegraph_db(fp)
            assert result is None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ========================================================================
# TST-1: connect_codegraph_db
# ========================================================================


class TestConnectCodegraphDb:
    """connect_codegraph_db — 只读连接"""

    def test_valid_db_returns_connection(self):
        """有效 db 路径返回 sqlite3.Connection 且 row_factory 正确设置"""
        tmp = _make_tmpdir()
        try:
            db_path = os.path.join(tmp, "test.db")
            _create_test_db(db_path)
            conn = connect_codegraph_db(db_path)
            assert isinstance(conn, sqlite3.Connection)
            # Verify row_factory is sqlite3.Row (rows accessed by name)
            cursor = conn.execute("SELECT name FROM symbols LIMIT 1")
            row = cursor.fetchone()
            assert row["name"] in ("main", "helper")
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_connection_is_readonly(self):
        """只读连接无法执行写入操作"""
        tmp = _make_tmpdir()
        try:
            db_path = os.path.join(tmp, "test.db")
            _create_test_db(db_path)
            conn = connect_codegraph_db(db_path)
            try:
                conn.execute("INSERT INTO symbols VALUES (99, 'x', 'f', 'py')")
                assert False, "只读连接应拒绝写入"
            except sqlite3.OperationalError:
                pass  # Expected: read-only database
            finally:
                conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_invalid_path_raises_exception(self):
        """无效路径抛出异常"""
        try:
            connect_codegraph_db("/nonexistent/path/to/db.db")
            assert False, "Expected exception for invalid path"
        except Exception:
            pass  # Expected


# ========================================================================
# TST-1: extract_schema_summary
# ========================================================================


class TestExtractSchemaSummary:
    """extract_schema_summary — Schema 摘要提取"""

    def test_db_with_tables_returns_full_summary(self):
        """含表的 db 返回完整摘要：表名、列名、行数、索引、CREATE TABLE"""
        tmp = _make_tmpdir()
        try:
            db_path = os.path.join(tmp, "test.db")
            _create_test_db(db_path)
            conn = _open_readonly_conn(db_path)
            summary = extract_schema_summary(conn)
            conn.close()

            assert "tables" in summary
            assert "language_stats" in summary
            table_names = [t["name"] for t in summary["tables"]]
            assert "symbols" in table_names
            assert "calls" in table_names

            # 验证 symbols 表的详细信息
            sym = [t for t in summary["tables"] if t["name"] == "symbols"][0]
            assert sym["row_count"] == 2
            col_names = [c["name"] for c in sym["columns"]]
            assert "id" in col_names
            assert "name" in col_names
            assert "kind" in col_names
            assert "language" in col_names
            assert sym["create_sql"] is not None
            # 验证索引信息
            idx_names = [i["name"] for i in sym["indexes"]]
            assert "idx_symbols_kind" in idx_names
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_empty_db_returns_empty_tables(self):
        """空 db 返回空表列表不崩溃"""
        tmp = _make_tmpdir()
        try:
            db_path = os.path.join(tmp, "empty.db")
            conn = sqlite3.connect(db_path)
            conn.close()
            conn = _open_readonly_conn(db_path)
            summary = extract_schema_summary(conn)
            conn.close()

            assert summary["tables"] == []
            assert summary["language_stats"] == {}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_language_stats_detected(self):
        """从含 language 列的表提取语言分布统计"""
        tmp = _make_tmpdir()
        try:
            db_path = os.path.join(tmp, "lang.db")
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE symbols (id INTEGER, name TEXT, language TEXT, extension TEXT)"
            )
            conn.execute("INSERT INTO symbols VALUES (1, 'a', 'python', '.py')")
            conn.execute("INSERT INTO symbols VALUES (2, 'b', 'javascript', '.js')")
            conn.execute("INSERT INTO symbols VALUES (3, 'c', 'python', '.py')")
            conn.commit()
            conn.close()

            conn = _open_readonly_conn(db_path)
            summary = extract_schema_summary(conn)
            conn.close()

            assert "language_stats" in summary
            lang_stats = summary["language_stats"]
            assert len(lang_stats) >= 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ========================================================================
# TST-1: execute_query
# ========================================================================


class TestExecuteQuery:
    """execute_query — 只读 SELECT 查询执行与注入防护"""

    def _setup_conn(self, tmp):
        db_path = os.path.join(tmp, "test.db")
        _create_test_db(db_path)
        return _open_readonly_conn(db_path)

    def test_valid_select_returns_list_of_dict(self):
        """有效 SELECT 查询返回 list[dict] 格式，数据正确"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            rows = execute_query(conn, "SELECT * FROM symbols ORDER BY id")
            conn.close()
            assert isinstance(rows, list)
            assert len(rows) == 2
            assert isinstance(rows[0], dict)
            assert rows[0]["name"] == "main"
            assert rows[0]["kind"] == "function"
            assert rows[1]["name"] == "helper"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_select_with_where_returns_filtered(self):
        """WHERE 子句正确过滤结果"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            rows = execute_query(conn, "SELECT * FROM symbols WHERE name = 'main'")
            conn.close()
            assert len(rows) == 1
            assert rows[0]["name"] == "main"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_empty_result_returns_empty_list(self):
        """无匹配结果返回空列表不崩溃"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            rows = execute_query(conn, "SELECT * FROM symbols WHERE name = 'nonexistent'")
            conn.close()
            assert rows == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_insert_rejected(self):
        """INSERT 被拒绝并抛出 ValueError"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            try:
                execute_query(conn, "INSERT INTO symbols VALUES (99, 'x', 'f', 'py')")
                conn.close()
                assert False, "Expected ValueError for INSERT"
            except ValueError as e:
                assert "只允许 SELECT" in str(e)
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_update_rejected(self):
        """UPDATE 被拒绝"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            try:
                execute_query(conn, "UPDATE symbols SET name='x'")
                conn.close()
                assert False, "Expected ValueError"
            except ValueError:
                pass
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_delete_rejected(self):
        """DELETE 被拒绝"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            try:
                execute_query(conn, "DELETE FROM symbols")
                conn.close()
                assert False, "Expected ValueError"
            except ValueError:
                pass
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_drop_rejected(self):
        """DROP 被拒绝"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            try:
                execute_query(conn, "DROP TABLE symbols")
                conn.close()
                assert False, "Expected ValueError"
            except ValueError:
                pass
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_multi_statement_injection_rejected(self):
        """多语句 SQL 注入（分号分隔）被拒绝"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            try:
                execute_query(conn, "SELECT * FROM symbols; DROP TABLE symbols;")
                conn.close()
                assert False, "Expected ValueError"
            except ValueError as e:
                assert "多语句" in str(e) or "禁止" in str(e)
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_leading_whitespace_select_works(self):
        """SELECT 前有空白字符仍正常执行"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            rows = execute_query(conn, "   SELECT * FROM symbols")
            conn.close()
            assert len(rows) == 2
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_lowercase_select_works(self):
        """小写 'select' 大小写不敏感检查通过"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            rows = execute_query(conn, "select * from symbols")
            conn.close()
            assert len(rows) == 2
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_results_exceeding_max_rows_truncated(self):
        """结果超出 max_rows 时截断并添加 _truncated 标记"""
        tmp = _make_tmpdir()
        try:
            db_path = os.path.join(tmp, "big.db")
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, val TEXT)")
            for i in range(5):
                conn.execute("INSERT INTO items (val) VALUES (?)", (f"item{i}",))
            conn.commit()
            conn.close()

            conn = _open_readonly_conn(db_path)
            rows = execute_query(conn, "SELECT * FROM items", max_rows=2)
            conn.close()
            assert len(rows) == 3  # 2 actual rows + 1 truncation message
            assert rows[-1]["_truncated"] is True
            assert "截断" in rows[-1]["_message"]
            assert "5" in rows[-1]["_message"]  # total count in message
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_results_within_max_rows_not_truncated(self):
        """结果未超过 max_rows 时不添加截断标记"""
        tmp = _make_tmpdir()
        try:
            conn = self._setup_conn(tmp)
            rows = execute_query(conn, "SELECT * FROM symbols", max_rows=200)
            conn.close()
            assert len(rows) == 2
            for row in rows:
                assert "_truncated" not in row
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ========================================================================
# TST-1: format_schema_for_llm
# ========================================================================


class TestFormatSchemaForLlm:
    """format_schema_for_llm — Schema Markdown 格式化"""

    def test_normal_schema_outputs_markdown(self):
        """正常 schema dict 输出含 Markdown 格式：表名、列、索引、语言分布"""
        schema = {
            "tables": [
                {
                    "name": "symbols",
                    "columns": [
                        {"name": "id", "type": "INTEGER"},
                        {"name": "name", "type": "TEXT"},
                    ],
                    "row_count": 100,
                    "indexes": [{"name": "idx_name", "unique": False}],
                    "create_sql": "CREATE TABLE symbols (...)",
                },
                {
                    "name": "calls",
                    "columns": [
                        {"name": "caller_id", "type": "INTEGER"},
                    ],
                    "row_count": 50,
                    "indexes": [],
                    "create_sql": "CREATE TABLE calls (...)",
                },
            ],
            "language_stats": {
                "symbols.language": {"python": 80, "javascript": 20},
            },
        }
        result = format_schema_for_llm(schema)
        assert "CodeGraph" in result
        assert "symbols" in result
        assert "calls" in result
        assert "id (INTEGER)" in result
        assert "name (TEXT)" in result
        assert "idx_name" in result
        assert "python" in result
        assert "80" in result
        # Markdown 格式检查
        assert "## " in result
        assert "### " in result

    def test_empty_schema_does_not_crash(self):
        """空 schema（无表）不崩溃，显示占位文本"""
        result = format_schema_for_llm({"tables": [], "language_stats": {}})
        assert "数据库中没有用户表" in result
        assert "CodeGraph" in result  # 标题仍然存在

    def test_schema_with_no_indexes_does_not_crash(self):
        """无索引的表不崩溃"""
        schema = {
            "tables": [
                {
                    "name": "t1",
                    "columns": [{"name": "a", "type": "TEXT"}],
                    "row_count": 0,
                    "indexes": [],
                    "create_sql": "CREATE TABLE t1 (a TEXT)",
                },
            ],
            "language_stats": {},
        }
        result = format_schema_for_llm(schema)
        assert "t1" in result
        assert "a (TEXT)" in result

    def test_schema_with_none_row_count_shows_unknown(self):
        """行数为 None 时显示 '未知'"""
        schema = {
            "tables": [
                {
                    "name": "t1",
                    "columns": [],
                    "row_count": None,
                    "indexes": [],
                    "create_sql": "CREATE TABLE t1 ()",
                },
            ],
            "language_stats": {},
        }
        result = format_schema_for_llm(schema)
        assert "未知" in result

    def test_schema_no_language_stats_no_crash(self):
        """无语言统计时正常输出不崩溃"""
        schema = {
            "tables": [
                {
                    "name": "t1",
                    "columns": [{"name": "a", "type": "INTEGER"}],
                    "row_count": 1,
                    "indexes": [],
                    "create_sql": "CREATE TABLE t1 (a INTEGER)",
                },
            ],
            "language_stats": {},
        }
        result = format_schema_for_llm(schema)
        assert "t1" in result
        assert "共 1 个表" in result


# ========================================================================
# TST-3: _call_llm_with_tools — tool-use LLM 多轮调用
# ========================================================================


def _mock_urlopen_response(response_data):
    """Create a mock object suitable for `with urlopen(...) as resp:` context manager."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode("utf-8")
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    return mock_cm


class TestCallLlmWithTools:
    """_call_llm_with_tools — 带 tool use 的多轮 LLM 调用"""

    def test_no_api_key_returns_none(self):
        """无 API Key 时返回 None"""
        config = {
            "api_key": None,
            "api_base": None,
            "model": "gpt-4o-mini",
            "provider": "openai",
        }
        result = _call_llm_with_tools(
            system_prompt="test",
            user_prompt="test",
            tools_def=[],
            tool_handler=lambda n, a: "ok",
            config=config,
        )
        assert result is None

    def test_openai_tool_handler_called_with_correct_args(self):
        """OpenAI 格式: tool_handler 被正确调用且参数解析正确"""
        tool_handler_calls = []

        def handler(tool_name, arguments):
            tool_handler_calls.append((tool_name, arguments))
            return json.dumps([{"result": "ok"}])

        mock_first_response = {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": "Let me check the symbols.",
                        "tool_calls": [
                            {
                                "id": "call_001",
                                "function": {
                                    "name": "query_codegraph",
                                    "arguments": json.dumps({
                                        "sql": "SELECT * FROM symbols LIMIT 10",
                                    }),
                                },
                            },
                        ],
                    },
                },
            ],
        }
        mock_final_response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": "Analysis complete.",
                    },
                },
            ],
        }

        mock_urlopen = MagicMock(side_effect=[
            _mock_urlopen_response(mock_first_response),
            _mock_urlopen_response(mock_final_response),
        ])

        config = {
            "api_key": "sk-test-123",
            "api_base": None,
            "model": "gpt-4o-mini",
            "provider": "openai",
        }

        with patch("app.analyzer.llm_assistant.urllib.request.urlopen", mock_urlopen):
            result = _call_llm_with_tools(
                system_prompt="test",
                user_prompt="test",
                tools_def=[{"type": "function", "function": {"name": "query_codegraph"}}],
                tool_handler=handler,
                config=config,
                max_rounds=5,
            )

        assert len(tool_handler_calls) == 1
        assert tool_handler_calls[0][0] == "query_codegraph"
        assert tool_handler_calls[0][1]["sql"] == "SELECT * FROM symbols LIMIT 10"
        assert result == "Analysis complete."

    def test_anthropic_tool_handler_called_with_correct_args(self):
        """Anthropic 格式: tool_use block 被正确解析，tool_handler 参数正确"""
        tool_handler_calls = []

        def handler(tool_name, arguments):
            tool_handler_calls.append((tool_name, arguments))
            return json.dumps([{"name": "main", "kind": "function"}])

        mock_first_response = {
            "stop_reason": "tool_use",
            "content": [
                {"type": "text", "text": "Let me query the database."},
                {
                    "type": "tool_use",
                    "id": "tool_001",
                    "name": "query_codegraph",
                    "input": {"sql": "SELECT name, kind FROM symbols"},
                },
            ],
        }
        mock_final_response = {
            "stop_reason": "end_turn",
            "content": [
                {"type": "text", "text": "Found main function."},
            ],
        }

        mock_urlopen = MagicMock(side_effect=[
            _mock_urlopen_response(mock_first_response),
            _mock_urlopen_response(mock_final_response),
        ])

        config = {
            "api_key": "sk-ant-test",
            "api_base": None,
            "model": "claude-3-5-sonnet-20241022",
            "provider": "anthropic",
        }

        with patch("app.analyzer.llm_assistant.urllib.request.urlopen", mock_urlopen):
            result = _call_llm_with_tools(
                system_prompt="test",
                user_prompt="test",
                tools_def=[{"name": "query_codegraph"}],
                tool_handler=handler,
                config=config,
                max_rounds=5,
            )

        assert len(tool_handler_calls) == 1
        assert tool_handler_calls[0][0] == "query_codegraph"
        assert tool_handler_calls[0][1] == {"sql": "SELECT name, kind FROM symbols"}
        assert "Found main function." in result or result == "Found main function."

    def test_max_rounds_reached_terminates_and_returns_text(self):
        """多轮对话达到 max_rounds 后终止并返回累积文本"""
        tool_handler_calls = []

        def handler(tool_name, arguments):
            tool_handler_calls.append(arguments)
            return json.dumps([{"row": 1}])

        # Always return tool_use so that max_rounds is reached
        same_response = {
            "stop_reason": "tool_use",
            "content": [
                {"type": "text", "text": "Round N"},
                {
                    "type": "tool_use",
                    "id": "tool_001",
                    "name": "query_codegraph",
                    "input": {"sql": "SELECT 1"},
                },
            ],
        }

        mock_urlopen = MagicMock(side_effect=[
            _mock_urlopen_response(same_response) for _ in range(6)
        ])

        config = {
            "api_key": "sk-ant-test",
            "api_base": None,
            "model": "claude-3-5-sonnet-20241022",
            "provider": "anthropic",
        }

        with patch("app.analyzer.llm_assistant.urllib.request.urlopen", mock_urlopen):
            result = _call_llm_with_tools(
                system_prompt="test",
                user_prompt="test",
                tools_def=[{"name": "query_codegraph"}],
                tool_handler=handler,
                config=config,
                max_rounds=3,
            )

        # Should terminate after max_rounds (3), not call handler more than max_rounds
        assert len(tool_handler_calls) <= 3
        # Returns collected text
        assert result is not None

    def test_tool_handler_exception_caught_continues_loop(self):
        """tool_handler 抛出异常被捕获，包含异常信息返回给 LLM，循环继续"""
        def handler(tool_name, arguments):
            raise RuntimeError("simulated tool error")

        mock_first_response = {
            "stop_reason": "tool_use",
            "content": [
                {"type": "tool_use", "id": "t1", "name": "query_codegraph",
                 "input": {"sql": "SELECT 1"}},
            ],
        }
        mock_final_response = {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "Done despite error."}],
        }

        mock_urlopen = MagicMock(side_effect=[
            _mock_urlopen_response(mock_first_response),
            _mock_urlopen_response(mock_final_response),
        ])

        config = {
            "api_key": "sk-ant-test",
            "api_base": None,
            "model": "claude-3-5-sonnet-20241022",
            "provider": "anthropic",
        }

        with patch("app.analyzer.llm_assistant.urllib.request.urlopen", mock_urlopen):
            result = _call_llm_with_tools(
                system_prompt="test",
                user_prompt="test",
                tools_def=[{"name": "query_codegraph"}],
                tool_handler=handler,
                config=config,
                max_rounds=5,
            )

        # Loop should continue after exception, final text returned
        assert result is not None

    def test_tool_handler_receives_empty_arguments_defaults(self):
        """tool_handler 收到空参数字典时正常调用"""
        tool_handler_calls = []

        def handler(tool_name, arguments):
            tool_handler_calls.append((tool_name, arguments))
            return "ok"

        mock_first = {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_x",
                                "function": {
                                    "name": "query_codegraph",
                                    "arguments": "{}",
                                },
                            },
                        ],
                    },
                },
            ],
        }
        mock_final = {
            "choices": [
                {"finish_reason": "stop", "message": {"content": "OK"}},
            ],
        }

        mock_urlopen = MagicMock(side_effect=[
            _mock_urlopen_response(mock_first),
            _mock_urlopen_response(mock_final),
        ])

        config = {
            "api_key": "sk-test",
            "api_base": None,
            "model": "gpt-4o-mini",
            "provider": "openai",
        }

        with patch("app.analyzer.llm_assistant.urllib.request.urlopen", mock_urlopen):
            result = _call_llm_with_tools(
                system_prompt="test",
                user_prompt="test",
                tools_def=[],
                tool_handler=handler,
                config=config,
                max_rounds=5,
            )

        assert len(tool_handler_calls) == 1
        assert tool_handler_calls[0][1] == {}
