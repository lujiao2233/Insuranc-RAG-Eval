import pymysql

conn = pymysql.connect(host='10.1.219.22', port=3306, user='root', password='dwcsrag123', database='RAGEVAL', charset='utf8mb4')
cursor = conn.cursor()

tables = [
    ('users', '''
CREATE TABLE IF NOT EXISTS users (
  id char(36) NOT NULL,
  username varchar(50) NOT NULL,
  email varchar(100) NOT NULL,
  password_hash varchar(255) NOT NULL,
  role varchar(20) DEFAULT NULL,
  full_name varchar(100) DEFAULT NULL,
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  last_login datetime DEFAULT NULL,
  is_active tinyint(1) DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY username (username),
  UNIQUE KEY email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
'''),
    ('documents', '''
CREATE TABLE IF NOT EXISTS documents (
  id char(36) NOT NULL,
  user_id char(36) DEFAULT NULL,
  filename varchar(255) NOT NULL,
  file_path varchar(500) NOT NULL,
  file_type varchar(20) NOT NULL,
  file_size bigint NOT NULL,
  page_count int DEFAULT NULL,
  upload_time datetime DEFAULT CURRENT_TIMESTAMP,
  status varchar(20) DEFAULT 'active',
  is_analyzed tinyint(1) DEFAULT 0,
  analyzed_at datetime DEFAULT NULL,
  doc_metadata_col text DEFAULT NULL,
  outline text DEFAULT NULL,
  category varchar(100) DEFAULT '未分类',
  product_entities text DEFAULT NULL,
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
'''),
    ('document_chunks', '''
CREATE TABLE IF NOT EXISTS document_chunks (
  id char(36) NOT NULL,
  document_id char(36) NOT NULL,
  content text NOT NULL,
  md5 varchar(32) NOT NULL,
  sequence_number int NOT NULL,
  start_char int DEFAULT NULL,
  end_char int DEFAULT NULL,
  overlap_ratio text DEFAULT NULL,
  entities text DEFAULT NULL,
  dense_vector text DEFAULT NULL,
  chunk_metadata text DEFAULT NULL,
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_document_id (document_id),
  KEY idx_md5 (md5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
'''),
    ('testsets', '''
CREATE TABLE IF NOT EXISTS testsets (
  id char(36) NOT NULL,
  document_id char(36) NOT NULL,
  user_id char(36) DEFAULT NULL,
  name varchar(255) NOT NULL,
  description text DEFAULT NULL,
  question_count int DEFAULT 0,
  question_types text DEFAULT NULL,
  generation_method varchar(50) DEFAULT 'qwen_model',
  create_time datetime DEFAULT CURRENT_TIMESTAMP,
  file_path varchar(500) DEFAULT NULL,
  testset_metadata text DEFAULT NULL,
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_document_id (document_id),
  KEY idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
'''),
    ('questions', '''
CREATE TABLE IF NOT EXISTS questions (
  id char(36) NOT NULL,
  testset_id char(36) NOT NULL,
  question text NOT NULL,
  question_type varchar(50) NOT NULL,
  category_major varchar(100) DEFAULT NULL,
  category_minor varchar(100) DEFAULT NULL,
  expected_answer text DEFAULT NULL,
  answer text DEFAULT NULL,
  context text DEFAULT NULL,
  question_metadata text DEFAULT NULL,
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_testset_id (testset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
'''),
    ('evaluations', '''
CREATE TABLE IF NOT EXISTS evaluations (
  id char(36) NOT NULL,
  user_id char(36) DEFAULT NULL,
  testset_id char(36) DEFAULT NULL,
  evaluation_method varchar(50) DEFAULT 'ragas_official',
  total_questions int NOT NULL,
  evaluated_questions int NOT NULL,
  evaluation_time int DEFAULT NULL,
  timestamp datetime DEFAULT CURRENT_TIMESTAMP,
  evaluation_metrics text DEFAULT NULL,
  overall_metrics text DEFAULT NULL,
  eval_config text DEFAULT NULL,
  status varchar(20) DEFAULT 'completed',
  error_message text DEFAULT NULL,
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_testset_id (testset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
'''),
    ('evaluation_results', '''
CREATE TABLE IF NOT EXISTS evaluation_results (
  id char(36) NOT NULL,
  evaluation_id char(36) NOT NULL,
  question_id char(36) DEFAULT NULL,
  question_text text NOT NULL,
  expected_answer text DEFAULT NULL,
  generated_answer text DEFAULT NULL,
  context text DEFAULT NULL,
  metrics text DEFAULT NULL,
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_evaluation_id (evaluation_id),
  KEY idx_question_id (question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
'''),
    ('configurations', '''
CREATE TABLE IF NOT EXISTS configurations (
  id char(36) NOT NULL,
  user_id char(36) NOT NULL,
  config_key varchar(100) NOT NULL,
  config_value text DEFAULT NULL,
  config_description text DEFAULT NULL,
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
'''),
]

for table_name, sql in tables:
    try:
        cursor.execute(sql)
        print(f'{table_name} 表创建成功')
    except Exception as e:
        print(f'{table_name} 表创建失败: {e}')

conn.commit()

cursor.execute('SHOW TABLES')
tables_list = cursor.fetchall()
print(f'\n已创建的表: {[t[0] for t in tables_list]}')

conn.close()
