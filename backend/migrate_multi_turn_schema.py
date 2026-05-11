"""多轮会话能力数据库迁移脚本。

保留现有数据，仅补齐多轮能力需要的字段、表和索引。
"""
import sys
from pathlib import Path

from sqlalchemy import inspect, text

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.database import engine
from models.database import Base


def _get_columns(inspector, table_name: str) -> set[str]:
    try:
        return {column["name"] for column in inspector.get_columns(table_name)}
    except Exception:
        return set()


def _get_indexes(inspector, table_name: str) -> set[str]:
    try:
        return {index["name"] for index in inspector.get_indexes(table_name)}
    except Exception:
        return set()


def _add_column_if_missing(conn, table_name: str, column_name: str, ddl_by_dialect: dict[str, str]) -> bool:
    inspector = inspect(conn)
    existing_columns = _get_columns(inspector, table_name)
    if column_name in existing_columns:
        print(f"✅ {table_name}.{column_name} 已存在，跳过")
        return False

    dialect_name = conn.dialect.name
    ddl = ddl_by_dialect.get(dialect_name) or ddl_by_dialect["default"]
    print(f"🔧 正在添加字段 {table_name}.{column_name} ...")
    conn.execute(text(ddl))
    return True


def _create_index_if_missing(conn, table_name: str, index_name: str, create_sql: str) -> bool:
    inspector = inspect(conn)
    existing_indexes = _get_indexes(inspector, table_name)
    if index_name in existing_indexes:
        print(f"✅ 索引 {index_name} 已存在，跳过")
        return False

    print(f"🔧 正在创建索引 {index_name} ...")
    conn.execute(text(create_sql))
    return True


def migrate() -> bool:
    print("🚀 开始数据库迁移：补齐多轮会话 schema ...")
    print(f"📦 当前数据库方言: {engine.dialect.name}")

    try:
        with engine.connect() as conn:
            changed = False

            print("\n1. 检查并补充旧表字段 ...")
            changed = _add_column_if_missing(
                conn,
                "testsets",
                "conversation_mode",
                {
                    "mysql": """
                        ALTER TABLE testsets
                        ADD COLUMN conversation_mode VARCHAR(20) NOT NULL DEFAULT 'single_turn'
                    """,
                    "sqlite": """
                        ALTER TABLE testsets
                        ADD COLUMN conversation_mode VARCHAR(20) NOT NULL DEFAULT 'single_turn'
                    """,
                    "default": """
                        ALTER TABLE testsets
                        ADD COLUMN conversation_mode VARCHAR(20) NOT NULL DEFAULT 'single_turn'
                    """,
                },
            ) or changed

            changed = _add_column_if_missing(
                conn,
                "evaluations",
                "evaluation_mode",
                {
                    "mysql": """
                        ALTER TABLE evaluations
                        ADD COLUMN evaluation_mode VARCHAR(30) NOT NULL DEFAULT 'single_turn'
                    """,
                    "sqlite": """
                        ALTER TABLE evaluations
                        ADD COLUMN evaluation_mode VARCHAR(30) NOT NULL DEFAULT 'single_turn'
                    """,
                    "default": """
                        ALTER TABLE evaluations
                        ADD COLUMN evaluation_mode VARCHAR(30) NOT NULL DEFAULT 'single_turn'
                    """,
                },
            ) or changed

            changed = _add_column_if_missing(
                conn,
                "background_tasks",
                "context_info",
                {
                    "mysql": """
                        ALTER TABLE background_tasks
                        ADD COLUMN context_info JSON NULL
                    """,
                    "sqlite": """
                        ALTER TABLE background_tasks
                        ADD COLUMN context_info JSON
                    """,
                    "default": """
                        ALTER TABLE background_tasks
                        ADD COLUMN context_info JSON
                    """,
                },
            ) or changed

            changed = _add_column_if_missing(
                conn,
                "evaluation_results",
                "case_id",
                {
                    "mysql": """
                        ALTER TABLE evaluation_results
                        ADD COLUMN case_id CHAR(36) NULL
                    """,
                    "sqlite": """
                        ALTER TABLE evaluation_results
                        ADD COLUMN case_id CHAR(36)
                    """,
                    "default": """
                        ALTER TABLE evaluation_results
                        ADD COLUMN case_id CHAR(36)
                    """,
                },
            ) or changed

            changed = _add_column_if_missing(
                conn,
                "evaluation_results",
                "turn_id",
                {
                    "mysql": """
                        ALTER TABLE evaluation_results
                        ADD COLUMN turn_id CHAR(36) NULL
                    """,
                    "sqlite": """
                        ALTER TABLE evaluation_results
                        ADD COLUMN turn_id CHAR(36)
                    """,
                    "default": """
                        ALTER TABLE evaluation_results
                        ADD COLUMN turn_id CHAR(36)
                    """,
                },
            ) or changed

            if changed:
                conn.commit()

        print("\n2. 创建缺失的多轮会话表 ...")
        # create_all 只会创建缺失表，不会删除旧数据
        Base.metadata.create_all(bind=engine)

        with engine.connect() as conn:
            print("\n3. 检查并补充索引 ...")
            index_sql = {
                "ix_testsets_conversation_mode": "CREATE INDEX ix_testsets_conversation_mode ON testsets (conversation_mode)",
                "ix_evaluations_evaluation_mode": "CREATE INDEX ix_evaluations_evaluation_mode ON evaluations (evaluation_mode)",
                "ix_evaluation_results_case_id": "CREATE INDEX ix_evaluation_results_case_id ON evaluation_results (case_id)",
                "ix_evaluation_results_turn_id": "CREATE INDEX ix_evaluation_results_turn_id ON evaluation_results (turn_id)",
            }
            changed = False
            changed = _create_index_if_missing(
                conn,
                "testsets",
                "ix_testsets_conversation_mode",
                index_sql["ix_testsets_conversation_mode"],
            ) or changed
            changed = _create_index_if_missing(
                conn,
                "evaluations",
                "ix_evaluations_evaluation_mode",
                index_sql["ix_evaluations_evaluation_mode"],
            ) or changed
            changed = _create_index_if_missing(
                conn,
                "evaluation_results",
                "ix_evaluation_results_case_id",
                index_sql["ix_evaluation_results_case_id"],
            ) or changed
            changed = _create_index_if_missing(
                conn,
                "evaluation_results",
                "ix_evaluation_results_turn_id",
                index_sql["ix_evaluation_results_turn_id"],
            ) or changed

            if changed:
                conn.commit()

            inspector = inspect(conn)
            tables = set(inspector.get_table_names())
            required_tables = {
                "conversation_test_cases",
                "conversation_turns",
                "conversation_executions",
                "conversation_turn_results",
            }
            missing_tables = sorted(required_tables - tables)
            if missing_tables:
                print(f"❌ 迁移后仍缺少表: {missing_tables}")
                return False

            testsets_columns = _get_columns(inspector, "testsets")
            evaluations_columns = _get_columns(inspector, "evaluations")
            background_tasks_columns = _get_columns(inspector, "background_tasks")
            evaluation_results_columns = _get_columns(inspector, "evaluation_results")
            if "conversation_mode" not in testsets_columns:
                print("❌ testsets.conversation_mode 缺失")
                return False
            if "evaluation_mode" not in evaluations_columns:
                print("❌ evaluations.evaluation_mode 缺失")
                return False
            if "context_info" not in background_tasks_columns:
                print("❌ background_tasks.context_info 缺失")
                return False
            if "case_id" not in evaluation_results_columns:
                print("❌ evaluation_results.case_id 缺失")
                return False
            if "turn_id" not in evaluation_results_columns:
                print("❌ evaluation_results.turn_id 缺失")
                return False

        print("\n🎉 多轮会话 schema 迁移完成！")
        print("\n已确认存在：")
        print("  - testsets.conversation_mode")
        print("  - evaluations.evaluation_mode")
        print("  - background_tasks.context_info")
        print("  - evaluation_results.case_id")
        print("  - evaluation_results.turn_id")
        print("  - conversation_test_cases")
        print("  - conversation_turns")
        print("  - conversation_executions")
        print("  - conversation_turn_results")
        return True
    except Exception as exc:
        print(f"❌ 多轮会话 schema 迁移失败: {exc}")
        return False


if __name__ == "__main__":
    ok = migrate()
    raise SystemExit(0 if ok else 1)
