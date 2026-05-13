"""数据库迁移脚本目录

注意：当前项目使用 SQLAlchemy 的 Base.metadata.create_all() 进行一键建表。
所有表定义在 models/database.py 中。

部署时运行：
    python scripts/init_db.py

如需修改表结构，请直接修改 models/database.py 中的模型定义。
"""
