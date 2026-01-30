# Quick start

This was tested only on Ubuntu.

### Configuration

First of all you need to change the main configuration:

```
/conf/config.py
```

If you plan to use module, have a look on the configuration file for module:

```
/conf/config_module.py
```

### Installation

After configuration you can run the installation script:

```bash
./install.sh
```

### Dockerfile

You have also the possibility to use the docker file:

```bash
docker build .
docker run -t -i -p 7006:7006 ID_IMAGE
```

### Docker image

There's an image already ready to use 

```bash
docker pull ghcr.io/flowintel/flowintel:latest
docker run -t -i -p 7006:7006 ID_IMAGE
```



### Account

- email: `admin@admin.admin`

- password: `admin`