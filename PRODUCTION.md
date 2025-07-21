## Production Deployment – Flowintel with Docker

To deploy **Flowintel** in production mode using Docker, follow the steps below:

---

### 1. Configure the application

Edit [`conf/config.py`](./conf/config.py) and set `ProductionConfig` as the default configuration:

```python
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}
```

Update the database URI if needed.

---

### 2. Disable database initialization during image build

Edit the [`Dockerfile`](./Dockerfile) and **remove or comment out** the following line:

```Dockerfile
RUN script -q -c "./launch.sh --init_db" /dev/null
```

❗ **Important:** The database must **not** be initialized during image build. Initialization must be performed **after** the database service is running.

---

### 3. Set the environment to production

Run the following command to replace all `FLASKENV="development"` with `FLASKENV="production"` in `launch.sh`:

```bash
sed -i 's/FLASKENV="development"/FLASKENV="production"/g' launch.sh
```

---

### 4. Add PostgreSQL dependency

Ensure your database adapter package is included in your `requirements.txt`, for PostgreSQL:

```
psycopg2-binary
```

---

### 5. Build the Docker image

Build the Docker image using:

```bash
docker build -t flowintel:{tag} .
```

Replace `{tag}` with your desired version tag (e.g. `latest`, `v1.6.1`, etc.).

---

### 6. Set up `docker-compose.yml`

Here is a template `docker-compose.yml` file with PostgreSQL:

```yml
services:
  postgresql:
    container_name: postgres
    image: postgres:17
    ports:
      - '${POSTGRES_PORT}:5432'
    volumes:
      - db:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_DB=${POSTGRES_DB}
    networks:
      - net
    restart: unless-stopped

  app:
    image: flowintel:{tag}
    container_name: flowintel
    ports:
      - '${APP_PORT}:7006'
    networks:
      - net
    depends_on:
      - postgresql
    environment:
      - DB_HOST=postgresql
      - DB_PORT=${POSTGRES_PORT}
      - DB_USER=${POSTGRES_USER}
      - DB_PASSWORD=${POSTGRES_PASSWORD}
      - DB_NAME=${POSTGRES_DB}
    restart: unless-stopped

volumes:
  db:

networks:
  net:
    driver: bridge
```
---
### 7. Configure environment variables
Copy the environment template and edit it:
```bash
cp template.env .env
```

Update the variables as needed (`POSTGRES_USER`, `POSTGRES_PASSWORD`, etc.).

---

### 8. Start the containers

Launch all services using:

```bash
docker compose up -d
```

---

### 9. Initialize the database

Once the containers are running, initialize the database with:

```bash
docker exec -it flowintel bash -i ./launch.sh --init_db
```

---