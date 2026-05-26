# codegraph.py — CodeGraph 集成核心模块：SQLite 符号知识图谱检测、Schema 提取、只读查询
import os
import sqlite3


def detect_codegraph_db(target_path: str) -> str | None:
    """检查 target_path 下是否存在 .codegraph/codegraph.db，返回 db 路径或 None。"""
    if not os.path.isdir(target_path):
        return None
    db_path = os.path.join(target_path, ".codegraph", "codegraph.db")
    if os.path.isfile(db_path):
        return db_path
    return None


def connect_codegraph_db(db_path: str) -> sqlite3.Connection:
    """以只读模式打开 SQLite 连接 (uri=True, mode=ro)。"""
    uri_path = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri_path, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def extract_schema_summary(conn: sqlite3.Connection) -> dict:
    """读取 sqlite_master 获取表名、CREATE TABLE SQL、行数和语言分布统计。"""
    tables = []
    cursor = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    for row in cursor:
        table_name = row["name"]
        create_sql = row["sql"]
        # 行数
        try:
            count_cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            row_count = count_cursor.fetchone()[0]
        except Exception:
            row_count = None
        # 列名
        columns = []
        col_cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
        for col in col_cursor:
            columns.append({"name": col["name"], "type": col["type"]})
        # 索引信息
        indexes = []
        idx_cursor = conn.execute(f"PRAGMA index_list([{table_name}])")
        for idx in idx_cursor:
            indexes.append({"name": idx["name"], "unique": bool(idx["unique"])})
        tables.append({
            "name": table_name,
            "columns": columns,
            "row_count": row_count,
            "indexes": indexes,
            "create_sql": create_sql,
        })

    # 语言/文件扩展名列统计
    lang_stats = _extract_language_stats(conn, tables)

    return {
        "tables": tables,
        "language_stats": lang_stats,
    }


def _extract_language_stats(conn: sqlite3.Connection, tables: list[dict]) -> dict:
    """尝试从相关表中按语言/扩展名列统计分布。"""
    stats = {}
    # 查找可能包含语言/扩展名列名的表
    lang_col_candidates = {}
    for t in tables:
        for c in t["columns"]:
            name_lower = c["name"].lower()
            if "language" in name_lower or "lang" in name_lower:
                lang_col_candidates.setdefault(t["name"], []).append(c["name"])
            if "extension" in name_lower or "ext" in name_lower:
                lang_col_candidates.setdefault(t["name"], []).append(c["name"])

    for tbl_name, cols in lang_col_candidates.items():
        for col_name in cols:
            try:
                cursor = conn.execute(
                    f"SELECT [{col_name}], COUNT(*) as cnt FROM [{tbl_name}] GROUP BY [{col_name}] ORDER BY cnt DESC"
                )
                tbl_stats = {}
                for row in cursor:
                    tbl_stats[row[col_name] or "(unknown)"] = row["cnt"]
                if tbl_stats:
                    stats[f"{tbl_name}.{col_name}"] = tbl_stats
            except Exception:
                pass

    return stats


def execute_query(conn: sqlite3.Connection, sql: str, max_rows: int = 200) -> list[dict]:
    """验证并执行只读 SELECT 查询，返回 [{col: val, ...}] 列表，超出 max_rows 时截断并标注。"""
    stripped = sql.strip()
    if not stripped.upper().startswith("SELECT"):
        raise ValueError(f"只允许 SELECT 查询，拒绝: {stripped[:60]}...")

    # 检查是否包含分号后再有其他语句（多语句注入）
    statements = stripped.split(";")
    non_empty = [s.strip() for s in statements if s.strip()]
    if len(non_empty) > 1:
        raise ValueError(f"禁止多语句查询: {stripped[:60]}...")
    single_sql = non_empty[0]
    if not single_sql.upper().startswith("SELECT"):
        raise ValueError(f"只允许 SELECT 查询，拒绝: {stripped[:60]}...")

    cursor = conn.execute(single_sql)
    col_names = [d[0] for d in cursor.description] if cursor.description else []
    rows = []
    total = 0
    for row in cursor:
        if total < max_rows:
            row_dict = {col_names[i]: row[i] for i in range(len(col_names))}
            rows.append(row_dict)
        total += 1

    if total > max_rows:
        rows.append({
            "_truncated": True,
            "_message": f"结果截断，共 {total} 行，显示前 {max_rows} 行",
        })

    return rows


def format_schema_for_llm(schema: dict) -> str:
    """将 schema 摘要格式化为 Markdown 风格的文本，供 LLM 读取。"""
    parts = ["# CodeGraph 知识图谱 Schema 摘要\n"]

    tables = schema.get("tables", [])
    if not tables:
        parts.append("(数据库中没有用户表)\n")
        return "\n".join(parts)

    parts.append(f"共 {len(tables)} 个表:\n")
    for t in tables:
        parts.append(f"## 表: {t['name']}\n")
        parts.append(f"- 行数: {t['row_count'] if t['row_count'] is not None else '未知'}\n")
        col_desc = ", ".join(f"{c['name']} ({c['type']})" for c in t.get("columns", []))
        parts.append(f"- 列: {col_desc}\n")
        if t.get("indexes"):
            idx_desc = ", ".join(i["name"] for i in t["indexes"])
            parts.append(f"- 索引: {idx_desc}\n")
        parts.append("")

    lang_stats = schema.get("language_stats", {})
    if lang_stats:
        parts.append("## 语言/扩展名分布\n")
        for key, dist in lang_stats.items():
            parts.append(f"### {key}\n")
            for name, cnt in dist.items():
                parts.append(f"- {name}: {cnt}\n")
            parts.append("")

    return "\n".join(parts)
