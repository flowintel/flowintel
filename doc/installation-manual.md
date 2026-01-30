
# Flowintel installation manual

## What is Flowintel?

**Flowintel** is an open-source platform for security analysts to organise cases and tasks. It provides workflow tools to track investigations, document findings, and collaborate within teams.

### Technical components

Flowintel is built with:

- **Flask**: Python web framework
- **PostgreSQL**: Production database (SQLite supported for development)
- **Valkey**: Session storage
- **MISP modules**: Analysis and enrichment engine

Flowintel follows a common pattern for Python web applications. The Flask application runs behind an application server and is exposed to users through a web server such as NGINX or Apache, which acts as a reverse proxy.

### Supported operating systems

Flowintel runs on Ubuntu Linux 22.04 LTS and 24.04 LTS. Other Debian-based distributions may work but are not officially tested.

## Pre-installation

### System requirements

#### Software requirements

- **Operating system**
    - Ubuntu 22.04 LTS or 24.04 LTS
    - System must be up-to-date (`apt update && apt upgrade`)
- **Installation access**
    -  During installation, you need:
        - Console or SSH access with sudo privileges
        - Ability to reconfigure system services
        - Permission to modify firewall rules
- **Network requirements**
    - One static IPv4 address; you can disable IPv6 if it is not used in your environment
    - Fully qualified domain name (FQDN) for accessing the web interface
    - **Internet connectivity**
        - The following domains must be accessible during installation:
            - `*.ubuntu.com` (package repositories)
            - `*.github.com`, `*.github.io`, `*.githubusercontent.com` (source code)
            - `*.pypi.org`, `*.python.org`, `*.pythonhosted.org` (Python packages)
        - After installation, internet access is only needed for updates.
        - *Note*: if you plan on using the MISP modules additional internet access is needed. Details are covered in the MISP modules section.    
- **DNS resolution**
    - The system must be able to resolve hostnames. Point to corporate DNS servers or use public resolvers.
- **Time synchronisation**
    - Configure NTP to keep system time accurate. This is critical for audit logging and session management.
- **Web browser**
    - Once the installation is completed, you can access Flowintel from any modern web browser (Chrome, Firefox, Safari, Edge).

#### Hardware requirements

Flowintel runs on both physical and virtual machines. While it doesn't demand heavy resources, plan for storage growth as case attachments and database entries accumulate over time.

- **Recommended specifications**
    - CPU: Intel Core i5 or equivalent (4 cores)
    - Memory: 8 GB RAM (minimum 4 GB)
    - Storage: 80 GB or more
- **Storage considerations**
    - Install Flowintel on a separate volume or partition. This makes:
        - Backups simpler and faster
        - System recovery easier
        - Disk expansion straightforward without touching the OS
    - Estimate storage needs based on:
        - Number of expected cases per year
        - Average attachment size per case
        - Retention period for closed cases

### Required installation skills

Flowintel installation is console-based and involves configuring Linux services. The person performing the installation should have:

- **Linux administration** knowledge (medium to advanced)
    - Package management with apt
    - Service management with systemd
    - File permissions and ownership
    - Log file navigation and troubleshooting
- Experience with **networking** (medium)
    - Static IP configuration
    - Firewall rules (ufw or iptables)
    - SSL certificate installation
    - Basic DNS and routing concepts
- Knowledge of **web applications** (medium)
    - Python virtual environments
    - Web server configuration (NGINX or Apache)
    - Database setup and user management
    - Environment variable configuration
- **Tools and interfaces**
    - Comfortable working in the terminal or via SSH
    - Basic text editor skills (nano, vim, or similar)

### Pre-installation checklist

Before starting the installation, verify you have:

- [ ] SSH or console access to Ubuntu 22.04/24.04 system
- [ ] Sudo privileges on the system
- [ ] Internet access to required domains (GitHub, PyPI, Ubuntu repos)
- [ ] Static IP address configured
- [ ] FQDN defined for the web interface
- [ ] The hardware meets the minimum requirements (8 GB RAM, 80 GB storage)
- [ ] NTP configured and time synchronised
- [ ] DNS resolution working
- [ ] SSL certificate available (or plan to use self-signed)
- [ ] Firewall rules configured

### Installation source

Flowintel is installed directly from its Git repository. There is no installer package or pre-built binary. The installation process clones the repository and sets up dependencies using standard Python and Linux tools.

# Installation

The installation follows these steps:

- Prepare the Linux system and create installation location
- Download Flowintel
- Setup the reverse proxy (NGINX)
- Setup the database (PostgreSQL)
- Configure and install the Flowintel application

## System preparation

**Virtual machine users**: If you're installing on a VM, create a snapshot before proceeding. This allows you to revert to a known good state if something goes wrong during installation.

Ensure your Linux system is fully updated:

```bash
# Update Ubuntu packages
sudo apt update
sudo apt upgrade -y
```

Install Git and basic dependencies:

```bash
# Git and basic dependencies
sudo apt install -y git curl wget build-essential
```

### Configure firewall

Set up UFW (Uncomplicated Firewall) to allow only necessary inbound traffic:

```bash
# Install UFW if not already present
sudo apt install -y ufw

# Allow SSH (adjust port if you use a non-standard SSH port)
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow http
sudo ufw allow https

# Enable firewall
sudo ufw enable

# Verify firewall status
sudo ufw status
```

You should see output showing SSH (22/tcp), HTTP (80/tcp), and HTTPS (443/tcp) are allowed.

**Note**: If you're connected via SSH, ensure SSH is allowed before enabling the firewall to avoid locking yourself out.

## Installation location

For better organisation and easier backups, create a dedicated partition or mount point for Flowintel.

**Option 1: Simple directory** (quick setup for testing)

```bash
# Create installation directory
sudo mkdir -p /opt/flowintel

# Set ownership (replace 'yourusername' with your actual username)
sudo chown -R yourusername:yourusername /opt/flowintel
```

**Option 2: LVM partition** (recommended for production)

If you have a dedicated disk (for example `/dev/sdb`), use LVM for better flexibility with backups, snapshots, and future expansion:

```bash
# Install LVM tools if not present
sudo apt install -y lvm2

# Create physical volume on the disk
sudo pvcreate /dev/sdb

# Create volume group named 'flowintel-vg'
sudo vgcreate flowintel-vg /dev/sdb

# Create logical volume (use 100% of available space, or specify size like -L 50G)
sudo lvcreate -n flowintel-lv -l 100%FREE flowintel-vg

# Format with ext4
sudo mkfs.ext4 /dev/flowintel-vg/flowintel-lv

# Create mount point
sudo mkdir -p /opt/flowintel

# Mount the filesystem
sudo mount /dev/flowintel-vg/flowintel-lv /opt/flowintel

# Add to /etc/fstab for automatic mounting on boot
echo '/dev/flowintel-vg/flowintel-lv /opt/flowintel ext4 defaults 0 2' | sudo tee -a /etc/fstab

# Set ownership (replace 'yourusername' with your actual username)
sudo chown -R yourusername:yourusername /opt/flowintel
```

Verify the mount:

```bash
df -h /opt/flowintel
```

## Download Flowintel

### Clone the repository

Download Flowintel from GitHub:

```bash
# Download Flowintel into /opt/flowintel
cd /opt/flowintel
git clone https://github.com/flowintel/flowintel.git
cd flowintel
```

The repository is now cloned to `/opt/flowintel/flowintel`. All subsequent commands assume you're working from this directory.

### Secure file permissions

Set appropriate permissions on the Flowintel application directory to prevent unauthorised access:

```bash
# Set secure permissions (owner read/write/execute, group read/execute, no access for others)
sudo chmod 750 /opt/flowintel/flowintel
```

You should see:
```
drwxr-x--- 10 yourusername yourusername 4096 Jan 30 08:00 /opt/flowintel/flowintel
```

This restricts access to the owner and group members, preventing other users on the system from reading sensitive configuration files or data.

**Important**: Do not apply chmod 750 to `/opt/flowintel` if you relocate the PostgreSQL data directory to `/opt/flowintel/database` (covered in the next section). This would prevent PostgreSQL from accessing the database. Only apply the permission restrictions to `/opt/flowintel/flowintel`.

## Web server: reverse proxy with NGINX

While you can access Flask directly during development, running Flowintel behind a reverse proxy is strongly recommended for production.

**Note**: If you're just testing Flowintel, you can skip this section and access Flask directly at `http://localhost:7006`. For production deployments, continue with the NGINX setup below.

### Setup NGINX

```bash
# Install and enable nginx
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

Replace **flowintel.yourdomain.com** with your actual hostname throughout this guide. If you're setting this up for internal use without public DNS, add an entry to your DNS server or use local hosts files on client machines.

### NGINX configuration file

Flowintel includes an NGINX configuration template. Copy it to the NGINX sites-available directory:

```bash
sudo cp /opt/flowintel/flowintel/doc/flowintel.nginx /etc/nginx/sites-available/flowintel
```

Replace `flowintel.yourdomain.com` with your actual domain name:

```bash
sudo sed -i 's/flowintel.yourdomain.com/your-actual-domain.com/g' /etc/nginx/sites-available/flowintel
```

### SSL certificates

You need to configure SSL certificates for HTTPS access before enabling the site. Choose one of the following options based on your requirements:

#### Option 1: Self-signed certificate (testing/internal use)

For testing or internal deployments, generate a self-signed certificate:

```bash
# Create directory for certificates
sudo mkdir -p /etc/nginx/ssl

# Generate self-signed certificate (valid for 365 days)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/flowintel.key \
  -out /etc/nginx/ssl/flowintel.crt \
  -subj "/C=BE/ST=Brussels/L=Brussels/O=Your Organisation/CN=your-actual-domain.com"

# Set proper permissions
sudo chmod 600 /etc/nginx/ssl/flowintel.key
sudo chmod 644 /etc/nginx/ssl/flowintel.crt
```

**Note**: Self-signed certificates will show a browser warning that users must accept. This option is suitable for testing or internal networks where all users can be instructed to accept the certificate.

#### Option 2: Let's Encrypt (free, automated)

For production environments with internet-accessible servers, use Let's Encrypt for free, trusted certificates:

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Ensure port 80 is accessible from the internet for verification
# Check firewall settings if needed

# Obtain and install certificate (certbot will modify your nginx config)
sudo certbot --nginx -d your-actual-domain.com

# Follow the prompts:
# - Enter your email address for renewal notifications
# - Agree to terms of service
# - Choose whether to redirect HTTP to HTTPS (recommended: Yes)

# Verify certificate installation
sudo certbot certificates

# Test automatic renewal
sudo certbot renew --dry-run
```

Certbot automatically sets up a systemd timer for renewal. Verify it's active:

```bash
sudo systemctl status certbot.timer
```

**Note**: Let's Encrypt certificates are valid for 90 days and renew automatically 30 days before expiration. You'll receive email notifications if renewal fails.

#### Option 3: Organisational certificate authority

If your organisation provides SSL certificates from an internal or commercial CA:

1. Obtain the certificate (`.crt` or `.pem`) and private key (`.key`) from your CA
2. Copy them to the server:
   ```bash
   sudo mkdir -p /etc/nginx/ssl
   sudo cp your-cert.crt /etc/nginx/ssl/flowintel.crt
   sudo cp your-key.key /etc/nginx/ssl/flowintel.key
   sudo chmod 600 /etc/nginx/ssl/flowintel.key
   sudo chmod 644 /etc/nginx/ssl/flowintel.crt
   ```
3. The NGINX configuration is already set to use `/etc/nginx/ssl/flowintel.crt` and `/etc/nginx/ssl/flowintel.key`

**Note**: With this option, you'll need to manually renew certificates before they expire. Set a reminder based on your certificate's validity period.

### Enable the site and test configuration

Now that SSL certificates are in place, enable the site and test the configuration:

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/flowintel /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t
```

A successful test shows:

```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

If the test passes, reload NGINX:

```bash
# Reload NGINX
sudo systemctl reload nginx
```

## Database: PostgreSQL

Flowintel requires PostgreSQL for production use. While SQLite works for development and testing, PostgreSQL provides better performance, concurrency handling, and data integrity for production environments.

### Install PostgreSQL

Install PostgreSQL and required packages:

```bash
sudo apt install -y postgresql postgresql-contrib
```

### Move PostgreSQL data directory (optional, recommended for production)

By default, PostgreSQL stores data in `/var/lib/postgresql`. For better organisation and to keep all Flowintel-related data together, move the PostgreSQL data directory to `/opt/flowintel/database`.

**Note**: Only perform these steps if you want to store database files on the dedicated Flowintel partition. Skip this section if you prefer to use the default PostgreSQL location.

```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Create database directory
sudo mkdir -p /opt/flowintel/database

# Copy existing PostgreSQL data
sudo rsync -av /var/lib/postgresql/ /opt/flowintel/database/

# Rename original directory as backup
sudo mv /var/lib/postgresql /var/lib/postgresql.bak

# Create symlink from original location to new location
sudo ln -s /opt/flowintel/database /var/lib/postgresql

# Set correct ownership
sudo chown -R postgres:postgres /opt/flowintel/database

# Verify the symlink
ls -la /var/lib/ | grep postgresql
```

You should see:
```
lrwxrwxrwx 1 root root   24 Jan 30 08:00 postgresql -> /opt/flowintel/database
```

Start PostgreSQL and verify it works:

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Check status
sudo systemctl status postgresql
```

You should see output showing PostgreSQL is active:

```
● postgresql.service - PostgreSQL RDBMS
     Loaded: loaded (/usr/lib/systemd/system/postgresql.service; enabled; preset: enabled)
     Active: active (exited) since Fri 2026-01-30 07:30:17 UTC; 5s ago
    Process: 11276 ExecStart=/bin/true (code=exited, status=0/SUCCESS)
   Main PID: 11276 (code=exited, status=0/SUCCESS)
        CPU: 2ms

Jan 30 07:30:17 flowintel-dev systemd[1]: Starting postgresql.service - PostgreSQL RDBMS...
Jan 30 07:30:17 flowintel-dev systemd[1]: Finished postgresql.service - PostgreSQL RDBMS.
```

If PostgreSQL starts successfully, remove the backup:

```bash
sudo rm -rf /var/lib/postgresql.bak
```

**Note**: If PostgreSQL fails to start after moving the data directory, see the troubleshooting section on PostgreSQL data directory relocation.

### Configure password encryption

Before creating database users, configure the password encryption method. PostgreSQL supports two main authentication methods:

- **SCRAM-SHA-256 (recommended)**: The most secure method, supported in PostgreSQL 10 and later. Use this for new installations.
- **MD5 (legacy)**: Considered cryptographically weak but acceptable for local-only connections where credentials are never transmitted over a network.

Choose one of the following options:

#### Option 1: SCRAM-SHA-256 (recommended)

Configure PostgreSQL to use SCRAM-SHA-256 for password encryption (replace `15` with your PostgreSQL version: 14, 15, or 16):

```bash
sudo vi /etc/postgresql/15/main/postgresql.conf
```

Find and set (or add if missing):

```
password_encryption = scram-sha-256
```

#### Option 2: MD5 (legacy)

MD5 is the default in most PostgreSQL installations. If you choose to use MD5, no configuration change is needed. However, for clarity, you can explicitly set it (replace `15` with your PostgreSQL version: 14, 15, or 16):

```bash
sudo vi /etc/postgresql/15/main/postgresql.conf
```

Find and set (or add if missing):

```
password_encryption = md5
```

**Note**: For maximum security, use SCRAM-SHA-256. Use MD5 only if you have compatibility concerns or are running an older PostgreSQL version (pre-10).

### Configure authentication

By default, PostgreSQL only accepts local connections. For production deployments where Flowintel runs on the same server, this is secure and requires minimal configuration.

Edit the PostgreSQL host-based authentication file to allow the flowintel user to connect (replace `15` with your PostgreSQL version: 14, 15, or 16):

```bash
sudo vi /etc/postgresql/15/main/pg_hba.conf
```

Add this line before the "local all all peer" line, using the authentication method that matches your password encryption choice:

**If you configured SCRAM-SHA-256:**

```
# Add this line before the "local all all peer" line
local   flowintel       flowintel                               scram-sha-256
```

**If you configured MD5:**

```
# Add this line before the "local all all peer" line
local   flowintel       flowintel                               md5
```

Restart PostgreSQL to apply changes:

```bash
sudo systemctl restart postgresql
```

### Create database and user

PostgreSQL uses peer authentication by default, which means you need to switch to the `postgres` system user to run database commands.

Create a dedicated database user and database for Flowintel:

```bash
# Switch to postgres user
sudo -u postgres psql

# In the PostgreSQL prompt, run these commands:
CREATE USER flowintel WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE flowintel OWNER flowintel;
GRANT ALL PRIVILEGES ON DATABASE flowintel TO flowintel;

# Grant schema permissions
\c flowintel
GRANT ALL ON SCHEMA public TO flowintel;

# Exit PostgreSQL
\q
```

**Security note**: Replace `your_secure_password_here` with a strong password. You'll need this password later when configuring Flowintel.

The user password will be encrypted using the method you configured in the previous step (SCRAM-SHA-256 or MD5).

### Test the connection

Verify you can connect to the database with the flowintel user:

```bash
psql -U flowintel -d flowintel -h localhost -W
```

Enter the password you created earlier. If you see the PostgreSQL prompt, the setup is working correctly. Type `\q` to exit.

## Configure Flowintel

### Create configuration files

Flowintel includes default configuration templates that need to be copied and customised for your installation:

```bash
cp conf/config.py.default conf/config.py
cp conf/config_module.py.default conf/config_module.py
```

These files will be edited in the next steps to match your environment and requirements.

### Configure application settings

Flowintel uses `conf/config.py` for application settings. This file contains different configuration classes for development, testing, and production environments.

#### Key settings overview

Open the configuration file:

```bash
vi conf/config.py
```

**Secret key**

The `SECRET_KEY` is used for session encryption and CSRF protection. Generate a strong random key:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Replace the default value in the `Config` class:

```python
SECRET_KEY = 'your_generated_key_here'
```

**Application binding**

- `FLASK_URL`: IP address Flask binds to (default `127.0.0.1` for local access only)
- `FLASK_PORT`: Port number (default `7006`)

For production with NGINX, keep `127.0.0.1` to ensure Flask only accepts connections from the reverse proxy. If you need to access Flask directly during testing, change to `0.0.0.0`, but never expose this in production.

**Database configuration**

The configuration file includes settings for both development and production databases. The installation script automatically uses the appropriate configuration based on the installation mode you chose.

**Option 1: SQLite (development and testing only)**

```python
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///flowintel.sqlite"
```

The SQLite database file is stored in `instance/flowintel.sqlite` within your Flowintel directory. 

**Important**: SQLite is **not recommended for production use**. It lacks the performance, concurrency handling, and data integrity features required for production deployments.

**Option 2: PostgreSQL (production)**

The `ProductionConfig` class is used with PostgreSQL:

```python
class ProductionConfig(Config):
    db_user = os.getenv('DB_USER', 'flowintel')
    db_password = os.getenv('DB_PASSWORD', 'your_secure_password_here')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'flowintel')
    
    SQLALCHEMY_DATABASE_URI = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
```

Update these values to match the PostgreSQL database and user you created earlier. If you followed the standard setup, the default values shown above should work.

**Session storage**

Flowintel uses Valkey for session management:

```python
VALKEY_IP = os.getenv('VALKEY_IP', '127.0.0.1')
VALKEY_PORT = os.getenv('VALKEY_PORT', '6379')
SESSION_TYPE = "redis"
```

The default settings work for most installations where Valkey runs on the same server. You only need to change these if Valkey is on a different host.

**Note**: Valkey is installed as a systemd service by the Flowintel installation script (`install.safe.sh`) and will be enabled and started automatically. No separate installation is required.

**File upload limits**

Control the maximum file size for attachments:

```python
FILE_UPLOAD_MAX_SIZE = int(os.getenv('FILE_UPLOAD_MAX_SIZE', 5 * 1024 * 1024))  # 5MB default
```

Adjust this based on your storage capacity and typical use case. Remember to keep this value in sync with the NGINX `client_max_body_size` setting.

**Access control**

```python
LIMIT_USER_VIEW_TO_ORG = False
```

When set to `True`, users can only see other users within their own organisation. Administrators always see all users regardless of this setting. For multi-tenant deployments, set this to `True`.

**Initial user accounts**

On first installation, Flowintel creates two users:

```python
INIT_ADMIN_USER = {
    "first_name": "admin",
    "last_name": "admin",
    "email": "admin@admin.admin",
    "password": "admin"
}

INIT_BOT_USER = {
    "first_name": "Matrix",
    "last_name": "Bot",
    "email": "neo@admin.admin"
}
```

**Important**: Change the admin password immediately after first login. The default credentials are well-known and represent a security risk.

The second user (`INIT_BOT_USER`) is used for Matrix notifications. The account is created during installation, but you're not required to use Matrix for notifications. If you don't plan to use Matrix, you can ignore this account.

**Audit logging**

```python
LOG_FILE = os.getenv('LOG_FILE', 'record.log')
AUDIT_LOG_PREFIX = os.getenv('AUDIT_LOG_PREFIX', 'AUDIT')
```

All user actions are logged to this file. The audit log prefix helps when filtering logs. Logs are written to the `logs/` directory within your Flowintel installation.

#### Development vs production settings

The main differences between environments:

| Setting | Development | Production |
|---------|-------------|------------|
| DEBUG | True (shows detailed errors) | False (never enable in production) |
| Database | SQLite (single file) | PostgreSQL (server) |
| SECRET_KEY | Can use default for testing | Must be unique and strong |
| FLASK_URL | Can use 0.0.0.0 for testing | Should be 127.0.0.1 (behind NGINX) |
| Error display | Full stack traces shown | Generic error pages |

Never run production with `DEBUG = True`. This exposes sensitive information and creates security vulnerabilities.

#### Using environment variables

Instead of hardcoding values in `config.py`, you can use environment variables. This is useful for sensitive data like passwords and for changing configuration without modifying code.

The configuration already supports environment variables through `os.getenv()`. You can set these in two ways:

**Option 1: System environment variables**

Set variables before starting Flowintel:

```bash
export DB_PASSWORD='your_secure_password'
export SECRET_KEY='your_secret_key'
export FLASKENV='production'
```

**Option 2: .env file (recommended)**

Create a `.env` file in the Flowintel directory:

```bash
vi .env
```

Add your configuration:

```bash
# Database settings
DB_USER=flowintel
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=flowintel

# Flask environment
FLASKENV=production

# Session storage
VALKEY_IP=127.0.0.1
VALKEY_PORT=6379

# File uploads (in bytes)
FILE_UPLOAD_MAX_SIZE=10485760

# Logging
LOG_FILE=record.log
AUDIT_LOG_PREFIX=AUDIT
```

Set appropriate permissions to protect sensitive values:

```bash
chmod 600 .env
```

The `.env` file approach keeps sensitive data out of version control and makes it easier to manage different environments. Add `.env` to your `.gitignore` file if you're tracking the installation with git.

### Module configuration

The `conf/config_module.py` file contains settings for optional features. In most setups, you won't need to modify this file. The default settings work for standard installations.

You only need to edit `config_module.py` if you're using:

- **SMTP**: For sending email notifications
- **Matrix**: For Matrix chat notifications
- **Computer-assisted generation**: For AI-powered content generation features

If you're not using these features, leave the file unchanged.

## Installing Flowintel

### Run the installation script

Flowintel includes an installation script that sets up the Python environment, installs dependencies, and initialises the database.

The installation script supports two modes:

**Development mode (default)**:
- Uses SQLite database
- Suitable for testing and development
- Easier to set up, no database server required

**Production mode**:
- Uses PostgreSQL database
- Recommended for production deployments
- Requires PostgreSQL to be installed and configured first (see previous sections)

Choose the appropriate installation mode:

**Option 1: Development installation (default)**

```bash
# Assuming you are still in /opt/flowintel/flowintel
bash install.safe.sh
```

**Option 2: Production installation**

Ensure you have completed the PostgreSQL setup and configuration steps before running this command.

```bash
# Assuming you are still in /opt/flowintel/flowintel
bash install.safe.sh --production
```

The installation takes several minutes depending on your internet connection and system performance. On modern systems, expect the process to complete in 5 to 15 minutes. You'll see progress messages as each component is installed.

This script performs the following actions:

1. Creates a Python virtual environment in the `env/` directory
2. Installs all required Python packages from `requirements.txt`
3. Sets up the database schema (SQLite for development, PostgreSQL for production)
4. Creates initial user accounts
5. Loads MISP taxonomies and galaxy data
6. Configures MISP modules

Successful installation output should look like this:

```
THIS APP IS IN PRODUCTION MODE.
  Created: Forensic Case
  Created: New Compromised Workstation
[INFO] Ran ./launch.sh -ip (production init) successfully
[INFO] install.safe.sh completed successfully
[INFO] 
[INFO] Production installation complete!
[INFO] To start Flowintel in production mode, run:
[INFO]   bash launch.sh -p
[INFO] 
[INFO] Or configure as a systemd service (see installation manual).
```

## Starting Flowintel

### Run Flowintel manually

The method for starting Flowintel manually depends on which installation mode you chose:

**Development mode:**

```bash
cd /opt/flowintel/flowintel
bash launch.sh -l
```

The `-l` flag runs Flowintel in the foreground with log output visible. You'll see startup messages, and Flask will bind to the address and port specified in your configuration (default `127.0.0.1:7006`).

**Production mode:**

```bash
cd /opt/flowintel/flowintel
bash launch.sh -p
```

The `-p` flag runs Flowintel in production mode using gunicorn as the WSGI server with 4 worker processes.

Once Flowintel is running, restart NGINX so it recognizes the backend service is available:

```bash
sudo systemctl restart nginx
```

Press `Ctrl+C` to stop Flowintel.

### Run Flowintel as a service

For production use, run Flowintel as a systemd service so it starts automatically on boot and restarts if it crashes.

Flowintel includes a systemd service template. Copy it to the systemd directory:

```bash
sudo cp /opt/flowintel/flowintel/doc/flowintel.service /etc/systemd/system/
```

Edit the service file to replace `yourusername` with the actual user that owns the Flowintel installation:

```bash
sudo sed -i 's/yourusername/your-actual-username/g' /etc/systemd/system/flowintel.service
```

Alternatively, edit the file manually:

```bash
sudo vi /etc/systemd/system/flowintel.service
```

Replace both occurrences of `yourusername` with your actual username in the `User` and `Group` fields.

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable flowintel
sudo systemctl start flowintel
```

Check the service status:

```bash
sudo systemctl status flowintel
```

Successful output should look like this:

```
● flowintel.service - Flowintel Case Management Platform
     Loaded: loaded (/etc/systemd/system/flowintel.service; enabled; preset: enabled)
     Active: active (running) since Fri 2026-01-30 08:04:19 UTC; 22s ago
   Main PID: 14580 (python)
      Tasks: 1 (limit: 4545)
     Memory: 76.6M (peak: 76.6M)
        CPU: 1.050s
     CGroup: /system.slice/flowintel.service
             └─14580 /opt/flowintel/flowintel/env/bin/python app.py
```

You should see `active (running)` in green. If there are errors, check the logs:

```bash
sudo journalctl -u flowintel -f
```

Once Flowintel is running, restart NGINX so it recognizes the backend service is available:

```bash
sudo systemctl restart nginx
```

## Accessing Flowintel

### First login

Open your web browser and navigate to:

```
https://your-actual-domain.com
```

If you used a self-signed certificate, accept the browser security warning.

Log in with the default administrator credentials:

- **Email**: `admin@admin.admin`
- **Password**: `admin`

**Security warning**: Change the administrator password immediately after first login. Go to your user profile and update the password to something secure.

## Log files for monitoring

For security monitoring and compliance, forward these log files to your SIEM or central syslog server:

- **NGINX** access and error logs
    - **Access log**: `/var/log/nginx/flowintel_access.log`
        - Contains all HTTP requests with timestamps, IPs, response codes, and user agents
        - Useful for detecting scanning, brute force attempts, and unusual access patterns
    - **Error log**: `/var/log/nginx/flowintel_error.log`
        - Contains NGINX errors, SSL issues, and upstream connection failures
        - Helpful for troubleshooting reverse proxy issues
- **Flowintel** audit logs
    - **Audit log**: `/opt/flowintel/flowintel/logs/record.log`
        - Contains all user actions within Flowintel (case creation, task updates, user changes)
        - Each entry is prefixed with `AUDIT` by default
        - Critical for compliance and forensic analysis


## Troubleshooting

### NGINX fails to start

**Symptom**: Running `sudo systemctl start nginx` fails or `sudo systemctl status nginx` shows `failed` status.

**Common causes and solutions**:

1. **Port already in use**
   
   Check if another service is using port 80 or 443:
   ```bash
   sudo lsof -i :80
   sudo lsof -i :443
   ```
   
   If Apache or another web server is running, stop it:
   ```bash
   sudo systemctl stop apache2
   sudo systemctl disable apache2
   ```

2. **Configuration syntax error**
   
   Test the NGINX configuration:
   ```bash
   sudo nginx -t
   ```
   
   Look for syntax errors in the output. Common mistakes and their error messages:
   
   **Missing semicolon:**
   ```
   nginx: [emerg] invalid number of arguments in "server_name" directive in /etc/nginx/sites-enabled/flowintel:21
   ```
   Fix: Add semicolon at the end of the line.
   
   **Certificate file not found:**
   ```
   nginx: [emerg] cannot load certificate "/etc/nginx/ssl/flowintel.crt": BIO_new_file() failed
   nginx: configuration file /etc/nginx/nginx.conf test failed
   ```
   Fix: Verify the certificate path and ensure files exist (see SSL certificates section above).
   
   **Invalid proxy_pass URL:**
   ```
   nginx: [emerg] invalid URL prefix in /etc/nginx/sites-enabled/flowintel:52
   ```
   Fix: Ensure `proxy_pass` includes the protocol (e.g., `http://127.0.0.1:7006;`).
   
   **Duplicate server block:**
   ```
   nginx: [warn] conflicting server name "flowintel.yourdomain.com" on 0.0.0.0:443
   ```
   Fix: You may have multiple configurations enabled. Check `/etc/nginx/sites-enabled/`.
   
   After fixing errors, test again with `sudo nginx -t`.

3. **SSL certificate files missing or wrong permissions**
   
   Verify certificate files exist:
   ```bash
   ls -la /etc/nginx/ssl/
   ```
   
   Permissions should be:
   - Private key (`.key`): `600` or `400`
   - Certificate (`.crt`): `644`
   
   Fix permissions if needed:
   ```bash
   sudo chmod 600 /etc/nginx/ssl/flowintel.key
   sudo chmod 644 /etc/nginx/ssl/flowintel.crt
   ```

4. **Check NGINX error log**
   
   View recent errors:
   ```bash
   sudo tail -50 /var/log/nginx/error.log
   ```

### PostgreSQL connection failures

**Symptom**: Flowintel fails to start with database connection errors in the logs.

**Common causes and solutions**:

1. **PostgreSQL service not running**
   
   Check PostgreSQL status:
   ```bash
   sudo systemctl status postgresql
   ```
   
   Start it if stopped:
   ```bash
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

2. **Wrong database credentials**
   
   Verify the database password in your configuration matches what you set:
   ```bash
   psql -U flowintel -d flowintel -h localhost -W
   ```
   
   If this fails, reset the password:
   ```bash
   sudo -u postgres psql
   ALTER USER flowintel WITH PASSWORD 'new_secure_password';
   \q
   ```
   
   Update `conf/config.py` or your `.env` file with the new password.

3. **Authentication method mismatch**
   
   Check the `pg_hba.conf` file (replace `15` with your PostgreSQL version: 14, 15, or 16):
   ```bash
   sudo cat /etc/postgresql/15/main/pg_hba.conf | grep flowintel
   ```
   
   You should see:
   ```
   local   flowintel       flowintel                               md5
   ```
   
   If missing, add it and restart PostgreSQL:
   ```bash
   sudo systemctl restart postgresql
   ```

4. **Database doesn't exist**
   
   Verify the database exists:
   ```bash
   sudo -u postgres psql -c "\l" | grep flowintel
   ```
   
   If missing, create it:
   ```bash
   sudo -u postgres psql
   CREATE DATABASE flowintel OWNER flowintel;
   \q
   ```

5. **PostgreSQL data directory relocation failed**
   
   If you moved the PostgreSQL data directory to `/opt/flowintel/database` and PostgreSQL fails to start, restore the original setup:
   
   ```bash
   # Stop PostgreSQL
   sudo systemctl stop postgresql
   
   # Remove the symlink
   sudo rm /var/lib/postgresql
   
   # Restore the backup
   sudo mv /var/lib/postgresql.bak /var/lib/postgresql
   
   # Start PostgreSQL
   sudo systemctl start postgresql
   ```
   
   Common issues with data directory relocation:
   
   - **Incomplete copy**: Verify all files were copied with `rsync -av`
   - **Wrong permissions**: Ensure `/opt/flowintel/database` is owned by `postgres:postgres`
   - **SELinux/AppArmor**: On systems with mandatory access control, you may need to update policies
   - **Symlink path**: Verify the symlink points to the correct location with `ls -la /var/lib/postgresql`
   
   Check PostgreSQL logs for specific errors:
   ```bash
   sudo journalctl -u postgresql -n 50
   ```

6. **PostgreSQL cannot access data directory (permission denied)**
   
   If PostgreSQL fails to start with permission denied errors like:
   ```
   pg_ctl: could not access directory "/var/lib/postgresql/16/main": Permission denied
   ```
   
   This typically occurs when the PostgreSQL data directory has been relocated to `/opt/flowintel/database` and the parent directory permissions are too restrictive.
   
   **Cause**: If you applied `chmod 750` to `/opt/flowintel`, the postgres user (which is not the owner or in the group) cannot access `/opt/flowintel/database`.
   
   **Solution**: Ensure `/opt/flowintel` has appropriate permissions for postgres to access subdirectories:
   ```bash
   # Check current permissions
   ls -ld /opt/flowintel
   
   # If needed, adjust permissions to allow postgres user access
   sudo chmod 755 /opt/flowintel
   
   # Verify postgres user can access the database directory
   sudo -u postgres ls -la /opt/flowintel/database
   
   # Restart PostgreSQL
   sudo systemctl restart postgresql
   ```
   
   Alternatively, if you need stricter permissions on `/opt/flowintel`:
   - Keep `/opt/flowintel` with 755 permissions
   - Apply restrictive permissions (750) only to `/opt/flowintel/flowintel` (the application directory)
   - Leave `/opt/flowintel/database` accessible to the postgres user

### Flowintel cannot reach NGINX (502 Bad Gateway)

**Symptom**: Accessing Flowintel in the browser shows "502 Bad Gateway" error from NGINX.

**Common causes and solutions**:

1. **Flowintel service not running**
   
   Check if Flowintel is running:
   ```bash
   sudo systemctl status flowintel
   ```
   
   If stopped, check why it failed:
   ```bash
   sudo journalctl -u flowintel -n 50
   ```
   
   Start the service:
   ```bash
   sudo systemctl start flowintel
   ```

2. **Flask not listening on correct address/port**
   
   Verify Flask is listening on `127.0.0.1:7006`:
   ```bash
   sudo lsof -i :7006
   ```
   
   You should see Python listening. If not, check your `conf/config.py`:
   ```python
   FLASK_URL = "127.0.0.1"
   FLASK_PORT = 7006
   ```

3. **NGINX upstream configuration mismatch**
   
   Check the NGINX config points to the correct Flask address:
   ```bash
   grep "proxy_pass" /etc/nginx/sites-available/flowintel
   ```
   
   Should show:
   ```
   proxy_pass http://127.0.0.1:7006;
   ```
   
   If different, edit the file and reload NGINX:
   ```bash
   sudo vi /etc/nginx/sites-available/flowintel
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. **Firewall blocking local connections**
   
   Although rare, verify local connections aren't blocked:
   ```bash
   curl http://127.0.0.1:7006
   ```
   
   This should return HTML from Flask. If it times out, check firewall rules.

### Valkey connection errors

**Symptom**: Flowintel starts but login fails or sessions don't persist. Logs show Valkey connection errors.

**Common causes and solutions**:

1. **Valkey service not running**
   
   Check Valkey status:
   ```bash
   sudo systemctl status valkey
   ```
   
   Start if stopped:
   ```bash
   sudo systemctl start valkey
   sudo systemctl enable valkey
   ```

2. **Wrong Valkey address or port**
   
   Verify Valkey is listening:
   ```bash
   sudo lsof -i :6379
   ```
   
   Should show Valkey listening on port 6379. You can also test connectivity:
   ```bash
   nc -zv 127.0.0.1 6379
   ```
   
   Should respond with `Connection to 127.0.0.1 6379 port [tcp/*] succeeded!`. If not, check your configuration matches:
   ```python
   VALKEY_IP = "127.0.0.1"
   VALKEY_PORT = 6379
   ```

3. **Configuration mismatch**
   
   Check the `conf/config.py` file to ensure `SESSION_TYPE` is set correctly:
   ```bash
   grep SESSION_TYPE conf/config.py
   ```
   
   Should show `SESSION_TYPE = "redis"` (Valkey uses the Redis protocol).

### Permission denied errors

**Symptom**: Flowintel logs show "Permission denied" when trying to write files or access directories.

**Common causes and solutions**:

1. **Wrong file ownership**
   
   Fix ownership of the entire installation:
   ```bash
   sudo chown -R yourusername:yourusername /opt/flowintel/flowintel
   ```

2. **Logs directory not writable**
   
   Ensure logs directory exists and is writable:
   ```bash
   mkdir -p /opt/flowintel/flowintel/logs
   chmod 755 /opt/flowintel/flowintel/logs
   ```

3. **Uploads directory not writable**
   
   Create and set permissions:
   ```bash
   mkdir -p /opt/flowintel/flowintel/uploads
   chmod 755 /opt/flowintel/flowintel/uploads
   ```

### General troubleshooting steps

When facing issues:

1. **Check all services are running**
   ```bash
   sudo systemctl status nginx
   sudo systemctl status postgresql
   sudo systemctl status valkey
   sudo systemctl status flowintel
   ```

2. **Review logs in order**
   ```bash
   # NGINX errors
   sudo tail -50 /var/log/nginx/error.log
   
   # Flowintel application logs
   tail -50 /opt/flowintel/flowintel/logs/record.log
   
   # Systemd service logs
   sudo journalctl -u flowintel -n 50
   ```

3. **Test each component independently**
   - Can you connect to PostgreSQL with the flowintel user?
   - Is Valkey listening on port 6379?
   - Does Flask respond on localhost:7006?
   - Does NGINX configuration pass syntax check?

4. **Verify network connectivity**
   ```bash
   # Test NGINX is listening
   sudo netstat -tlnp | grep nginx
   
   # Test Flask is listening
   sudo netstat -tlnp | grep 7006
   ```

5. **Check disk space**
   ```bash
   df -h
   ```
   
   Full disks cause cryptic errors. Ensure you have at least 1 GB free.

If problems persist, check the GitHub issues page or contact your system administrator with the relevant log excerpts.