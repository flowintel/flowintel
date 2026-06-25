#!/bin/bash
set -e

# TODO maybe we generalize with Database Dialect instead of a single techno ...

echo "Checking if ${DB_HOST:-postgresql} server is up..."

/home/flowintel/app/bin/wait-for-it.sh "${DB_HOST:-postgresql}":"${DB_PORT:-5432}" --timeout=30 --strict -- echo "${DB_HOST:-postgresql} is up"

sleep 2

echo "${DB_HOST:-postgresql} is reachable."

# We make the following distinction error codes:
# 0 = connected, query ran, no matching admin row.
# 1 = connected, admin row exists.
# 2 = connection/auth/network failure.
# 3 = SQL/schema problem.
# 4 = something else.
DB_EXISTS=$(python3 - << 'EOF'
import os, sys

config_name = os.environ.get("FLOWINTEL_ENV", "development")
print(f"Loading app config {config_name}...", file=sys.stderr)

from conf.config import config as Config
from conf.config import get_db_config

DB = get_db_config()

driver = str(DB["DRIVER"])

if driver == "pymysql":
    import pymysql
else:
    import psycopg2

host = DB["HOST"]
user = DB["USER"]
password = DB["PASSWORD"]
database = DB["NAME"]
port = int(DB["PORT"])
admin_first_name = Config[config_name].INIT_ADMIN_USER["first_name"]

print(f"Checking for database {database} using driver {driver}...", file=sys.stderr)

conn = None
cur = None

if driver == "pymysql":
    import pymysql as dbmod
    OperationalError = dbmod.err.OperationalError
    ProgrammingError = dbmod.err.ProgrammingError
    user_query = 'SELECT id FROM `user` WHERE first_name = %s LIMIT 1'
else:
    import psycopg2 as dbmod
    OperationalError = dbmod.OperationalError
    ProgrammingError = dbmod.ProgrammingError
    user_query = 'SELECT id FROM "user" WHERE first_name = %s LIMIT 1'

try:
    print(f"CHECK: connecting to {host}:{port}/{database}", file=sys.stderr)
    print(f"CHECK: selected module driver was {driver}", file=sys.stderr)
    if driver == "pymysql":
        print(f"CHECK: forced module driver is {pymysql}", file=sys.stderr)
        conn = dbmod.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connect_timeout=5,
        read_timeout=5,
        write_timeout=5,
    )
    else:
        print(f"CHECK: forced driver is {psycopg2}", file=sys.stderr)
        conn = dbmod.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=database,
            connect_timeout=3,
        )
    print(f"CHECK: connection established with driver {driver}", file=sys.stderr)

    cur = conn.cursor()
    cur.execute("SELECT 1")
    print(f"CHECK: SELECT 1 -> {cur.fetchone()}", file=sys.stderr)

    cur.execute(user_query, (admin_first_name,))
    exists = cur.fetchone() is not None
    print(f"CHECK: Is First Admin User first name \"{admin_first_name}\" ?", file=sys.stderr)
    if exists:
        print("First user is already correctly created...", file=sys.stderr)
    print("1" if exists else "0")

except OperationalError as e:
    print(f"CONNECTION_ERROR: {e}", file=sys.stderr)
    print("2")
except ProgrammingError as e:
    print(f"QUERY_ERROR: {e}", file=sys.stderr)
    print("Initialisation necessary.", file=sys.stderr)
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
