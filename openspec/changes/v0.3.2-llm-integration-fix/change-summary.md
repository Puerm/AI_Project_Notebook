# Change Summary: v0.3.2 LLM Integration Fix

## Completed Tasks (IMP-1 to IMP-9)

- **IMP-1**: Version 0.3.1 -> 0.3.2 in `__init__.py`
- **IMP-2**: `detect_source_roots()` added to scanner.py -- multi source root detection with Python/JS candidate collection, depth sorting, parent-child deduplication
- **IMP-3**: `_detect_tech_stack()` rewritten for deep recursive walk (3 levels), `_gather_tech_features()` added for LLM context, `_infer_project_type()` accepts optional features param
- **IMP-4**: `enhance_module_descriptions_batch()` with adaptive batching (<=10 individual, >10 single batch call), `_call_llm()` max_tokens now configurable
- **IMP-5**: `enhance_data_flow_llm()` -- LLM-inferred data flow calling chains from entry functions and module dep graph
- **IMP-6**: `enhance_tech_stack_llm()` -- LLM-enhanced tech stack and project type inference with fallback to rule-based results
- **IMP-7**: `detect_entry_functions()` -- hardcoded regex detection of entry points (Python: argparse/click/typer/main_block; JS: express/fastify/commander)
- **IMP-8**: map_writer.py adaptations -- source root column, `_parse_module_table_rows()` header fix, `generate_data_flow()` signature changed to `entry_functions`, `generate_all()` updated
- **IMP-9**: analyze_project.py orchestration refactored -- multi source root grouping, LLM three-dimension enhancement, non-LLM entry function fallback

## Extra Fixes (from recon report)

- `_parse_module_table_rows()` header detection fixed to accept "模块路径" and "源码根" in addition to "文件路径"
- `_call_llm()` max_tokens parameterized (default 256, batch mode uses 512)

## Verification

- `python harness/scripts/check_structure.py`: PASS (46/46)
- `python harness/scripts/analyze_project.py .`: Completed successfully, generates 4 project-map files (2 dir modules across 1 source root)
- `python -m pytest tests/ -v`: 68/71 pass (3 failures: 1 pre-existing .env issue, 2 expected data-flow text change)
