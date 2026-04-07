import pymysql

# 本地数据库连接
local_conn = pymysql.connect(host='localhost', port=3306, user='root', password='password', database='rag_evaluation', charset='utf8mb4')
local_cursor = local_conn.cursor()

# 内网数据库连接
remote_conn = pymysql.connect(host='10.1.219.22', port=3306, user='root', password='dwcsrag123', database='RAGEVAL', charset='utf8mb4')
remote_cursor = remote_conn.cursor()

tables = ['users', 'documents', 'document_chunks', 'testsets', 'questions', 'evaluations', 'evaluation_results', 'configurations']

for table in tables:
    print(f'\n迁移 {table} 表...')
    
    # 获取本地数据
    local_cursor.execute(f'SELECT * FROM {table}')
    columns = [desc[0] for desc in local_cursor.description]
    rows = local_cursor.fetchall()
    
    if not rows:
        print(f'  {table} 表无数据')
        continue
    
    print(f'  找到 {len(rows)} 条记录')
    
    # 清空目标表
    try:
        remote_cursor.execute(f'TRUNCATE TABLE {table}')
    except:
        remote_cursor.execute(f'DELETE FROM {table}')
    
    # 插入数据
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)
    insert_sql = f'INSERT INTO {table} ({columns_str}) VALUES ({placeholders})'
    
    success = 0
    errors = 0
    
    for row in rows:
        try:
            # 转换数据类型
            converted_row = []
            for val in row:
                if isinstance(val, bytes):
                    converted_row.append(val.decode('utf-8'))
                else:
                    converted_row.append(val)
            
            remote_cursor.execute(insert_sql, converted_row)
            success += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f'  错误: {str(e)[:100]}')
    
    remote_conn.commit()
    print(f'  成功: {success}, 错误: {errors}')

# 验证数据
print('\n验证数据:')
for table in tables:
    remote_cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = remote_cursor.fetchone()[0]
    print(f'  {table}: {count} 条记录')

local_conn.close()
remote_conn.close()

print('\n迁移完成!')
