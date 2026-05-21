#!/bin/sh
# 等待 PostgreSQL 就绪（云平台 DB 启动可能延迟）
# 从 DATABASE_URL 解析 host:port，最长等 60 秒

echo "=== PAYGO Platform Entrypoint ==="

# Python 解析 URL
python3 -c "
import os, time, re, socket

url = os.getenv('DATABASE_URL', '')
if not url:
    url = os.getenv('DATABASE_PRIVATE_URL', '')
if not url:
    print('No DATABASE_URL found, starting anyway...')
    exit(0)

# 提取 host:port
host, port = 'localhost', 5432
m = re.search(r'@([^:/]+):?(\d+)?/', url)
if m:
    host = m.group(1)
    port = int(m.group(2) or 5432)

print(f'Waiting for PostgreSQL at {host}:{port}...')
for i in range(20):
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((host, port))
        s.close()
        print(f'PostgreSQL ready after {i+1} attempt(s)!')
        break
    except Exception as e:
        print(f'Attempt {i+1}/20: not ready ({e})')
        time.sleep(3)
else:
    print('WARNING: PostgreSQL not ready after 60s, starting anyway...')
"

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
