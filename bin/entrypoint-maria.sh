#!/bin/bash
set -e

# TODO I have not yet generalized the entrypoint, but I generalized in the rest of your code with DIALECT :)

echo "Checking if MariaDB server is up..."

/home/flowintel/app/bin/wait-for-it.sh mariadb:3306 --timeout=30 --strict -- echo "MariaDB is up"

sleep 2

echo "MariaDB is reachable."

# We make the following distinction error codes:
# 0 = connected, query ran, no matching admin row.
# 1 = connected, admin row exists.
# 2 = connection/auth/network failure.
# 3 = SQL/schema problem.
# 4 = something else.
DB_EXISTS=$(python3 - << 'EOF'
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

import os, sys, pymysql

from conf.config import config as Config

config_name = os.environ.get("FLASKENV", "development")
print(f"Loading app config {config_name}...", file=sys.stderr)

host = Config[config_name].db_host
user = Config[config_name].db_user
password = Config[config_name].db_password
database = Config[config_name].db_name
port = int(Config[config_name].db_port)

print(f"Checking for database {database}...", file=sys.stderr)

conn = None
cur = None

try:
    print(f"CHECK: connecting to {host}:{port}/{database}", file=sys.stderr)
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connect_timeout=5,
        read_timeout=5,
        write_timeout=5,
    )
    print("CHECK: connection established", file=sys.stderr)

    cur = conn.cursor()
    cur.execute("SELECT 1")
    print(f"CHECK: SELECT 1 -> {cur.fetchone()}", file=sys.stderr)

    cur.execute("SELECT id FROM `user` WHERE first_name = %s LIMIT 1", ("admin",))
    exists = cur.fetchone() is not None
    print("1" if exists else "0")
except pymysql.err.OperationalError as e:
    print(f"CONNECTION_ERROR: {e}", file=sys.stderr)
    print("2")
except pymysql.err.ProgrammingError as e:
    print(f"QUERY_ERROR: {e}", file=sys.stderr)
    print("3")
except Exception as e:
    print(f"OTHER_ERROR: {type(e).__name__}: {e}", file=sys.stderr)
    print("4")
finally:
    try:
        if cur is not None:
            cur.close()
    except Exception:
        pass
    try:
        if conn is not None:
            conn.close()
    except Exception:
        pass
EOF
)

if [ "$DB_EXISTS" = "1" ]; then
    echo "Database already exists."
else
    echo "Database missing — running initialization..."
    bash -i /home/flowintel/app/launch.sh -id
fi

exec bash -i /home/flowintel/app/launch.sh -ld
