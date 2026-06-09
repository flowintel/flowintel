#!/bin/bash
set -e

# TODO maybe we generalize with Database Dialect instead of a single techno ...

echo "Checking if PostgreSQL server is up..."

/home/flowintel/app/bin/wait-for-it.sh postgresql:5432 --timeout=30 --strict -- echo "Postgres is up"

sleep 2

echo "Postgres is reachable. Checking for database '$DB_NAME'..."

# We make the following distinction error codes:
# 0 = connected, query ran, no matching admin row.
# 1 = connected, admin row exists.
# 2 = connection/auth/network failure.
# 3 = SQL/schema problem.
# 4 = something else.
DB_EXISTS=$(python3 - << 'EOF'
import os, sys, psycopg2
host = os.getenv("DB_HOST")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")
port = int(os.getenv("DB_PORT"))

try:
    print(f"CHECK: connecting to {host}:{port}/{database}", file=sys.stderr)
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=database,
        connect_timeout=3,
    )
    print("CHECK: connection established", file=sys.stderr)

    cur = conn.cursor()
    cur.execute("SELECT 1")
    print(f"CHECK: SELECT 1 -> {cur.fetchone()}", file=sys.stderr)

    cur.execute("SELECT id FROM `user` WHERE first_name = %s LIMIT 1", ("admin",))
    exists = cur.fetchone() is not None
    print("1" if exists else "0")
except psycopg2.err.OperationalError as e:
    print(f"CONNECTION_ERROR: {e}", file=sys.stderr)
    print("2")
except psycopg2.err.ProgrammingError as e:
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
