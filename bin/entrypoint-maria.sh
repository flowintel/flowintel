#!/bin/bash
set -e

# TODO I have not yet generalized the entrypoint, but I generalized in the rest of your code with DIALECT :)

echo "Checking if MariaDB server is up..."

/home/flowintel/app/bin/wait-for-it.sh mariadb:3306 --timeout=30 --strict -- echo "MariaDB is up"

sleep 2

echo "MariaDB is reachable. Checking for database '$DB_NAME'..."

DB_EXISTS=$(python3 - << 'EOF'
import os, pymysql
try:
    conn = pymsql.connect(
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
