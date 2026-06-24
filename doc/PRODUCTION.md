## Production Deployment – Flowintel with Docker

To deploy **Flowintel** in production mode using Docker, follow the steps below:

---

### 1. Configure the application
TODO harmonize with .env

Edit [`conf/config.py`](./conf/config.py) and set `ProductionConfig` as the default configuration:

```python
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
```

Update the database URI if needed.

---

### 2. Disable database initialization during image build
TODO Adapt with Docker files production grade, then simply mention to use these production files ?

Edit the [`Dockerfile`](./Dockerfile) and **remove or comment out** the following line:

```Dockerfile
RUN script -q -c "./launch.sh --init_db" /dev/null
```

❗ **Important:** The database must **not** be initialized during image build. Initialization must be performed **after** the database service is running.

---

### 3. Set the environment to production

Run the following command to replace all `FLOWINTEL_ENV="development"` with `FLOWINTEL_ENV="production"` in `launch.sh`:

```bash
sed -i 's/FLOWINTEL_ENV="development"/FLOWINTEL_ENV="production"/g' launch.sh
```

---

### 4. Add PostgreSQL dependency
TODO the requirements are supposed to be maintained in the repo, this looks like a tweak that might have been necessary
in early version ? Seeing it here is a smell of strong coupling of DB backend with code/conf/doc, removing will decouple
yet more from the DB backend if and only if the code path is sane.

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

### 6. Set up `docker/docker-compose*.yml`
Adapt the .yml files to your exact use case, especially regarding the environment variables management.
The different Docker composition files are described in the README.md and can be found under the ```docker/``` folder.

---
### 7. Configure environment variables
TODO Should be made explicit that config (.env, conf.py) are mounted at docker composition level and not embedded into the image.

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
TODO Transform me into a memo ?

Once the containers are running, initialize the database with:

```bash
docker exec -it flowintel bash -i ./launch.sh --init_db
```

---