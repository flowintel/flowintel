
# Flowintel installation manual

TODO I am not sure it is worth mentionning all the troubleshooting tips for MariaDB. The presence of some for Postgres should already raise ideas when problems occurs with other Backen. Maybe a small memo line to say we propose only some tips for Postgres for legacy ?

## Documentation set

This installation manual is part of a broader documentation set that covers installing, configuring, and using Flowintel. The set also includes:

- [Flowintel encryption guide](encryption-guide.md), which explains the encryption options to consider before installation
- [Flowintel backup and restore](backup-restore.md), a guide to managing backups and restoring data
- [Flowintel user manual](user-manual.md), which covers both the configuration of Flowintel for your organisation and day-to-day use during case handling

## What is Flowintel?

**Flowintel** is an open-source platform for security analysts to organise cases and tasks. It provides workflow tools to track investigations, document findings, and collaborate within teams.

### Technical components

Flowintel is a Python web application written on top of the Flask framework. It runs as a service on a Linux server and is reached by users through a standard web browser. The platform is built from a small number of well established open-source components, each with a clear role. This keeps the operating cost predictable and avoids tying the organisation to a single vendor.

- **Flask application**: the Flowintel codebase itself, written in Python. It implements the case workflow, user interface, permissions, and the integrations with external systems.
- **Gunicorn application server**: runs the Flask application as a set of worker processes. The number of workers is sized to the available CPU cores so that several users can work in parallel without slowing each other down.
- **NGINX reverse proxy**: the public entry point. It terminates HTTPS, serves static assets, and exposes both the user interface and the REST API to the network.
- **PostgreSQL database**: the database system to record cases, tasks, users, audit information, and configuration. SQLite is supported for development and demonstrations only; production deployments use PostgreSQL.
- **Valkey session store**: an in-memory store, compatible with Redis, that holds user session data. Keeping sessions out of the database keeps the user experience responsive and makes it easier to scale the application tier later if needed.
- **MISP modules service**: an enrichment engine that lets analysts pull additional context on observables (IP addresses, domains, files, and similar) from third-party sources such as VirusTotal or CIRCL. It runs as a separate service and is consulted on demand.
- **MISP taxonomies and galaxies**: open vocabularies maintained by the wider CTI community. Flowintel uses them so that classifications and threat actor labels stay aligned with what other security teams use across the sector.
- **Notifications service**: a background worker that produces real-time updates and alerts inside the user interface, so analysts see new assignments and changes without having to refresh.
- **Template repositories**: case and task templates live in Git repositories that Flowintel pulls into a local folder. Teams can keep their own playbooks under version control, share them between Flowintel instances, and bring in templates published by other organisations without copying files by hand.
- **GPG support**: Flowintel can sign and encrypt outbound notifications and accept encrypted input where the workflow requires it. The server holds its own key, and analysts can attach their public keys so that sensitive material stays protected end to end.
- **Optional integrations**: single sign-on with Keycloak and Microsoft Entra ID, mailbox ingestion over IMAP, outbound webhooks, and links to MISP, AIL or Matrix. None of these are required to run Flowintel; they are turned on only when the organisation has the matching infrastructure.

All components run on the same host in a typical installation, which keeps the deployment simple to operate and to back up. The same component layout also runs under Docker Compose for evaluation and test environments.

### Supported operating systems

Flowintel runs on Ubuntu Linux 22.04 LTS and 24.04 LTS. Other Debian-based distributions may work but are not officially tested.

### Architecture

The diagram below shows how the components fit together. A user's browser talks to NGINX over HTTPS. NGINX serves the static files itself and passes everything else to Gunicorn, which dispatches the request to one of the Flowintel worker processes. The worker reads from and writes to PostgreSQL for persistent data, and to Valkey for the user's session. When an analyst asks for enrichment on an observable, the worker calls the MISP modules service and stores the result back in the case. The notifications service runs alongside the application and pushes updates to the browser as cases evolve.

Users sign in either with a local account managed inside Flowintel or through an external identity provider. **Single sign-on** is supported with Keycloak and with Microsoft Entra ID, so organisations that already run a central directory can keep account creation, password policy and multi-factor authentication where they belong. Permissions inside Flowintel are then applied on top of whichever identity the user signed in with.

Cases can also be synchronised with a MISP instance. Once a case is linked to a MISP event, the standard MISP distribution model decides who else gets to see it: the same organisation, a trusted group, all connected communities, or no one at all. This is the same mechanism that the threat intelligence community already uses to share events between departments and between organisations, so Flowintel integrates nicely into existing sharing arrangements without inventing a new protocol.

When analysts add data points to a case (IP addresses, domains, hashes, URLs, and so on), they can run MISP modules against them to pull in additional context from third-party sources and to pivot from one observable to related ones. The enriched information is attached back to the case, which keeps the investigation trail in one place and saves the analyst from copying values between separate tools.

Analysts can also query a connected MISP instance directly from the case. Any matching events or attributes returned by MISP are added back to the case, so prior knowledge held in the organisation's threat intelligence platform shows up next to the current investigation without leaving Flowintel.

Each component runs as its own systemd service on the host. This means the platform starts automatically with the server, can be restarted component by component during maintenance, and is monitored using the same tools the operations team already uses to monitor the rest of the Linux servers. From an ownership point of view, Flowintel is a single application that fits within a normal Linux operations practice, with no exotic runtime requirements and no per-seat licence fees on its components.

Flowintel keeps two kinds of **audit trail**. Activity that belongs to a case (status changes, comments, file uploads, task updates) is recorded inside the database alongside the case itself, so analysts can see the full history of an investigation from the user interface. Application events (logins, errors, background jobs) are written to rotating log files under the `logs/` folder, with `logs/record.log` as the main entry. Operations teams can tail these files directly or forward them to a central log collector if the organisation already runs one.

**Backups** are handled at the data layer. A regular dump of the PostgreSQL database, together with the uploads folder, is enough to restore a working instance on a fresh server. The procedure, including how often to run it and how to test a restore, is described in the [backup and restore guide](backup-restore.md).

For deployments that need data at rest protection, Flowintel can be installed on **encrypted** volumes. The [encryption guide](encryption-guide.md) walks through the choices to make before installation, so that the database, uploads and backups all sit on storage that meets the organisation's confidentiality requirements.

![installation-manual-diagrams/flowintel-installation-Architecture.png](installation-manual-diagrams/flowintel-installation-Architecture.png)

## Pre-installation

### System requirements

![installation-manual-diagrams/flowintel-installation-pre-installation-requirements.png](installation-manual-diagrams/flowintel-installation-pre-installation-requirements.png)

#### Software requirements

- **Operating system**
    - A fully configured Linux system
    - Ubuntu 22.04 LTS or 24.04 LTS
    - The system must be up to date
- **Installation access**
    - During installation, you need:
        - Console or SSH access with sudo privileges
        - Ability to reconfigure system services
        - Permission to modify firewall rules
- **Network requirements**
    - One static IPv4 address; you can disable IPv6 if it is not used in your environment
    - Fully qualified domain name (FQDN) for accessing the web interface
    - **Internet connectivity**
        - The following domains must be accessible during installation:
            - `*.ubuntu.com` (package repositories)
            - `*.github.com`, `*.github.io`, `*.githubusercontent.com` (source code) or a (private) GitLab server where you cloned Flowintel
            - `*.pypi.org`, `*.python.org`, `*.pythonhosted.org` (Python packages)
        - After installation, internet access is only needed for updates.
    - **MISP modules enrichment services** (optional)
        - If you want to use MISP modules to enrich objects using analysers, you need access to the enrichment services such as CIRCL Passive DNS, VirusTotal, and similar platforms.
        - Some of these enrichment services require accounts and API keys. Setting up the analysers is covered in the user manual.
    - **MISP, AIL or Matrix connectivity** (optional)
        - If you plan to integrate Flowintel with MISP, AIL or Matrix, network access to these servers is required.
        - Installing or configuring MISP, AIL or Matrix is not part of this manual.
    - **Entra ID** (optional)
        - If you plan to set up SSO with Microsoft Entra ID, you need access to the Microsoft authentication services, at least `graph.microsoft.com` and `login.microsoftonline.com`.
- **DNS resolution**
    - The system must be able to resolve hostnames. Point the Linux system to corporate DNS servers or use public resolvers.
- **Time synchronisation**
    - Configure NTP to keep the system time accurate. This is critical for audit logging and session management.
- **Web browser**
    - Once the installation is complete, you can access Flowintel from any modern web browser (Chrome, Firefox, Safari, Edge).

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

#### Encryption requirements (optional)

If your environment requires data-at-rest encryption (for GDPR compliance, law enforcement agency policies, or other security requirements), you must consider the encryption options **before** installing Flowintel.

Refer to the [Flowintel encryption guide](encryption-guide.md) for detailed instructions.

There are two encryption options:
- Option 1: **full disk encryption**: Best for new installations. Encrypt the entire system during Ubuntu installation. Follow option 1 in the encryption guide to install the Linux system with full disk encryption, then continue with this installation guide.
- Option 2: **partition encryption**: For existing systems. Encrypt `/opt/flowintel` where all Flowintel data will be stored. Install the Linux system according to your organisation's policies, then follow option 2 in the encryption guide to set up an encrypted volume.

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
- [ ] Internet access to required domains
- [ ] Static IP address configured
- [ ] FQDN defined for the web interface
- [ ] The hardware meets the minimum requirements (8 GB RAM, 80 GB storage)
- [ ] NTP configured and time synchronised
- [ ] DNS resolution working
- [ ] SSL certificate available (or plan to use self-signed)
- [ ] Firewall rules configured
- [ ] Decision on encryption options

### Installation source

Flowintel is installed directly from its Git repository. There is no installer package or pre-built binary. The installation process clones the repository and sets up dependencies using standard Python and Linux tools.

# Installing Linux services

Before installing Flowintel itself, you need to set up several Linux services it depends on. This section walks through each service in the order shown below.

- Prepare the Linux system 
- Create the installation location
- Download Flowintel
- Set up the reverse proxy (NGINX)
- Set up the database (PostgreSQL)

![installation-manual-diagrams/flowintel-installation-high-level-overview.png](installation-manual-diagrams/flowintel-installation-high-level-overview.png)

## System preparation

Start by updating the operating system and installing the packages that Flowintel and its build process depend on. You will also configure the host firewall so that only the required ports are open.

**Virtual machine users**: If you're installing on a VM, create a snapshot before proceeding. This allows you to revert to a known good state if something goes wrong during installation.

### Packages

Make sure your Linux system is fully updated:

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

### Firewall

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

After executing the `ufw status` command, you should see output showing SSH (22/tcp), HTTP (80/tcp), and HTTPS (443/tcp) are allowed.

```bash
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443                        ALLOW       Anywhere
```

**Note**: If you're connected via SSH, ensure SSH is allowed before enabling the firewall to avoid locking yourself out.

**Remote PostgreSQL**: If you run PostgreSQL on a separate server rather than on the same machine as Flowintel, you also need to allow inbound traffic on port 5432 from the Flowintel server. Restrict the rule to the specific source IP so the database is not exposed to the wider network:

```bash
# On the PostgreSQL server (replace with the Flowintel server's IP)
sudo ufw allow from 10.0.0.5 to any port 5432
```

![installation-manual-diagrams/flowintel-installation-Network.png](installation-manual-diagrams/flowintel-installation-Network.png)

## Installation location

Flowintel stores its application files, configuration, and uploaded attachments under a single directory tree. Choosing the right location now makes future backups, storage expansion, and disaster recovery much simpler.

For better organisation and easier backups, create a dedicated partition or mount point for Flowintel.

### Option 1: Simple directory

A simple directory under `/opt/flowintel` is suitable for development, testing, and smaller production installations. It is the quickest option to set up and is perfectly acceptable if you do not need separate storage management features.

```bash
# Create installation directory
sudo mkdir -p /opt/flowintel

# Set ownership (replace 'yourusername' with your actual username)
sudo chown -R yourusername:yourusername /opt/flowintel
```

### Option 2: LVM partition (recommended for production)

For production environments, a dedicated LVM partition is the more robust option because it keeps Flowintel data separate from the operating system and makes it easier to manage growth, backups, snapshots, and future expansion. The Logical Volume Manager, or LVM, is a Linux-based storage management technology that adds an abstraction layer between physical disks and filesystems, enabling flexible, dynamic storage allocation.

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

**Expanding LVM volumes** (when additional storage is needed)

A key advantage of LVM is that you can expand storage without downtime. If you need more space in the future:

```bash
# Add a new physical disk to the volume group (for example /dev/sdc)
sudo pvcreate /dev/sdc
sudo vgextend flowintel-vg /dev/sdc

# Extend the logical volume (add all free space from new disk)
sudo lvextend -l +100%FREE /dev/flowintel-vg/flowintel-lv

# Resize the filesystem to use the new space
sudo resize2fs /dev/flowintel-vg/flowintel-lv

# Verify new size
df -h /opt/flowintel
```

This process can be performed while Flowintel is running, but it is best to schedule it during a maintenance window.

## Download Flowintel

Flowintel is distributed as a Git repository rather than a packaged installer. You clone the repository, optionally check out a tagged release, and then lock down the file permissions.

### Clone the repository

Download Flowintel from GitHub:

```bash
# Download Flowintel into /opt/flowintel
cd /opt/flowintel
git clone https://github.com/flowintel/flowintel.git
cd flowintel
```

The repository is now cloned to `/opt/flowintel/flowintel`. All subsequent commands assume you're working from this directory.

### Install a specific version

Flowintel uses Git tags to mark releases. You can find the list of available versions at:

https://github.com/flowintel/flowintel/tags

Each tag corresponds to a release (e.g. `3.1.0`), with release notes available at `https://github.com/flowintel/flowintel/releases/tag/<version>`.

To install a specific version instead of the latest development code, pass the tag to `git clone`:

```bash
cd /opt/flowintel
git clone --branch 3.1.0 --single-branch https://github.com/flowintel/flowintel.git
cd flowintel
```

Replace `3.1.0` with the tag of the version you want to install. Using `--single-branch` avoids downloading the full history of other branches.

### Secure file permissions

Set appropriate permissions on the Flowintel application directory to prevent unauthorised access:

```bash
# Set secure permissions (owner read/write/execute, group read/execute, no access for others)
sudo chmod 750 /opt/flowintel/flowintel
```

You should see the following output when you run `ls -l /opt/flowintel/`:
```
drwxr-x--- 10 yourusername yourusername 4096 Jan 30 08:00 /opt/flowintel/flowintel
```

This restricts access to the owner and group members, preventing other users on the system from reading sensitive configuration files or data.

**Important**: Do not apply chmod 750 to `/opt/flowintel` if you relocate the PostgreSQL data directory to `/opt/flowintel/database` (covered in the database section). This would prevent PostgreSQL from accessing the database. Only apply the permission restrictions to `/opt/flowintel/flowintel`.

## Setup the reverse proxy

NGINX sits between users and the Flask application, handling TLS termination, static file serving, and request buffering. While you can access Flask directly during development, running Flowintel behind a reverse proxy is strongly recommended for production.

**Note**: If you're just testing Flowintel, you can skip this section and access Flask directly at `http://localhost:7006`. For production deployments, continue with the NGINX setup below.

### Set up NGINX

```bash
# Install and enable nginx
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

Replace **flowintel.yourdomain.com** with your actual hostname (**your-actual-domain.com**) throughout this guide. If you're setting this up for internal use without public DNS, add an entry to your DNS server or use local hosts files on client machines.

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
  -subj "/C=BE/ST=Brussels/L=Brussels/O=Your Organisation/CN=flowintel.yourdomain.com"

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
sudo certbot --nginx -d flowintel.yourdomain.com

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

A successful test with `nginx -t` shows:

```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

If the test passes, reload NGINX:

```bash
# Reload NGINX
sudo systemctl reload nginx
```

## Database

This section covers installing PostgreSQL, creating the Flowintel database and user, and configuring authentication. Flowintel requires PostgreSQL for production use. While SQLite works for development and testing, PostgreSQL provides better performance, concurrency handling, and data integrity for production environments.

### Install PostgreSQL

Install PostgreSQL and required packages:

```bash
sudo apt install -y postgresql postgresql-contrib
```

### Move PostgreSQL data directory (optional, but recommended for production)

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

Before creating database users, decide which password encryption method to use. PostgreSQL offers two options:

- Option 1: **SCRAM-SHA-256 (recommended)**: The most secure method, supported in PostgreSQL 10 and later. Use this for new installations.
- Option 2: **MD5 (legacy)**: Considered cryptographically weak but acceptable for local-only connections where credentials are never transmitted over a network.

You can determine your PostgreSQL version by running `sudo -u postgres psql -c 'SELECT version();'`.

#### Option 1: SCRAM-SHA-256 (recommended)

Configure PostgreSQL to use SCRAM-SHA-256 for password encryption (replace `16` with your PostgreSQL version: 14, 15, or 16):

```bash
sudo vi /etc/postgresql/16/main/postgresql.conf
```

Find and set (or add if missing):

```
password_encryption = scram-sha-256
```

#### Option 2: MD5 (legacy)

MD5 is the default in most PostgreSQL installations. If you choose to use MD5, no configuration change is needed. However, for clarity, you can explicitly set it (replace `16` with your PostgreSQL version: 14, 15, or 16):

```bash
sudo vi /etc/postgresql/16/main/postgresql.conf
```

Find and set (or add if missing):

```
password_encryption = md5
```

**Note**: For maximum security, use SCRAM-SHA-256. Use MD5 only if you have compatibility concerns or are running an older PostgreSQL version (pre-10).

### Configure authentication

By default, PostgreSQL only accepts local connections. For production deployments where Flowintel runs on the same server, this is secure and requires minimal configuration.

Edit the PostgreSQL host-based authentication file to allow the flowintel user to connect (replace `16` with your PostgreSQL version: 14, 15, or 16):

```bash
sudo vi /etc/postgresql/16/main/pg_hba.conf
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

Enter the password you created earlier. 

```bash
psql (16.13 (Ubuntu 16.13-0ubuntu0.24.04.1))
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, compression: off)
Type "help" for help.

flowintel=>
```

If you see the PostgreSQL prompt, the setup is working correctly. Type `\q` to exit.


# Configure Flowintel for installation

With the system packages, reverse proxy, and database in place, the next step is to configure the Flowintel application. These settings must be in place before you run the installation script.

## Configuration files

Flowintel includes default configuration templates that need to be copied and customised for your installation:

```bash
cp conf/config.py.default conf/config.py
cp conf/config_module.py.default conf/config_module.py
```

## Configure the base application settings

Once Flowintel is installed, some of these settings can also be changed through the web interface by users with the **Admin** role. This section covers only the settings needed to get Flowintel up and running; detailed configuration options are documented in the user manual.

![installation-manual-diagrams/flowintel-installation-Configuration.png](installation-manual-diagrams/flowintel-installation-Configuration.png)

Flowintel reads configuration from environment variables. The recommended way to provide them is a `.env` file: it keeps sensitive data such as database passwords and secret keys out of `conf/config.py`, loads automatically on startup so settings persist across reboots, and is straightforward to back up or transfer to a new server. For development and testing you can edit `conf/config.py` directly instead.

## Environment file

From the template file, create a `.env` file in the Flowintel directory and restrict file permissions to prevent unauthorised access:

```bash
cp /opt/flowintel/flowintel/template.env /opt/flowintel/flowintel/.env
chmod 600 /opt/flowintel/flowintel/.env
```

Then open the file for editing.

```
vi /opt/flowintel/flowintel/.env
```

## Base configuration

### Secret key

`SECRET_KEY` is used for Flask session encryption and CSRF protection. It must be unique to your installation: if two installations share the same key, a session token from one could be accepted by the other. Generate a strong random value in a separate terminal and paste it into `.env`:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Database connection

The `DB_*` variables tell Flowintel how to connect to PostgreSQL. Set them to match the database and user you created in the database section earlier. `DB_HOST` should be `localhost` when PostgreSQL runs on the same server as Flowintel. `DB_PORT` defaults to `5432` and rarely needs changing.

### File uploads

Users can attach files to cases and tasks, for example evidence, screenshots, or reports. These files are stored on disk in the `uploads/files/` directory within the Flowintel installation, not in the database. `FILE_UPLOAD_MAX_SIZE` controls the maximum size of a single uploaded file, expressed in bytes. The default is 5 MB (5242880 bytes).

If you increase this limit, also update the `client_max_body_size` directive in `/etc/nginx/sites-available/flowintel` to match, otherwise NGINX will reject large uploads before they reach Flowintel. The value included in the NGINX template is `50M`, which comfortably covers the default upload limit. After changing the NGINX configuration, test and reload it:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Reverse proxy settings

When Flowintel runs behind NGINX, Flask needs to read the forwarded headers that NGINX adds so it can determine the real client IP address, the original protocol (HTTP or HTTPS), and the hostname the client requested. Without this, Flask only sees connections from `127.0.0.1` and cannot construct correct redirect URLs.

`BEHIND_PROXY` enables Werkzeug's ProxyFix middleware, which reads those headers. Set it to `true` for any production deployment behind NGINX.

`PROXY_X_FOR` is the number of proxy servers between your users and Flowintel. If NGINX runs on the same server as Flowintel, set this to `1`. If users first pass through a corporate proxy and then reach NGINX, set it to `2`. Setting it too high allows clients to spoof their IP address by injecting forged headers, so keep this value as low as your network topology allows.

`PROXY_X_PROTO` tells Flask to trust the `X-Forwarded-Proto` header so it can distinguish HTTP from HTTPS requests. `PROXY_X_HOST` trusts the `X-Forwarded-Host` header so Flask knows the original hostname. `PROXY_X_PREFIX` trusts the `X-Forwarded-Prefix` header, which is only needed if Flowintel is served under a URL sub-path; the default value of `0` disables it.

### Other settings

The remaining variables in `template.env` cover areas such as appearance (logos, welcome text, GDPR notice), single sign-on via Microsoft Entra ID or Keycloak, outbound webhooks, MISP connector defaults, GPG report signing, and IMAP notification archiving. These are all optional for a basic installation.

### Minimum configuration values to set

Update at least the following configuration values before running the installation script:

```bash
# Secret key for Flask session encryption and CSRF protection
SECRET_KEY="your_generated_secret_key_here"

# Database settings
DB_USER=flowintel
DB_PASSWORD=your_secure_password_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=flowintel

# Application environment
FLOWINTEL_APP_ENV="production"
```

## Key configuration options

The table below covers all settings from `template.env` (`.env`):

| Setting | Purpose | Example value |
|---------|---------|---|
| `SECRET_KEY` | Session encryption and CSRF protection (generate a strong random key) | 64-character hex string |
| `DB_NAME` | PostgreSQL database name | `flowintel` |
| `DB_USER` | PostgreSQL database user | `flowintel` |
| `DB_PASSWORD` | PostgreSQL user password | Strong password |
| `DB_HOST` | PostgreSQL server address | `localhost` or `192.168.1.100` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `VALKEY_IP` | Valkey session storage IP | `127.0.0.1` |
| `VALKEY_PORT` | Valkey port | `6379` |
| `ENFORCE_PRIVILEGED_CASE` | Enable privileged-case controls | `true` |
| `PRIVILEGED_CASE_ADD_ADMIN_ON_TASK_REQUEST` | Auto-add admins to requested privileged tasks | `true` |
| `ENABLE_CHATBOT` | Toggle chatbot routes/menu | `false` |
| `FILE_UPLOAD_MAX_SIZE` | Maximum file upload size in bytes | `5242880` (5 MB) |
| `BEHIND_PROXY` | Enable reverse proxy support | `true` or `false` |
| `PROXY_X_FOR` | Number of proxies to trust | `1` |
| `PROXY_X_PROTO` | Trust X-Forwarded-Proto header | `1` |
| `PROXY_X_HOST` | Trust X-Forwarded-Host header | `1` |
| `PROXY_X_PREFIX` | Trust X-Forwarded-Prefix header | `0` or `1` |
| `FLOWINTEL_APP_ENV` | Flowintel runtime environment | `production` |
| `AUDIT_LOG_PREFIX` | Prefix used for audit log entries | `AUDIT` |
| `LOG_FILE` | Audit/application log filename | `record.log` |
| `MAIN_LOGO` | Main application logo path | `/static/image/flowintel.png` |
| `TOPRIGHT_LOGO` | Top-right logo path | empty string |
| `FOOTER_1_LOGO` | First footer logo path | empty string |
| `FOOTER_2_LOGO` | Second footer logo path | empty string |
| `WELCOME_TEXT_TOP` | Login page top text | empty string |
| `WELCOME_TEXT_BOTTOM` | Login page bottom text | empty string |
| `WELCOME_LOGO` | Login page logo path | empty string |
| `SHOW_GDPR_NOTICE` | Show GDPR notice in forms | `true` |
| `GDPR_NOTICE` | GDPR notice text | Custom string |
| `ENTRA_ID_ENABLED` | Enable Microsoft Entra ID SSO | `true` or `false` |
| `ENTRA_TENANT_ID` | Entra tenant ID | GUID |
| `ENTRA_CLIENT_ID` | Entra application client ID | GUID |
| `ENTRA_CLIENT_SECRET` | Entra client secret | Secret string |
| `ENTRA_REDIRECT_URL` | Entra callback URL | `https://<host>/account/entra/callback` |
| `ENTRA_GROUP_ADMIN` | Entra group mapped to Admin onboarding flow | `FlowintelAdmin` |
| `ENTRA_GROUP_EDITOR` | Entra group mapped to Editor | `FlowintelEditor` |
| `ENTRA_GROUP_READONLY` | Entra group mapped to Read Only | `FlowintelReadOnly` |
| `ENTRA_GROUP_CASE_ADMIN` | Entra group mapped to CaseAdmin | `FlowintelCaseAdmin` |
| `ENTRA_ROLE_CASE_ADMIN` | Flowintel role name for CaseAdmin mapping | `CaseAdmin` |
| `ENTRA_GROUP_QUEUE_ADMIN` | Entra group mapped to QueueAdmin | `FlowintelQueueAdmin` |
| `ENTRA_ROLE_QUEUE_ADMIN` | Flowintel role name for QueueAdmin mapping | `QueueAdmin` |
| `ENTRA_GROUP_QUEUER` | Entra group mapped to Queuer | `FlowintelQueuer` |
| `ENTRA_ROLE_QUEUER` | Flowintel role name for Queuer mapping | `Queuer` |
| `KEYCLOAK_ENABLED` | Enable Keycloak SSO | `true` or `false` |
| `KEYCLOAK_BASE_URL` | Keycloak server base URL | `https://keycloak.example.com` |
| `KEYCLOAK_REALM` | Keycloak realm | `flowintel` |
| `KEYCLOAK_CLIENT_ID` | Keycloak client ID | `flowintel` |
| `KEYCLOAK_CLIENT_SECRET` | Keycloak client secret | Secret string |
| `KEYCLOAK_REDIRECT_URL` | Keycloak callback URL | `https://<host>/account/keycloak/callback` |
| `KEYCLOAK_GROUP_ADMIN` | Keycloak group mapped to Admin onboarding flow | `FlowintelAdmin` |
| `KEYCLOAK_GROUP_EDITOR` | Keycloak group mapped to Editor | `FlowintelEditor` |
| `KEYCLOAK_GROUP_READONLY` | Keycloak group mapped to Read Only | `FlowintelReadOnly` |
| `KEYCLOAK_GROUP_CASE_ADMIN` | Keycloak group mapped to CaseAdmin | `FlowintelCaseAdmin` |
| `KEYCLOAK_ROLE_CASE_ADMIN` | Flowintel role name for CaseAdmin mapping | `CaseAdmin` |
| `KEYCLOAK_GROUP_QUEUE_ADMIN` | Keycloak group mapped to QueueAdmin | `FlowintelQueueAdmin` |
| `KEYCLOAK_ROLE_QUEUE_ADMIN` | Flowintel role name for QueueAdmin mapping | `QueueAdmin` |
| `KEYCLOAK_GROUP_QUEUER` | Keycloak group mapped to Queuer | `FlowintelQueuer` |
| `KEYCLOAK_ROLE_QUEUER` | Flowintel role name for Queuer mapping | `Queuer` |
TODO ADD SIMPLE SAML
| `WEBHOOK_URL` | Outbound webhook URL for new-case events | `https://example.com/webhook` |
| `WEBHOOK_ENABLED` | Enable outbound new-case webhook | `false` |
| `WEBHOOK_SECRET` | HMAC secret for webhook signing | Secret string |
| `MISP_EXPORT_FILES` | Include case/task files in MISP exports | `true` or `false` |
| `MISP_EVENT_THREAT_LEVEL` | Default MISP threat level | `4` |
| `MISP_EVENT_ANALYSIS` | Default MISP analysis status | `0` |
| `MISP_ADD_LOCAL_TAGS_ALL_EVENTS` | Local tags applied to MISP events | `curation:source="flowintel"` |
| `REPOSITORY_BASE_PATH` | Base path for template repositories | `modules/repositories` |
| `GPG_HOME` | GPG home/keyring directory for report signing | `/home/user/.gnupg` or empty |
| `GPG_KEY_ID` | GPG signing key identifier | Key ID, fingerprint, or empty |
| `GPG_PASSPHRASE` | Passphrase for GPG signing key | Secret string or empty |
| `IMAP_SERVER` | IMAP server for notification archiving | `imap.gmail.com` |
| `IMAP_PORT` | IMAP server port | `993` |
| `IMAP_USER` | IMAP username | `your-email@example.com` |
| `IMAP_PASSWORD` | IMAP password/app password | Secret string |
| `IMAP_USE_SSL` | Enable SSL for IMAP connection | `true` |

## Alternative: Direct config.py editing (development and testing only)

For development and testing environments, you can edit `conf/config.py` directly instead of using a `.env` file. This approach is simpler for local development but is **not recommended for production** because it stores credentials in the configuration file.

Open and edit config.py

```bash
vi /opt/flowintel/flowintel/conf/config.py
```

The first section of the file contains the base `Config` class. The settings below apply to all environments (development, testing, and production).

```python
class Config:
```

When editing `config.py`, search for variable names that match the `.env` keys (for example `DB_USER`, `DB_PASSWORD`, `FILE_UPLOAD_MAX_SIZE`, `BEHIND_PROXY`, `MISP_EXPORT_FILES`). This makes it easy to map `.env` values to the corresponding config entries.

Keep these settings in `config.py` at their defaults unless you have a specific reason to change them:

**Valkey session storage**:

```python
VALKEY_IP = os.getenv('VALKEY_IP', '127.0.0.1')
VALKEY_PORT = os.getenv('VALKEY_PORT', '6379')
SESSION_TYPE = "redis"
```

You only need to change these if Valkey is on a different host. **Note**: `SESSION_TYPE` is set to `"redis"` because Valkey is compatible with Redis and uses the same client protocol.

**System roles**:

```python
SYSTEM_ROLES = [1, 2, 3]
```

Flowintel has three built-in roles (Admin, Editor, Read only) that should remain unchanged.

## Initial user accounts

When Flowintel runs for the first time, it creates two built-in user accounts: an administrator and a bot account. These accounts are defined by `INIT_ADMIN_USER` and `INIT_BOT_USER` in the configuration file. You can change the names and email addresses before the first run, but the settings are only read during the initial bootstrapping of the application. Once the accounts exist in the database, changes to these values have no effect.

**Administrator account**

The administrator account is the first account you use to log in after installation. It has full administrative privileges.

```python
INIT_ADMIN_USER = {
    "first_name": "admin",
    "last_name": "admin",
    "email": "admin@admin.admin",
    "password": "admin"
}
```

**Important**: Change the administrator password immediately after your first login. The default credentials are publicly documented and represent a serious security risk. Navigate to your user profile in the web interface to set a strong password.

**Bot account**

The bot account is used internally for Matrix chat notifications. Flowintel creates this account during installation regardless of whether you plan to use Matrix.

```python
INIT_BOT_USER = {
    "first_name": "Matrix",
    "last_name": "Bot",
    "email": "neo@admin.admin"
}
```

If you do not intend to use Matrix notifications, you can leave this account as it is. It does not need to be deleted and has no administrative privileges.


## Database configuration

The configuration file includes settings for both development and production databases. The installation script automatically uses the appropriate configuration based on the installation mode you chose.

### Option 1: SQLite (development and testing only)

```python
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///flowintel.sqlite"
```

The SQLite database file is stored in `instance/flowintel.sqlite` within your Flowintel directory. 

**Important**: SQLite is **not recommended for production use**. It lacks the performance, concurrency handling, and data integrity features required for production deployments.

### Option 2: PostgreSQL (production)

The `ProductionConfig` class is used with PostgreSQL and gets the database host, port name, username, and password through environment variables via the `.env` file as described in the base configuration section above.


## Development, testing and production settings

The main differences between environments:

| Setting | Development | Testing | Production |
|---------|-------------|---------|------------|
| DEBUG | True (shows detailed errors) | False | False (never enable in production) |
| TESTING | False | True (disables CSRF checks) | False |
| Database | SQLite (`flowintel.sqlite`) | SQLite (`flowintel-test.sqlite`) | PostgreSQL (server) |
| SECRET_KEY | Can use default | Can use default | Must be unique and strong |
| FLASK_URL | Can use 0.0.0.0 | Can use 0.0.0.0 | Should be 127.0.0.1 (behind NGINX) |
| Error display | Full stack traces shown | Full stack traces shown | Generic error pages |
| BEHIND_PROXY | Direct access to Flask | Direct access to Flask | Access via NGINX |
| Sample cases | Imported | Not imported | Not imported |

Sample test cases are included in development installations to give new users something to explore immediately. Production and testing installations skip this import. This is not controlled by the configuration file but by the installation mode you choose when running the installation script.

The testing configuration uses a separate SQLite database to avoid interfering with development data. It also disables CSRF token validation (`WTF_CSRF_ENABLED = False`) so that automated tests can submit forms without generating tokens.

Never run production with `DEBUG = True`. This exposes sensitive information and creates security vulnerabilities.


## Microsoft Entra ID SSO (optional)

Flowintel supports single sign-on via Microsoft Entra ID (formerly Azure AD). When enabled, users can sign in with their Microsoft account instead of a local password. Local accounts still work alongside SSO.

### Azure portal setup

Before configuring Flowintel, register an application in the [Azure portal](https://portal.azure.com/):

1. Go to Microsoft Entra ID → App registrations → **New registration**
2. Set the **Name** to something like `Flowintel`
3. Set **Supported account types** to *Accounts in this organizational directory only*
4. Add a **Redirect URI** (Web platform):
   ```
   https://flowintel.yourdomain.com/account/entra/callback
   ```
5. After registration, note the **Directory (tenant) ID** and **Application (client) ID** from the Overview page
6. Under **Certificates & secrets → New client secret**, create a secret and note its value immediately (it is only shown once)
7. Under **API permissions**, add:
   - `Microsoft Graph → Delegated → User.Read` (usually present by default)
   - `Microsoft Graph → Delegated → GroupMember.Read.All`
   - Click **Grant admin consent**

### Entra ID group setup

Flowintel uses Entra ID group membership to assign roles. Create the following security groups in your Entra ID tenant, then add users to the appropriate group:

| Entra ID group | Flowintel role | Notes |
|---|---|---|
| `FlowintelAdmin` | Editor | Account is created as **Editor**; all admins receive a notification to promote the user to Admin manually |
| `FlowintelEditor` | Editor | Standard analyst access |
| `FlowintelCaseAdmin` | CaseAdmin | Can manage cases and approve tasks |
| `FlowintelQueueAdmin` | QueueAdmin | Can manage queues and approve tasks |
| `FlowintelQueuer` | Queuer | Can submit tasks for approval in privileged cases |
| `FlowintelReadOnly` | Read Only | View-only access |

When a user signs in for the first time, Flowintel checks their group memberships in the order listed above. The first matching group determines their role. Users not in any of these groups are denied access.

If a user is a member of multiple groups (for example both `FlowintelQueueAdmin` and `FlowintelReadOnly`), the higher-priority group wins. `FlowintelReadOnly` is checked last so it only applies when none of the more specific groups match.

If your organisation uses different group names, you can customise the mappings with the environment variables shown below.

Flowintel synchronises roles on every SSO login. If a user's Entra ID group membership changes, their Flowintel role is updated the next time they sign in. Be aware that if you manually promote an SSO user to a higher role within Flowintel, that change will be overwritten at their next login unless their Entra ID group membership has also been updated.

### Flowintel configuration for Entra ID

Add the following to your `.env` file (or set the equivalent environment variables):

```bash
# Entra ID App
ENTRA_ID_ENABLED=true
ENTRA_TENANT_ID=<your-directory-tenant-id>
ENTRA_CLIENT_ID=<your-application-client-id>
ENTRA_CLIENT_SECRET=<your-client-secret>
ENTRA_REDIRECT_URL=https://flowintel.yourdomain.com/account/entra/callback
```

The `ENTRA_REDIRECT_URL` must exactly match the redirect URI registered in the Azure portal, including the scheme (`https://`). If Flowintel runs behind a reverse proxy, make sure this URL reflects the public-facing address rather than the internal `127.0.0.1` address.

The group and role name mappings can be customised if your Entra ID groups are named differently:

```bash
# Entra ID group names
ENTRA_GROUP_ADMIN=FlowintelAdmin
ENTRA_GROUP_EDITOR=FlowintelEditor
ENTRA_GROUP_READONLY=FlowintelReadOnly
ENTRA_GROUP_CASE_ADMIN=FlowintelCaseAdmin
ENTRA_GROUP_QUEUE_ADMIN=FlowintelQueueAdmin
ENTRA_GROUP_QUEUER=FlowintelQueuer

# Flowintel role names for the custom roles
ENTRA_ROLE_CASE_ADMIN=CaseAdmin
ENTRA_ROLE_QUEUE_ADMIN=QueueAdmin
ENTRA_ROLE_QUEUER=Queuer
```

### SSO behaviour

When Entra ID SSO is enabled (`ENTRA_ID_ENABLED=true`), a **Sign in with Microsoft** button appears on the Flowintel login page. The first time a user signs in through SSO, Flowintel automatically creates a local account for them based on their Entra ID profile.

Users whose highest-priority group is `FlowintelAdmin` are initially created with the **Editor** role rather than Admin. This is a deliberate safeguard: it ensures that no one receives full administrative access automatically, reducing the risk of accidental privilege escalation.

All existing Flowintel administrators receive a notification whenever a new SSO account is created. For users in the Admin group, the notification asks administrators to promote the user if appropriate. For all other users, the notification asks administrators to review the user's organisation assignment. New SSO users are placed in a personal organisation by default, so administrators may want to move them to a shared organisation.

SSO accounts rely entirely on the organisation's Microsoft account for authentication. This means they cannot use the local password reset feature or change the email address associated with their Flowintel account. Administrators can still edit SSO user accounts through the web interface, for example to change a user's role or organisation, but they cannot set a local password for them.

## Keycloak SSO (optional)

Flowintel supports single sign-on via Keycloak. When enabled, users can sign in with their Keycloak account instead of a local password. Local accounts still work alongside SSO. The Keycloak integration follows the same role-mapping model as the Entra ID integration described above.

### Keycloak server prerequisites

You need a running Keycloak instance (version 20 or later) before configuring Flowintel. The examples below assume Keycloak is reachable at `https://keycloak.your-org-keycloak.com`. Replace this with the address of your own Keycloak server.

### Create a realm

If you do not already have a dedicated realm for Flowintel, create one:

1. Open the Keycloak admin console at `https://keycloak.your-org-keycloak.com/admin/`
2. In the top-left realm dropdown, click **Create realm**
3. Set the **Realm name** to `flowintel`
4. Make sure **Enabled** is on, then click **Create**

All the steps below are carried out inside this `flowintel` realm.

### Create an OpenID Connect client

1. In the Keycloak admin console, go to **Clients → Create client**
2. Set **Client type** to `OpenID Connect`
3. Set **Client ID** to `flowintel` (you can pick a different name, but take note of it for the Flowintel configuration later)
4. Click **Next**
5. On the Capability config step:
   - Enable **Client authentication** (this makes it a confidential client)
   - Ensure **Standard flow** is enabled (Authorization Code flow)
   - Disable **Direct access grants** unless you need them for testing
6. Click **Next**
7. On the Login settings step, configure the redirect URI:
   ```
   https://flowintel.yourdomain.com/account/keycloak/callback
   ```
   Set **Valid post logout redirect URIs** to:
   ```
   https://flowintel.yourdomain.com/*
   ```
   Set **Web origins** to:
   ```
   https://flowintel.yourdomain.com
   ```
8. Click **Save**

After saving, go to the **Credentials** tab and copy the **Client secret**. You will need it when configuring Flowintel.

Note down the following values:

| Value | Where to find it | Example |
|---|---|---|
| Realm name | Top-left dropdown | `flowintel` |
| Client ID | Clients → flowintel → Settings | `flowintel` |
| Client secret | Clients → flowintel → Credentials | `AbCdEf...` |
| Keycloak base URL | Your Keycloak address | `https://keycloak.your-org-keycloak.com` |

### Create groups for role mapping

Flowintel uses Keycloak group membership to assign roles, in the same way as it uses Entra ID groups. Create the following groups in your realm:

1. In the Keycloak admin console, go to **Groups → Create group**
2. Create each of the following groups:

| Keycloak group | Flowintel role | Notes |
|---|---|---|
| `FlowintelAdmin` | Editor | Account is created as **Editor**; all admins receive a notification to promote the user to Admin manually |
| `FlowintelEditor` | Editor | Standard analyst access |
| `FlowintelCaseAdmin` | CaseAdmin | Can manage cases and approve tasks |
| `FlowintelQueueAdmin` | QueueAdmin | Can manage queues and approve tasks |
| `FlowintelQueuer` | Queuer | Can submit tasks for approval in privileged cases |
| `FlowintelReadOnly` | Read Only | View-only access |

When a user signs in for the first time, Flowintel checks their group memberships in the order listed above. The first matching group determines their role. Users not in any of these groups are denied access.

### Assign users to groups

1. Go to **Users** in the Keycloak admin console
2. Select a user (or create one)
3. Go to the **Groups** tab
4. Click **Join Group** and select the appropriate Flowintel group

### Add a group membership mapper

Keycloak does not include group information in tokens by default. You need to add a client scope mapper so that Flowintel can read the user's groups from the token.

1. Go to **Clients** in the left menu, then click on your `flowintel` client
2. Go to the **Client scopes** tab
3. Click on the `flowintel-dedicated` scope. Keycloak creates this scope automatically when you create a client, and names it `<client-id>-dedicated`. If you do not see it in the list, click **Add client scope**, select **flowintel-dedicated**, and add it as a **Default** scope. If no dedicated scope exists at all, you can create one manually: go to **Client scopes** in the left menu, click **Create client scope**, name it `flowintel-dedicated`, set the type to **Default**, and then assign it to your client from the client's **Client scopes** tab.
4. Click **Configure a new mapper**
4. Select **Group Membership**
5. Configure the mapper:
   - **Name**: `groups`
   - **Token Claim Name**: `groups`
   - **Full group path**: **OFF** (Flowintel expects flat group names, not paths like `/FlowintelAdmin`)
   - **Add to ID token**: **ON**
   - **Add to access token**: **ON**
   - **Add to userinfo**: **ON**
6. Click **Save**

With this mapper in place, every token issued for the Flowintel client will include a `groups` claim with the user's group names.

### Verify the token contains groups

Before moving on to Flowintel, it is worth checking that the token contains the expected claims. In the Keycloak admin console:

1. Go to **Clients → flowintel → Client scopes**
2. Click **Evaluate**
3. Select a user who is a member of one of the Flowintel groups
4. Click **Generated ID token**
5. Confirm the JSON contains:
   - `preferred_username` or `email`
   - `given_name` and `family_name` (or `name`). If these are empty, open the user in **Users**, fill in **First name** and **Last name**, and save. Keycloak does not require these fields when creating a user, but Flowintel needs them to set up the local account.
   - `groups` array with the user's group names, for example `["FlowintelEditor"]`

If the `groups` claim is missing, check that the mapper from the previous step is correctly configured and assigned to the `flowintel-dedicated` scope.

### Flowintel configuration for Keycloak

Add the following to your `.env` file (or set the equivalent environment variables):

```bash
# Keycloak SSO
KEYCLOAK_ENABLED=true
KEYCLOAK_BASE_URL=https://keycloak.your-org-keycloak.com
KEYCLOAK_REALM=flowintel
KEYCLOAK_CLIENT_ID=flowintel
KEYCLOAK_CLIENT_SECRET=<your-client-secret>
KEYCLOAK_REDIRECT_URL=https://flowintel.yourdomain.com/account/keycloak/callback
```

The `KEYCLOAK_REDIRECT_URL` must exactly match the redirect URI registered in Keycloak, including the scheme (`https://`). If Flowintel runs behind a reverse proxy, make sure this URL reflects the public-facing address rather than the internal `127.0.0.1` address.

The group and role name mappings can be customised if your Keycloak groups are named differently:

```bash
# Keycloak group names
KEYCLOAK_GROUP_ADMIN=FlowintelAdmin
KEYCLOAK_GROUP_EDITOR=FlowintelEditor
KEYCLOAK_GROUP_READONLY=FlowintelReadOnly
KEYCLOAK_GROUP_CASE_ADMIN=FlowintelCaseAdmin
KEYCLOAK_GROUP_QUEUE_ADMIN=FlowintelQueueAdmin
KEYCLOAK_GROUP_QUEUER=FlowintelQueuer

# Flowintel role names for the custom roles
KEYCLOAK_ROLE_CASE_ADMIN=CaseAdmin
KEYCLOAK_ROLE_QUEUE_ADMIN=QueueAdmin
KEYCLOAK_ROLE_QUEUER=Queuer
```

### SSO behaviour

When Keycloak SSO is enabled (`KEYCLOAK_ENABLED=true`), a **Sign in with Keycloak** button appears on the Flowintel login page. The first time a user signs in through SSO, Flowintel automatically creates a local account for them based on their Keycloak profile.

Users whose highest-priority group is `FlowintelAdmin` are initially created with the **Editor** role rather than Admin. This is intentional: no one should receive full administrative access automatically.

All existing Flowintel administrators receive a notification whenever a new SSO account is created. For users in the Admin group, the notification asks administrators to promote the user if appropriate. For all other users, the notification asks administrators to review the user's organisation assignment. New SSO users are placed in a personal organisation by default, so administrators may want to move them to a shared organisation.

SSO accounts rely on the organisation's Keycloak instance for authentication. Users who sign in through Keycloak cannot use the local password reset feature or change the email address on their Flowintel account. Administrators can still edit SSO user accounts through the web interface, for example to change a user's role or organisation, but cannot set a local password for them.

Flowintel synchronises roles on every SSO login. If a user's Keycloak group membership changes, their Flowintel role is updated the next time they sign in. If you manually promote an SSO user to a higher role within Flowintel, that change will be overwritten at their next login unless their Keycloak group membership has also been updated.

## GPG report signing (optional)

Flowintel can digitally sign case reports with a GPG key. When configured, every generated report includes a detached GPG signature that recipients can verify independently. If you do not need signed reports, skip this section, report generation works without it.

You can either create a new key or use an existing key.

### Create a signing key

Generate a dedicated GPG key for the user account that runs Flowintel. When prompted, select **RSA and RSA** as the key type and set the key size to **4096** bits. For the expiry, you can either set the key not to expire or choose a specific date, depending on your organisation's key-rotation policy.

```bash
gpg --full-generate-key
```

If Flowintel runs as a systemd service under a dedicated user (for example `yourusername`), generate the key as that user so it is stored in the correct keyring:

```bash
sudo -u yourusername gpg --full-generate-key
```

When GPG asks for a user ID, use a dedicated email address (for example `flowintel-signing@flowintel.yourdomain.com`) so the key is clearly linked to the application rather than to an individual person.

Set a passphrase when prompted. You will need to enter this passphrase in the Flowintel configuration file later.

After generation, GPG displays the key location and the path to the revocation certificate. Copy the revocation certificate to a secure, offline location; you will need it if the key is ever compromised.

Verify the key was created by listing all keys on the keyring:

```bash
gpg --list-keys --keyid-format long
```

#### Export the public key

Recipients of signed reports need your public key to verify the signature. Export it in armored (text) format so it can be shared by email, published on a website, or uploaded to a key server:

```bash
gpg --export --armor flowintel-signing@flowintel.yourdomain.com > flowintel-signing-public.asc
```

Distribute `flowintel-signing-public.asc` to anyone who needs to verify your signed reports.

#### Verify a signature externally

When a recipient downloads a signed report from Flowintel, they receive two files: the report itself (for example `case-report.pdf`) and a detached signature file (for example `case-report.pdf.sig`). To verify the signature outside of Flowintel:

1. Import the Flowintel public key (only needed once):

    ```bash
    gpg --import flowintel-signing-public.asc
    ```

2. Verify the signature against the report:

    ```bash
    gpg --verify case-report.pdf.sig case-report.pdf
    ```

3. GPG prints the result. A valid signature looks like:

    ```
    gpg: Signature made Mon 30 Mar 2026 10:00:00 AM UTC
    gpg:                using RSA key ABCDEF1234567890ABCDEF1234567890ABCDEF12
    gpg: Good signature from "flowintel-signing@flowintel.yourdomain.com"
    ```

    If the signature does not match, GPG prints `BAD signature`. In that case, the report may have been modified after signing.

### Use an existing key

If you already have a GPG key pair on another machine (for example your workstation), you can export it and transfer it to the Flowintel server.

#### Export the key pair

On the machine that holds the key, export both the public and private key to armored files. Replace `flowintel-signing@flowintel.yourdomain.com` with the email address or fingerprint of your key:

```bash
gpg --export --armor flowintel-signing@flowintel.yourdomain.com > flowintel-signing-public.asc
gpg --export-secret-keys --armor flowintel-signing@flowintel.yourdomain.com > flowintel-signing-private.asc
```

Transfer both files to the Flowintel server using a secure method such as `scp`:

```bash
scp flowintel-signing-public.asc flowintel-signing-private.asc yourusername@flowintel-server:/tmp/
```

After the transfer, delete the exported private key file from the source machine.

#### Import the keys on the server

On the Flowintel server, import the public key first, then the private key. If Flowintel runs as a dedicated user, import as that user so the keys end up in the correct keyring:

```bash
sudo -u yourusername gpg --import /tmp/flowintel-signing-public.asc
sudo -u yourusername gpg --import /tmp/flowintel-signing-private.asc
```

Verify that both keys were imported:

```bash
sudo -u yourusername gpg --list-keys --keyid-format long
sudo -u yourusername gpg --list-secret-keys --keyid-format long
```

The output should show the key with `sec` (secret/private) and `pub` (public) entries. If you only see `pub`, the private key was not imported correctly.

Once the import is confirmed, remove the key files from the temporary location.

### Configure Flowintel for report signing

Set the GPG settings:

```python
# GPG report signing
GPG_BINARY = "/usr/bin/gpg"                 # Absolute path to the gpg binary
GPG_HOME = "/home/yourusername/.gnupg"      # Path to the GPG keyring directory
GPG_KEY_ID = "flowintel-signing@flowintel.yourdomain.com"  # Fingerprint or email of the signing key
GPG_PASSPHRASE = "your_passphrase_here"     # Passphrase for the key (leave empty if unprotected)
```

| Setting | Description |
|---------|-------------|
| `GPG_BINARY` | Absolute path to the `gpg` binary (for example `/usr/bin/gpg`). Using an absolute path avoids issues with restricted `PATH` environments under gunicorn or systemd. Defaults to `gpg` if left empty. |
| `GPG_HOME` | Absolute path to the `.gnupg` directory that holds the signing key. Leave empty to use the default keyring of the process owner. |
| `GPG_KEY_ID` | Fingerprint or email address that identifies the signing key. Must match a key present in the keyring. |
| `GPG_PASSPHRASE` | Passphrase that unlocks the private key. Leave empty if the key has no passphrase. |

Leave all three settings empty to disable signing. When `GPG_KEY_ID` is empty, Flowintel skips signing entirely and reports are generated without a signature.

### Disabling signing

`GPG_KEY_ID` is the only setting that controls whether signing is active. Setting `GPG_HOME` or `GPG_PASSPHRASE` to an empty string does **not** disable signing:

- An empty `GPG_HOME` causes GPG to fall back to the default keyring (`~/.gnupg`). If a matching key exists there, signing will still succeed.
- An empty `GPG_PASSPHRASE` does not prevent signing either. The `gpg-agent` process caches passphrases across sessions, so GPG can unlock the key without being given the passphrase again. This cache persists until the agent is restarted or its timeout expires.

To fully disable signing, clear `GPG_KEY_ID`:

```python
GPG_KEY_ID = ""
```

If you want to stop the `gpg-agent` from caching passphrases (for example during testing), you can flush its cache:

```bash
gpgconf --kill gpg-agent
```

## MISP connector configuration (optional)

Flowintel can export case and task data to a MISP instance through its connector system. The settings in this section do not set up the connection to MISP itself; they control the default values that Flowintel applies when it creates or updates events on your MISP server. The actual connector (URL, API key, and organisation) is configured later through the web interface.

If you do not plan to use the MISP connector, you can leave these settings at their defaults.

### File export behaviour

The `MISP_EXPORT_FILES` setting controls whether file attachments are included when Flowintel exports a case or task to MISP. When set to `True`, any files uploaded to a case or task (for example evidence, screenshots, or documents) are attached as attributes on the corresponding MISP event. When set to `False`, only structured data such as observables, notes, and metadata is exported and file attachments are skipped.

```python
MISP_EXPORT_FILES = os.getenv('MISP_EXPORT_FILES', 'false').lower() == 'true
```

The default is `False`. Enable this if your analysts need file evidence included in MISP events.

### Event threat level

Every MISP event carries a threat level that indicates its severity. The `MISP_EVENT_THREAT_LEVEL` setting determines which threat level Flowintel assigns by default when it creates a new event. MISP uses the following scale:

| Value | Meaning   |
|-------|-----------|
| 1     | High      |
| 2     | Medium    |
| 3     | Low       |
| 4     | Undefined |

```python
MISP_EVENT_THREAT_LEVEL = 4
```

The default is `4` (Undefined). Adjust this to match the classification that best fits your organisation's workflow. Analysts can still change the threat level on individual events within MISP after export.

### Event analysis state

MISP events also carry an analysis state that tracks how far the investigation has progressed. The `MISP_EVENT_ANALYSIS` setting determines the default state assigned to newly created events. MISP uses the following values:

| Value | Meaning  |
|-------|----------|
| 0     | Initial  |
| 1     | Ongoing  |
| 2     | Complete |

```python
MISP_EVENT_ANALYSIS = 0
```

The default is `0` (Initial). Events exported from Flowintel typically start as Initial and are progressed to Ongoing or Complete within MISP as the analysis develops.

### Automatic local tags

The `MISP_ADD_LOCAL_TAGS_ALL_EVENTS` setting defines a list of local tags that Flowintel automatically applies to every MISP event it creates or updates. Local tags are visible only on your own MISP instance and are never synchronised with other servers, which makes them well suited for internal workflow tracking and source attribution.

The value accepts either a single string or a list of strings:

```python
# Single tag
MISP_ADD_LOCAL_TAGS_ALL_EVENTS = 'curation:source="flowintel"'

# Multiple tags
MISP_ADD_LOCAL_TAGS_ALL_EVENTS = [
    'workflow:state="incomplete"',
    'curation:source="flowintel"'
]
```

The default is `'curation:source="flowintel"'`, which marks every exported event as originating from Flowintel. Set this to an empty string or an empty list if you do not want any tags applied automatically.

## Module configuration (optional)

The `conf/config_module.py` file contains settings for optional features. The default settings work for standard installations.

You only need to edit `config_module.py` if you're using:

- **SMTP**: For sending email notifications
- **Matrix**: For Matrix chat notifications
- **Computer-assisted generation**: For AI-powered content generation features

If you're not using these features, leave the file unchanged.

## Chatbot (optional)

Flowintel ships with an conversational assistant that can answer questions about the cases and tasks you have access to. It is **disabled by default** to keep the base installation light and to avoid pointing the platform at an external language model without an explicit decision from the operator.

### Enabling the chatbot

The chatbot is controlled by a single flag in `conf/config.py`:

```python
ENABLE_CHATBOT = True
```

When the flag is set to `False` (the default), the **Chatbot** entry is hidden from the sidebar and every `/chatbot/` route returns a 404. Setting it to `True` re-exposes the menu item and the routes.

The chatbot itself talks to an Ollama instance, so you also need to point Flowintel at it. These values live in `conf/config_module.py`:

```python
OLLAMA_URL = "http://localhost:11434"   # URL of the Ollama server
OLLAMA_KEY = ""                         # Optional bearer token
OLLAMA_MODEL = ""                       # Default model name (optional)
```

If `OLLAMA_URL` is not reachable, the chatbot page still loads but the model dropdown stays empty and queries fail with a clear error. Restart Flowintel after changing either configuration file.

### Technical background

The chatbot is a thin Flask blueprint (`app/chatbot/`) that wires three external pieces together:

- **Ollama** runs the actual large language model. It is a separate service, hosted by you, and Flowintel never sends prompts anywhere else. Install it from <https://ollama.com> and pull at least one model, for example `ollama pull llama3`.
- **LiteLLM** (`litellm` Python package) provides the uniform client used to talk to Ollama. It abstracts the model-specific request format so the same code works against different back-ends.
- **DSPy** (`dspy` Python package) defines the question/answer signature and orchestrates the call. It gives the chatbot a structured prompt rather than a free-form one.
- **MCP** (Model Context Protocol, `mcp` package together with the `flowintel-mcp` server) lets the model call back into Flowintel's REST API to look up cases, tasks and other data on your behalf. The MCP server is started in a background thread on the first chatbot request and uses your personal API key, so the assistant only sees what you would see in the web interface.

# Installing Flowintel

## Run the installation script

Flowintel includes an installation script that sets up the Python environment, installs dependencies, and initialises the database.

### Python virtual environment

Flowintel runs inside a Python virtual environment. A virtual environment is an isolated copy of the Python interpreter and its package library, kept in a self-contained directory within the project. This isolation means that the packages Flowintel needs do not interfere with system-level Python libraries or with other Python applications on the same server.

The main advantages are:

- **Dependency isolation**: Each application keeps its own set of packages at the exact versions it requires, so an upgrade for one project cannot break another.
- **Clean uninstallation**: Because everything lives inside a single directory, removing the virtual environment removes all installed packages with it.
- **No root privileges for packages**: Python packages are installed under the project directory rather than in system paths, so `pip install` does not need `sudo`.
- **Reproducibility**: The `requirements.txt` file pins dependencies, ensuring that a fresh installation produces the same environment every time.

The installation script creates the virtual environment automatically. The directory name is hardcoded as `env` in both the installer and the system scripts (`VENV_DIR="env"`), so you do not need to create or activate it yourself. If the `env/` directory does not already exist when you run the installer, the script creates it for you. It then installs all libraries listed in `requirements.txt` into the virtual environment and copies the Python binary into `env/bin/python`, so that Flowintel always uses its own interpreter regardless of any system-wide Python changes.

When you start Flowintel through `launch.sh` or the systemd service, the scripts reference `env/bin/python` directly, which means the virtual environment is used without requiring manual activation.

### Installation mode 

The installation script supports two installation modes:

![installation-manual-diagrams/flowintel-installation-Installation.png](installation-manual-diagrams/flowintel-installation-Installation.png)

**Development mode (default)**:
- Uses SQLite database
- Suitable for testing and development
- Easier to set up, no database server required
- Installs sample cases

**Production mode**:
- Uses PostgreSQL database
- Recommended for production deployments
- Requires PostgreSQL to be installed and configured first (see previous sections)

Choose the appropriate installation mode:

Option 1: **Development installation (default)**

```bash
# Assuming you are still in /opt/flowintel/flowintel
bash install.safe.sh
```

Option 2: **Production installation**

Make sure you have completed the PostgreSQL setup and configuration steps before running this command.

```bash
# Assuming you are still in /opt/flowintel/flowintel
bash install.safe.sh --production
```

### Installation progress

The installation takes several minutes depending on your internet connection and system performance. On modern systems, expect the process to complete in 10 to 15 minutes. You'll see progress messages as each component is installed.

Several steps in the script require elevated privileges, so it will prompt you for your **sudo password** during execution.

This script performs the following actions:

1. Creates a Python virtual environment in the `env/` directory
2. Installs all required Python packages from `requirements.txt`
3. Sets up the database schema (SQLite for development, PostgreSQL for production)
4. Creates initial user accounts
5. Loads MISP taxonomies and galaxy data
6. Configures MISP modules

### Successful installation

Successful installation output should look like this:

```bash
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

### Verify the installation

Before moving on, confirm that Flowintel can start and respond to requests. Run it briefly in the foreground:

```bash
bash launch.sh -l
```

In a second terminal session, check that Flask is listening:

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7006/
```

A response code of `200` or `302` confirms that the application is running. If you get `000` or the connection is refused, review the terminal output from `launch.sh` for error messages.

# Starting Flowintel

## Run Flowintel manually

Use this for development or to verify the installation. Run Flowintel in the foreground with log output visible:

```bash
cd /opt/flowintel/flowintel
bash launch.sh -l
```

The `-l` flag binds Flask to the address and port specified in your configuration (default `127.0.0.1:7006`). Press `Ctrl+C` to stop Flowintel.

**For production deployments, use the systemd service described in the next section.** Running directly with `launch.sh` is not recommended for production: the process is not supervised, does not start on boot, and stops when the terminal session closes.

## Run Flowintel as a service

For production use, run Flowintel as a systemd service so it starts automatically on boot and restarts if it crashes.

Flowintel ships with three systemd service templates in the `doc/` directory:

- `flowintel.service` : the main application (Gunicorn)
- `flowintel-misp-modules.service` : the MISP modules enrichment service
- `flowintel-notifications.service` : the notification service

Copy all three to the systemd directory:

```bash
sudo cp /opt/flowintel/flowintel/doc/flowintel.service /etc/systemd/system/
sudo cp /opt/flowintel/flowintel/doc/flowintel-misp-modules.service /etc/systemd/system/
sudo cp /opt/flowintel/flowintel/doc/flowintel-notifications.service /etc/systemd/system/
```

Edit all three service files to replace `yourusername` with the actual user that owns the Flowintel installation:

```bash
sudo sed -i 's/yourusername/your-actual-username/g' \
  /etc/systemd/system/flowintel.service \
  /etc/systemd/system/flowintel-misp-modules.service \
  /etc/systemd/system/flowintel-notifications.service
```

Alternatively, edit each file manually and replace both occurrences of `yourusername` with your actual username in the `User` and `Group` fields.

The main service file contains the following directives:

```ini
[Unit]
Description=Flowintel Case Management Platform
After=network.target postgresql.service valkey.service
Requires=postgresql.service valkey.service
Wants=flowintel-misp-modules.service flowintel-notifications.service

[Service]
Type=simple
User=yourusername
Group=yourusername
WorkingDirectory=/opt/flowintel/flowintel
Environment="PATH=/opt/flowintel/flowintel/env/bin:/usr/local/bin:/usr/bin:/bin"
Environment="FLOWINTEL_APP_ENV=production"
Environment="HISTORY_DIR=/opt/flowintel/flowintel/history"
ExecStart=/opt/flowintel/flowintel/env/bin/gunicorn -w 4 "app:create_app()" -b 127.0.0.1:7006 --access-logfile -
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

The `[Unit]` section declares that Flowintel depends on PostgreSQL and Valkey; systemd will start those services first and stop Flowintel if either of them fails. The `Wants=` directive tells systemd to also start the MISP modules and notification services when Flowintel starts. `Type=simple` tells systemd that the process started by `ExecStart` is the main service process. `Restart=on-failure` means systemd will automatically restart Flowintel if it exits with a non-zero status, waiting 10 seconds (`RestartSec`) between attempts. `WantedBy=multi-user.target` ensures the service starts during normal multi-user boot.

The `ExecStart` directive uses Gunicorn with 4 worker processes. Each worker handles requests independently, so more workers allow Flowintel to serve more users at the same time. A common rule of thumb is to set the worker count to (2 x CPU cores) + 1. For a 4-core server, that would be 9 workers. To change the default, edit the `-w` value in the service file:

```bash
ExecStart=/opt/flowintel/flowintel/env/bin/gunicorn -w 9 "app:create_app()" -b 127.0.0.1:7006 --access-logfile -
```

Avoid setting the worker count too high on systems with limited memory, as each worker runs a separate copy of the application. The bind address (`127.0.0.1:7006`) should match the `FLASK_URL` and `FLASK_PORT` values in `conf/config.py`.

If you need to adjust resource limits (for example capping memory usage), you can add directives such as `MemoryMax=512M` or `CPUQuota=200%` in the `[Service]` section.

Enable and start the services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable flowintel flowintel-misp-modules flowintel-notifications
sudo systemctl start flowintel
```

Starting the main `flowintel` service automatically pulls in the MISP modules and notification services because of the `Wants=` directive.

Check the service status:

```bash
sudo systemctl status flowintel
```

Successful output should look like this:

```
● flowintel.service - Flowintel Case Management Platform
     Loaded: loaded (/etc/systemd/system/flowintel.service; enabled; preset: enabled)
     Active: active (running) since Fri 2026-01-30 08:04:19 UTC; 22s ago
   Main PID: 14580 (gunicorn)
      Tasks: 5 (limit: 4545)
     Memory: 156.2M (peak: 160.0M)
        CPU: 2.340s
     CGroup: /system.slice/flowintel.service
             ├─14580 /opt/flowintel/flowintel/env/bin/python /opt/flowintel/flowintel/env/bin/gunicorn ...
             ├─14582 /opt/flowintel/flowintel/env/bin/python /opt/flowintel/flowintel/env/bin/gunicorn ...
             ├─14583 /opt/flowintel/flowintel/env/bin/python /opt/flowintel/flowintel/env/bin/gunicorn ...
             ├─14584 /opt/flowintel/flowintel/env/bin/python /opt/flowintel/flowintel/env/bin/gunicorn ...
             └─14585 /opt/flowintel/flowintel/env/bin/python /opt/flowintel/flowintel/env/bin/gunicorn ...
```

You should see `active (running)` in green. You can also verify the companion services:

```bash
sudo systemctl status flowintel-misp-modules
sudo systemctl status flowintel-notifications
```

If there are errors, check the logs:

```bash
sudo journalctl -u flowintel -f
sudo journalctl -u flowintel-misp-modules -f
sudo journalctl -u flowintel-notifications -f
```

Once Flowintel is running, restart NGINX so it recognises the backend service is available:

```bash
sudo systemctl restart nginx
```

# Accessing Flowintel

## First login

Open your web browser and navigate to:

```
https://flowintel.yourdomain.com
```

If you used a self-signed certificate, accept the browser security warning.

Log in with the default administrator credentials. If you customised the `INIT_ADMIN_USER` settings in the configuration file before installation, use those credentials instead.

- **Email**: `admin@admin.admin`
- **Password**: `admin`

After a successful login, Flowintel displays its welcome page:
![installation-manual-diagrams/flowintel-installation-firstlogin.png](installation-manual-diagrams/flowintel-installation-firstlogin.png)

**Security warning**: Change the administrator password immediately after your first login. Navigate to your user profile in the web interface and set a strong password. These default credentials are defined in the configuration file and are only used to bootstrap the initial account. Once you update the password through the web interface, the values in the configuration file are no longer read.

# Monitoring

## Log files for monitoring

For security monitoring and compliance, forward these log files to your SIEM or central syslog server:

- **NGINX** access and error logs
    - **Access log**: `/var/log/nginx/flowintel_access.log`
        - Contains all HTTP requests with timestamps, IPs, response codes, and user agents
        - Useful for detecting scanning, brute force attempts, and unusual access patterns
    - **Error log**: `/var/log/nginx/flowintel_error.log`
        - Contains NGINX errors, SSL issues, and upstream connection failures
        - Helpful for troubleshooting reverse proxy issues
- **Flowintel** application log
    - **Log file**: `/opt/flowintel/flowintel/logs/record.log`
        - Contains Flask access logs (requests, responses) and application-level events
        - Audit entries are prefixed with `AUDIT` and can be filtered with `grep AUDIT record.log`
        - Useful for compliance, forensic analysis, and tracking user actions such as case creation, task updates, and user changes

Administrators (and users with the **Audit Viewer** role) do not need shell access to inspect the audit trail. The same `AUDIT` entries from `record.log`, together with the per-case history files, are exposed in Flowintel under **Tools > Audit logs**. The page lets you filter by date range, user, action and an exclude string, and download the filtered result as CSV or JSON straight from the browser.

### Log rotation (optional)

Log rotation prevents log files from growing indefinitely and filling up the disk. Setting up rotation is optional, but recommended for any long-running installation.

NGINX logs are typically already rotated by the configuration that ships with the NGINX (or Apache) package (`/etc/logrotate.d/nginx`). You do not need to configure rotation for those files yourself.

The Flowintel application log and the backup log (if you run scheduled backups) are not covered by any default rotation policy. To rotate them, create a logrotate configuration file:

```bash
sudo vi /etc/logrotate.d/flowintel
```

Add the following content, replacing `yourusername` with the user account that runs Flowintel:

```
/opt/flowintel/flowintel/logs/record.log /opt/flowintel/backups/backup.log {
    weekly
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 0640 yourusername yourusername
}
```

| Directive | Meaning |
|-----------|---------|
| `weekly` | Rotate once per week |
| `missingok` | Do not report an error if a log file is missing (useful when the backup log does not exist yet) |
| `rotate 52` | Keep 52 rotated files (one year of weekly rotations) |
| `compress` | Compress rotated files with gzip |
| `delaycompress` | Wait one rotation cycle before compressing, so the most recent rotated file stays uncompressed |
| `notifempty` | Skip rotation if the log file is empty |
| `create 0640 yourusername yourusername` | After rotation, create a new log file with the specified permissions and ownership |

Test the configuration by running a dry run:

```bash
sudo logrotate --debug /etc/logrotate.d/flowintel
```


# Troubleshooting

## Installation errors

**Symptom**: Running `git clone https://github.com/flowintel/flowintel.git` fails with a permission error:

`fatal: could not create work tree dir 'flowintel': Permission denied`

**Common causes and solutions**:

1. **Wrong directory**

   You are not inside `/opt/flowintel`. Change to the correct directory first with `cd /opt/flowintel`.

2. **Insufficient permissions**

   Your user does not own the target directory. Set the correct ownership by running `sudo chown yourusername:yourusername /opt/flowintel`, replacing `yourusername` with the account that will run Flowintel.

## NGINX fails to start

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
   Fix: Ensure `proxy_pass` includes the protocol (for example `http://127.0.0.1:7006;`).
   
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

## PostgreSQL connection failures

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
   ALTER USER flowintel WITH PASSWORD 'your_secure_password_here';
   \q
   ```
   
   Update `conf/config.py` or your `.env` file with the new password.

3. **Authentication method mismatch**
   
   Check the `pg_hba.conf` file (replace `16` with your PostgreSQL version: 14, 15, or 16):
   ```bash
   sudo cat /etc/postgresql/16/main/pg_hba.conf | grep flowintel
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

## Flowintel cannot reach NGINX (502 Bad Gateway)

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

## NGINX logs "upstream sent duplicate header line: Date"

**Symptom**: The NGINX error log (`/var/log/nginx/flowintel_error.log`) contains repeated warnings like:

```
upstream sent duplicate header line: "Date: Mon, 30 Mar 2026 12:00:00 GMT",
previous value: "Date: Mon, 30 Mar 2026 12:00:00 GMT", ignored while reading
response header from upstream, client: 192.168.x.x, server: flowintel.example.com,
request: "GET /static/js/utils.js HTTP/2.0",
upstream: "http://127.0.0.1:7006/static/js/utils.js"
```

**This warning is harmless.** The Flask application server sends its own `Date` header, and NGINX adds one as well. NGINX detects the duplicate, logs a warning, and ignores the upstream value. It does not affect functionality or cause errors for users.

To silence the warnings, add `proxy_hide_header Date;` to the NGINX `location` block so NGINX strips the upstream `Date` header before processing:

```nginx
location / {
    proxy_pass http://127.0.0.1:7006;
    proxy_hide_header Date;
    # ... rest of your proxy settings
}
```

Then test and reload the configuration:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Valkey connection errors

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

2. **Wrong Valkey address: `VALKEY_IP` set to `valkey` instead of `127.0.0.1`**

   `valkey` is the Docker Compose service name. On a direct Linux installation this hostname cannot be resolved and Flowintel fails with:

   ```
   redis.exceptions.ConnectionError: Error -3 connecting to valkey:6379. Temporary failure in name resolution.
   ```

   Open `.env` and set the correct address:

   ```bash
   VALKEY_IP=127.0.0.1
   ```

   Then restart Flowintel.

3. **Valkey not running or not listening on the expected port**
   
   Verify Valkey is listening:
   ```bash
   sudo lsof -i :6379
   ```
   
   Should show Valkey listening on port 6379. You can also test connectivity:
   ```bash
   nc -zv 127.0.0.1 6379
   ```
   
   Should respond with `Connection to 127.0.0.1 6379 port [tcp/*] succeeded!`. If not, check your `.env` matches:
   ```
   VALKEY_IP=127.0.0.1
   VALKEY_PORT=6379
   ```

4. **Configuration mismatch**
   
   Check the `conf/config.py` file to ensure `SESSION_TYPE` is set correctly:
   ```bash
   grep SESSION_TYPE conf/config.py
   ```
   
   Should show `SESSION_TYPE = "redis"` (Valkey uses the Redis protocol).

## Permission denied errors

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

## Keycloak SSO

| Symptom | Likely cause | Fix |
|---|---|---|
| Redirect fails after clicking "Sign in with Keycloak" | `KEYCLOAK_REDIRECT_URL` does not match the URI registered in Keycloak | Ensure the URLs are identical, including trailing slashes and scheme |
| User denied access despite being in a group | `groups` claim missing from the token | Add the Group Membership mapper as described in the Keycloak SSO section and set **Full group path** to OFF |
| Token contains `/FlowintelEditor` instead of `FlowintelEditor` | **Full group path** is enabled in the mapper | Edit the mapper and set **Full group path** to OFF |
| "Invalid client" error | Client authentication is disabled or wrong secret | Check the Credentials tab in Keycloak and verify `KEYCLOAK_CLIENT_SECRET` |
| SSO works but user gets the wrong role | User is in multiple groups | The highest-priority group wins; check the group priority table in the Keycloak SSO section |

## General troubleshooting steps

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
   
   Full disks cause cryptic errors. Make sure you have at least 1 GB free.

If problems persist, check the GitHub issues page or contact your system administrator with the relevant log excerpts.

# Security hardening checklist

The steps above produce a working installation. The recommendations below go further and help reduce the attack surface of the server. Apply them based on your organisation's security policies.

## SSH access

- Disable password authentication and require SSH key pairs instead. In `/etc/ssh/sshd_config`:
  ```
  PasswordAuthentication no
  PubkeyAuthentication yes
  ```
  Restart the SSH service after making changes: `sudo systemctl restart sshd`.
- Change the default SSH port if your policy requires it, and update the UFW rule accordingly.
- Limit SSH access to specific source IP addresses or ranges where possible.

## Brute-force protection

Install fail2ban to block repeated failed login attempts for SSH and other services:

```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

The default configuration monitors SSH out of the box. Check the active jails with:

```bash
sudo fail2ban-client status
```

## Disable unused services

List all listening services and disable any that Flowintel does not need:

```bash
sudo ss -tlnp
```

Only the following ports should be open on a standard single-server installation:

| Port | Service | Purpose |
|------|---------|----------|
| 22 | SSH | Remote administration |
| 80 | NGINX | HTTP (redirects to HTTPS) |
| 443 | NGINX | HTTPS |
| 5432 | PostgreSQL | Database (local only, unless remote) |
| 6379 | Valkey | Session storage (local only) |
| 6666 | MISP modules | Enrichment (local only) |
| 7006 | Flask/Gunicorn | Application (local only, behind NGINX) |

Services listening on `127.0.0.1` are not exposed to the network. If you see anything unexpected, stop and disable it.

## PostgreSQL connection limits
TODO branch for MariaDB

Restrict the maximum number of database connections so the server does not run out of resources under heavy load. Edit the PostgreSQL configuration (replace `16` with your version):

```bash
sudo vi /etc/postgresql/16/main/postgresql.conf
```

Set a reasonable connection limit:

```
max_connections = 50
```

The default of 100 is more than most Flowintel installations need. Lower it to match the expected number of Gunicorn workers plus a small margin for maintenance connections.

Restart PostgreSQL after making changes:

```bash
sudo systemctl restart postgresql
```

## Automatic security updates

Enable unattended security updates so that critical patches are applied automatically:

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

This configures Ubuntu to download and install security updates automatically. Review `/etc/apt/apt.conf.d/50unattended-upgrades` to confirm the settings match your requirements.


# Upgrading Flowintel

This section covers how to upgrade Flowintel to a newer version. Flowintel uses Flask-Migrate (Alembic) for database schema changes, so every upgrade includes a migration step that applies any new or modified tables and columns automatically.

## Before upgrading

1. **Read the release notes**. Check the [Flowintel releases page](https://github.com/flowintel/flowintel/releases) for breaking changes, new dependencies, or manual steps that apply to the version you are upgrading to.

2. **Stop Flowintel**. If Flowintel is running as a systemd service, stop it before making any changes:

   ```bash
   sudo systemctl stop flowintel
   ```

   If you are running Flowintel manually in a terminal, press `Ctrl+C` to stop it.

3. **Back up the database and files**. If you have already set up the automated backup script described in the [backup and restore guide](backup-restore.md), run it manually before proceeding:

   ```bash
   sudo /opt/flowintel/backups/flowintel-backup.sh
   ```

   If you have not yet configured the backup script, create a quick manual backup instead.

   **SQLite (development)**:

   ```bash
   mkdir -p instance/backup
   cp instance/flowintel.sqlite instance/backup/$(date +"%Y_%m_%d").sqlite
   ```

   **PostgreSQL (production)**:
   TODO branch for MariaDB

   ```bash
   mkdir -p instance/backup
   sudo -u postgres pg_dump -F c -b -v flowintel > instance/backup/$(date +"%Y_%m_%d")_pg.sql
   ```

   For full backup and restore procedures, including file system archives and retention, see the [backup and restore guide](backup-restore.md).

4. **Back up the configuration files**. Copy `conf/config.py` and `conf/config_module.py` so you can compare them with the updated defaults after the upgrade:

   ```bash
   cp conf/config.py conf/config.py.pre-upgrade
   cp conf/config_module.py conf/config_module.py.pre-upgrade
   ```

## Upgrade using the update script

Flowintel includes an `update.sh` script that automates most of the upgrade process. It pulls the latest code from Git, backs up the database, runs database migrations, updates taxonomy and galaxy submodules, updates Python dependencies, and refreshes MISP modules.

**Development environment:**

```bash
cd /opt/flowintel/flowintel
bash update.sh
```

**Production environment:**

```bash
cd /opt/flowintel/flowintel
bash update.sh --env production
```

The script performs the following steps:

1. Stops any running Flowintel screen sessions
2. Pulls the latest code with `git pull`
3. Backs up the database (SQLite copy or PostgreSQL dump) into `instance/backup/`
4. Runs `flask db upgrade` to apply pending database migrations
5. Updates the MISP taxonomy and galaxy submodules
6. Updates Python dependencies from `requirements.txt`
7. Reloads taxonomy and galaxy data into the database
8. Starts MISP modules temporarily, then refreshes MISP module metadata in the database

**Note**: The script uses `git pull`, so it always pulls the most recent commits on your current branch (typically `main`).

After the script completes, start Flowintel again:

**Development**
```bash
bash launch.sh -l
```

**Production**
```
sudo systemctl start flowintel
```

Once Flowintel is running, confirm that the new version is active:

```bash
curl -s http://127.0.0.1:7006/api/swagger.json \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"
```

The output should match the version you upgraded to.

## Check for configuration changes

New versions occasionally introduce new settings in the configuration files. After upgrading, compare the default templates with your current configuration:

```bash
diff conf/config.py conf/config.py.default
diff conf/config_module.py conf/config_module.py.default
```

If the defaults contain settings that are not present in your configuration, add them. The release notes normally document new or changed configuration options.

## Database migrations

Flowintel uses Flask-Migrate (which wraps Alembic) to manage database schema changes. Each release that modifies the database includes one or more migration scripts in the `migrations/versions/` directory. The `flask db upgrade` command (called by both `update.sh` and `migrate.sh -u`) applies these migrations in sequence, bringing your database schema up to date with the application code.

At the current moment, in order to fully support MariaDB, we have two branches and two heads of migrations: ```postgres@head``` which embed all the original migration files 
and ```mariadb@head``` which allows to initialize a first install database for MariaDB deployment, starting as of Flowintel v3.4.0 (TODO stamp the actual version).
The related migrations files lives in the original folder ```migrations/versions``` and in ```migrations/versions_mariadb```. Both paths must be actively maintained when
a database model change imply change in a the database schema so that the change is validated to be compatible with both Production backends.

If a migration fails, PostgreSQL leaves the database in its pre-migration state thanks to transactional DDL. SQLite and MariaDB do not support transactional DDL, so a failed migration on a development database may leave the schema in a partially modified state — restore from your backup in that case. Consult the release notes or the issue tracker for guidance.

To check which migration your database is currently on:

```bash
source env/bin/activate
export FLOWINTEL_APP_ENV=production  # or development
flask db current
```

To see which migrations are pending:

```bash
flask db history --rev-range current:head
```

### Migration fails with "column already exists"
TODO Adapt with migration branch

**Symptom**: Running `flask db upgrade` (either directly or through `update.sh`) fails with an error like:

```
sqlalchemy.exc.OperationalError: (psycopg2.errors.DuplicateColumn)
column "version" of relation "case__template" already exists
```

**Cause**: The database schema already contains the column or table that the migration is trying to create, but Alembic's revision tracking has not been updated to reflect this. This can happen when schema changes were applied manually, when a previous upgrade was interrupted after the SQL ran but before Alembic recorded the new revision, or when the database was restored from a backup that was newer than the migration history.

**Solution**: If you have verified that the database schema is already up to date (for example because you are already running the latest version), you can tell Alembic to mark all migrations as applied without executing any SQL:

```bash
source env/bin/activate
export FLOWINTEL_APP_ENV=production  # or development
flask db stamp head
```

This updates Alembic's revision table (`alembic_version`) to point to the latest migration without making any schema changes. After stamping, re-run the upgrade to confirm there are no further pending migrations:

```bash
flask db upgrade
```

**When not to use this**: Only use `flask db stamp head` when you are certain the database schema matches the current code. If you are genuinely behind on migrations (for example upgrading across several versions), stamping will skip those migrations and leave the schema incomplete. In that case, investigate which specific migration is failing and resolve the conflict manually.

### "Error in misp-modules" during upgrade

**Symptom**: During the upgrade (either through `update.sh` or the manual steps), the output includes:

```
[+] Create/Update MISP-Modules...
[-] Error in misp-modules. It might not running.
```

**Cause**: This is a timing issue. The update script starts the MISP modules server in a background `screen` session and then immediately tries to query it. If the server has not finished starting by the time Flowintel queries it, the connection is refused and this error is printed.

**Impact**: The error is **harmless**. Flowintel itself is upgraded correctly; only the MISP module database entries are not refreshed during this particular run. The modules will be registered automatically the next time Flowintel starts and successfully connects to the MISP modules server.

**Solution**: No action is needed. If you want to force a refresh, wait a few seconds for the MISP modules server to finish starting and then run:

```bash
source env/bin/activate
python3 app.py -mm
```

## Rolling back an upgrade

If the upgrade causes problems, you can revert to the previous version. For a full restore (database and files), follow the restore procedures in the [backup and restore guide](backup-restore.md). The summary below covers the essential steps:

1. Stop Flowintel.
2. Restore the database from the backup you created before upgrading (see the [backup and restore guide](backup-restore.md) for detailed instructions).
3. Check out the previous Git tag or commit:

   ```bash
   git checkout tags/3.1.0
   ```

4. Reinstall the previous version's dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Downgrade the database schema to match the previous version (example for Postgres):

   ```bash
   bash migrate.sh --env production -d --migration_branch postgres
   ```

6. Restore your pre-upgrade configuration files if needed.
7. Start Flowintel.


# Uninstalling Flowintel

This section describes how to completely remove Flowintel and all associated services from your system.

**Warning**: This process is destructive and irreversible. All case data, configurations, and user files will be permanently deleted. Make sure you have backups if you need to preserve any data.

> **Note on installation modes**: The steps below are split by mode. A **production** installation (run with `bash install.safe.sh --production`) uses PostgreSQL, NGINX, and systemd services installed under `/opt/flowintel`. A **development** installation (run without `--production`) uses SQLite, runs directly from your working directory, and does not set up any system services beyond Valkey. Follow the section that matches how you originally installed Flowintel.

## Development mode uninstall

A development installation does not create systemd services, NGINX configuration, or a database. The install script does install system packages (Valkey, pandoc, etc.) via apt, but only Valkey runs as a persistent daemon that needs to be explicitly stopped and removed.

1. Stop the running application. If you started it with `bash launch.sh -l`, press **Ctrl+C** in the terminal. If it is running in a `screen` session, kill the screens:

   ```bash
   screen -X -S fcm quit
   screen -X -S misp_mod_flowintel quit
   ```

2. Remove Valkey:

   ```bash
   sudo systemctl stop valkey
   sudo systemctl disable valkey
   sudo apt remove --purge valkey -y
   sudo rm -rf /var/lib/valkey /var/log/valkey
   sudo systemctl daemon-reload
   ```

3. Remove the application directory (the git clone containing the virtual environment and all data):

   ```bash
   # Replace the path below with the actual directory where you cloned Flowintel
   rm -rf /path/to/flowintel
   ```

4. Optionally remove nvm and Node.js (installed in your home directory):

   ```bash
   rm -rf "$HOME/.nvm"
   # Remove the lines nvm added to ~/.bashrc
   ```

That is all that is needed for a development installation. The rest of this section covers **production mode only**.

## Before uninstalling

Create a backup if you need to preserve any data. Refer to the backup and restore documentation for detailed backup procedures. As a quick reference, you can create a PostgreSQL database dump with:

```bash
sudo -u postgres pg_dump flowintel > flowintel_backup_$(date +%Y%m%d).sql
```

To back up uploaded files and configuration as well:

```bash
tar czf flowintel_files_$(date +%Y%m%d).tar.gz \
  /opt/flowintel/flowintel/uploads \
  /opt/flowintel/flowintel/conf/config.py \
  /opt/flowintel/flowintel/.env
```

## Stop all services

Stop all running Flowintel services:

```bash
# Stop Flowintel and its companion services
sudo systemctl stop flowintel flowintel-misp-modules flowintel-notifications
sudo systemctl disable flowintel flowintel-misp-modules flowintel-notifications

# Stop NGINX
sudo systemctl stop nginx

# Stop PostgreSQL
TODO branch for MariaDB ?
sudo systemctl stop postgresql

# Stop Valkey
sudo systemctl stop valkey
```

## Remove Flowintel application

Remove the systemd service files:

```bash
sudo rm /etc/systemd/system/flowintel.service
sudo rm /etc/systemd/system/flowintel-misp-modules.service
sudo rm /etc/systemd/system/flowintel-notifications.service
sudo systemctl daemon-reload
```

Remove the application directory:

```bash
sudo rm -rf /opt/flowintel
```

## Remove NGINX

Remove NGINX and its configuration:

```bash
# Remove NGINX package
sudo apt remove --purge nginx nginx-common nginx-core -y

# Remove configuration files
sudo rm -rf /etc/nginx

# Remove log files
sudo rm -rf /var/log/nginx

# Remove default web root
sudo rm -rf /var/www/html
```

## Remove PostgreSQL
TODO branch for MariaDB ?

Remove PostgreSQL and all database data:

```bash
# Remove PostgreSQL packages
sudo apt remove --purge postgresql postgresql-* -y

# Remove data directory
sudo rm -rf /var/lib/postgresql

# Remove configuration directory
sudo rm -rf /etc/postgresql

# Remove log files
sudo rm -rf /var/log/postgresql
```

## Remove Valkey

Remove Valkey service and files:

```bash
# Stop and disable the service
sudo systemctl stop valkey
sudo systemctl disable valkey

# Remove the package (this removes the binary and the systemd unit file managed by apt)
sudo apt remove --purge valkey -y

# Remove data directory
sudo rm -rf /var/lib/valkey

# Remove log files
sudo rm -rf /var/log/valkey

sudo systemctl daemon-reload
```

## Clean up remaining files

Remove any remaining configuration or temporary files:

```bash
# Clean package cache
sudo apt clean
sudo apt autoremove -y
```

## Verify removal

Check that all services have been removed:

```bash
# Check systemd services
systemctl list-units --all | grep -E 'flowintel|valkey'

# Check for remaining processes
ps aux | grep -E 'flowintel|valkey|nginx|postgres'

# Check for remaining files
ls -la /opt/flowintel 2>/dev/null || echo "Directory removed"
ls -la /etc/nginx 2>/dev/null || echo "NGINX config removed"
ls -la /var/lib/postgresql 2>/dev/null || echo "PostgreSQL data removed"
```

All checks should show that files and services have been removed.

## Final cleanup

Remove any remaining dependencies that are no longer needed:

```bash
sudo apt autoremove -y
sudo apt autoclean
```

The uninstallation is now complete. Your system has been returned to its pre-Flowintel state.