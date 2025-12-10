#!/bin/bash
set -e

echo "Checking if PostgreSQL server is up..."

/home/flowintel/app/bin/wait-for-it.sh postgresql:5432 --timeout=30 --strict -- echo "Postgres is up"

sleep 2

echo "Postgres is reachable. Checking for database '$DB_NAME'..."

DB_EXISTS=$(python3 - << 'EOF'
import os, psycopg2
try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
        connect_timeout=3
    )
    cur = conn.cursor()
    cur.execute('SELECT id FROM "user" WHERE first_name = %s;', ("admin",))
    exists = cur.fetchone() is not None
    print("1" if exists else "0")
except:
    print("0")
EOF
)

if [ "$DB_EXISTS" = "1" ]; then
    echo "Database already exists."
else
    echo "Database missing — running initialization..."
    bash -i /home/flowintel/app/launch.sh -id
fi

exec bash -i /home/flowintel/app/launch.sh -ld
