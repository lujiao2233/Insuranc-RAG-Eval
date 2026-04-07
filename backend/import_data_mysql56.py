import pymysql
import re

conn = pymysql.connect(host='10.1.219.22', port=3306, user='root', password='dwcsrag123', database='RAGEVAL', charset='utf8mb4')
cursor = conn.cursor()

print('开始导入数据...')

with open('rag_eval_import_mysql56.sql', 'r', encoding='utf-8') as f:
    content = f.read()

# 删除 CREATE DATABASE 和 USE 语句
content = re.sub(r'CREATE DATABASE[^;]*;', '', content)
content = re.sub(r'USE\s+`?RAGEVAL`?\s*;', '', content)

# 删除 CREATE TABLE 语句（表已创建）
content = re.sub(r'CREATE TABLE[^;]*\);', '', content, flags=re.DOTALL)
content = re.sub(r'DROP TABLE[^;]*;', '', content)

# 使用正则表达式提取每个 INSERT 语句
all_inserts = re.finditer(r'(INSERT INTO `?\w+`?\s+VALUES\s*[^;]+);', content, re.DOTALL)

success = 0
errors = 0

for match in all_inserts:
    stmt = match.group(1) + ';'
    try:
        cursor.execute(stmt)
        success += 1
        if success % 10 == 0:
            conn.commit()
            print(f'已导入 {success} 条语句...')
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f'错误: {str(e)[:100]}')

conn.commit()

# 验证数据
cursor.execute('SELECT COUNT(*) FROM users')
users_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM documents')
docs_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM testsets')
testsets_count = cursor.fetchone()[0]

print(f'\n导入完成! 成功: {success}, 错误: {errors}')
print(f'验证数据: users={users_count}, documents={docs_count}, testsets={testsets_count}')

conn.close()
