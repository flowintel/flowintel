# Flowintel encryption guide

## Introduction

This guide describes how to implement encryption at the operating system level for Flowintel installations on Ubuntu Linux. Encryption protects sensitive case data, investigation details, and personal information from unauthorised access, ensuring compliance with GDPR, EU regulations, and law enforcement agency (LEA) security policies.

### Scope and objectives

This guide covers:

- **Data-at-rest encryption**: Protecting stored data on disk using LUKS (Linux Unified Key Setup)
- **Database encryption**: PostgreSQL data directory encryption through filesystem-level encryption
- **Key management**: Secure storage and backup of encryption keys
- **Recovery procedures**: Restoring access to encrypted data after system issues

### Compliance context

Flowintel handles sensitive information in law enforcement and security environments. Encryption at the operating system level ensures:

- **GDPR compliance**: Article 32 requires appropriate technical measures to secure personal data
- **LEA data protection**: Internal policies mandate encryption for investigation data
- **Confidentiality**: Protection against physical theft, unauthorised access, and data breaches
- **Audit requirements**: Demonstrable security controls for compliance reporting

### Encryption approach

This guide focuses on **LUKS encryption** for Linux filesystems. LUKS is one of the most robust and reliable encryption solutions available for Linux systems, offering several advantages over alternative approaches:

- **Industry-leading security**: LUKS uses AES-256-XTS encryption. This encryption has been extensively peer-reviewed and is trusted by security professionals worldwide.
- **Battle-tested reliability**: LUKS has been the standard disk encryption method for Linux distributions for over 15 years. This maturity means edge cases have been discovered and resolved, making it highly dependable for production use.
- **Transparent operation**: Applications (including Flowintel and PostgreSQL) operate normally without modification. There is no need to change application code or workflows.
- **Flexible key management**: LUKS supports different key slots, allowing multiple administrators to have their own passphrases. Keys can be rotated without re-encrypting the entire volume.
- **Comprehensive tooling**: The cryptsetup utility provides straightforward commands for all encryption operations, from initial setup to key rotation and recovery. Ubuntu includes LUKS support out of the box.
- **Disaster recovery**: LUKS header backups enable recovery from corrupted metadata, and multiple key slots ensure access even if one administrator is unavailable.
- **Active maintenance**: LUKS continues to receive updates and security improvements from the Linux kernel community, ensuring long-term support and compatibility.

## Encryption options

You have two main approaches for implementing encryption, depending on whether Ubuntu is already installed or you're performing a fresh installation.

### Option 1: Full disk encryption (recommended for new installations)

**When to use**: Installing Ubuntu from scratch for a dedicated Flowintel server.

**Advantages**:
- Encrypts entire system including swap, temporary files, and all user data
- Configured during installation (no manual setup required)
- Highest security level
- Simplest to manage

**Disadvantages**:
- Requires reinstalling Ubuntu if system is already configured
- Requires passphrase entry at every boot (manual intervention needed)

**Best for**: New Flowintel deployments, dedicated servers, high-security environments.

### Option 2: Partition/volume encryption (for existing systems)

**When to use**: Ubuntu is already installed and you want to add encryption without reinstalling.

**Advantages**:
- No need to reinstall the operating system
- Can encrypt only data directories (/opt/flowintel, PostgreSQL data)
- Flexible approach for existing deployments

**Disadvantages**:
- More complex setup process
- Requires data migration
- Swap and temporary files may remain unencrypted

**Best for**: Existing Ubuntu installations, virtual machines, environments where reinstallation is not practical.

## Option 1: Full disk encryption (new installation)

### Prerequisites

- Ubuntu 22.04 LTS or 24.04 LTS installation media (USB or ISO)
- Physical or remote console access to the server
- Strong passphrase (minimum 20 characters, mix of letters, numbers, symbols)

### Installation procedure

1. **Boot from Ubuntu installation media**

   Insert the USB drive or mount the ISO and boot the server.

2. **Select installation type**

   When prompted for installation type, choose "Try or install Ubuntu" and select the option "Encrypt the LVM group with LUKS".

![LUKS-ubuntu-install.png](LUKS-ubuntu-install.png)

3. **Choose security key**

   Enter a strong encryption passphrase. This passphrase will be required every time the server boots.

   **Passphrase requirements**:
   - Minimum 20 characters
   - Mix of uppercase, lowercase, numbers, and symbols
   - Avoid dictionary words and personal information
   - Use a passphrase manager or document securely

   **Important considerations**:
   - Store this passphrase in a secure location (password manager, sealed envelope in a safe). Without it, all data on the server is permanently inaccessible.
   - Select to create a recovery key when prompted during the installation process. This provides an additional way to unlock the encrypted volume if the primary passphrase is lost.
   - Verify that the keyboard mapping and layout is correct before entering your passphrase. If the keyboard layout is incorrect (for example, QWERTY instead of AZERTY), you may not be able to enter the passphrase correctly at boot time.

4. **Complete installation**

   Continue with the standard Ubuntu installation process (timezone, user account, etc.).

5. **First boot**

   At boot, the system will prompt for the encryption passphrase. Enter it to unlock the disk and start the operating system.

   **Recovery key**: If you enabled the recovery key during installation, it will be saved to `/var/log/installer/recovery-key.txt`. Copy this file to a safe location immediately:

   ```bash
   sudo cp /var/log/installer/recovery-key.txt ~/recovery-key.txt
   sudo chmod 400 ~/recovery-key.txt
   ```

   Store the recovery key securely (encrypted USB drive, password manager, or secure storage) and remove it from the server once backed up.

### Post-installation configuration

After installing Ubuntu with full disk encryption:

1. **Verify encryption status**

   Check that the root filesystem is encrypted:

   ```bash
   lsblk -o NAME,FSTYPE,MOUNTPOINT
   ```

   You should see `crypto_LUKS` as the filesystem type for the encrypted volume:

   ```
   NAME                        FSTYPE      MOUNTPOINT
   sda
   ├─sda1
   ├─sda2                      ext4        /boot
   └─sda3                      crypto_LUKS
     └─dm_crypt-0              LVM2_member
       └─ubuntu--vg-ubuntu--lv ext4        /
   sr0
   ```

   Check encryption details:

   ```bash
   sudo cryptsetup luksDump /dev/sda3
   ```

   Replace `/dev/sda3` with the actual encrypted partition from your system. For full disk encryption, this is typically on the primary system disk.

3. **Continue with Flowintel installation**

   Proceed with the standard Flowintel installation as documented in the installation manual. All Flowintel data will automatically be encrypted because the entire filesystem is encrypted.

## Option 2: Partition encryption (existing system)

### Overview

This approach encrypts a dedicated partition or logical volume where Flowintel data will be stored. The operating system remains on an unencrypted partition.

### Planning

This guide demonstrates creating a dedicated encrypted volume mounted at `/opt/flowintel`. This single encrypted partition will contain:

- Flowintel application installation
- User uploads and attachments
- PostgreSQL data directory (`/opt/flowintel/database`)
- Configuration files
- Logs and temporary files

By encrypting `/opt/flowintel`, all Flowintel components are protected with a single encrypted volume.

**LVM and encryption**: This guide uses LUKS directly on a disk partition. However, you can combine LUKS with LVM for additional flexibility. The recommended approach is **LUKS on LVM** (encrypt the LVM logical volume), which allows you to:
- Expand storage by adding physical disks to the volume group
- Take LVM snapshots for backups before encryption
- Manage multiple encrypted logical volumes within one volume group

If you need LVM flexibility, follow this guide to create the encrypted volume, but use an LVM logical volume (like `/dev/flowintel-vg/flowintel-lv`) instead of a raw disk partition. The commands remain the same, just replace `/dev/sdb` with your LVM logical volume path.

### Prerequisites

- Existing Ubuntu 22.04 LTS or 24.04 LTS installation
- Unallocated disk space (or a new disk/volume) for the encrypted partition
- Backup of existing Flowintel data (if already installed)
- Root access

### Step 1: Create encrypted partition

1. **Identify available disk space**

   Before creating an encrypted partition, you need to locate a suitable disk or unallocated space. Use these commands to list all available storage devices:

   ```bash
   sudo fdisk -l
   lsblk
   ```

   Example output:

   ```
   NAME                      MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
   sda                         8:0    0   20G  0 disk 
   ├─sda1                      8:1    0    1M  0 part 
   ├─sda2                      8:2    0  1.8G  0 part /boot
   └─sda3                      8:3    0 18.2G  0 part 
     └─ubuntu--vg-ubuntu--lv 252:0    0 18.2G  0 lvm  /
   sdb                         8:16   0   10G  0 disk 
   sr0                        11:0    1  3.1G  0 rom  
   ```

   Look for unallocated space or a new disk. In this example, `/dev/sdb` is a new 10GB disk that can be used for the encrypted partition.

   **Note**: If you want to use LVM for easier storage expansion, create your LVM setup first (physical volume, volume group, and logical volume as described in the installation manual), then proceed with encrypting the logical volume. For example, you would encrypt `/dev/flowintel-vg/flowintel-lv` instead of `/dev/sdb`.

2. **Encrypt the disk with LUKS**

   This step initialises LUKS encryption on the disk. The luksFormat command creates the LUKS header and sets up the encryption layer. **Warning**: This will erase all existing data on the disk.

   ```bash
   sudo cryptsetup luksFormat /dev/sdb
   ```

   You will be prompted to confirm (type `YES` in uppercase) and enter a passphrase.

   **Passphrase requirements**: Same as for full disk encryption (minimum 20 characters, complex).

3. **Open the encrypted disk**

   Opening the encrypted disk unlocks it using your passphrase and creates a device mapper entry. This mapped device (`/dev/mapper/flowintel_encrypted`) is what you will use for filesystem operations.

   ```bash
   sudo cryptsetup luksOpen /dev/sdb flowintel_encrypted
   ```

   Enter the passphrase. This creates a mapped device at `/dev/mapper/flowintel_encrypted`:

   ```bash
   ls -l /dev/mapper/flowintel_encrypted
   ```

   Expected output:

   ```
   lrwxrwxrwx 1 root root 7 Jan 31 16:43 /dev/mapper/flowintel_encrypted -> ../dm-1
   ```

4. **Create filesystem**

   Now that the encrypted device is unlocked, create an ext4 filesystem on it. This is a standard Linux filesystem that will store all Flowintel data.

   ```bash
   sudo mkfs.ext4 /dev/mapper/flowintel_encrypted
   ```

5. **Create mount point**

   Create the directory where the encrypted volume will be mounted. This is where all Flowintel components will be installed.

   ```bash
   sudo mkdir -p /opt/flowintel
   ```

6. **Mount the encrypted volume**

   Mount the encrypted filesystem to make it accessible. At this point, any files you write to `/opt/flowintel` will be encrypted automatically.

   ```bash
   sudo mount /dev/mapper/flowintel_encrypted /opt/flowintel
   ```

### Step 2: Configure automatic mounting

To mount the encrypted volume at boot:

1. **Create key file** (optional, for automatic unlock)

   A key file allows the system to unlock the encrypted volume automatically at boot without manual passphrase entry. This file contains random data that serves as an additional authentication method.

   ```bash
   sudo dd if=/dev/urandom of=/root/flowintel-keyfile bs=1024 count=4
   sudo chmod 0400 /root/flowintel-keyfile
   ```

2. **Add key file to LUKS**

   Register the key file with LUKS as an additional authentication method. LUKS supports multiple keys (up to 8 slots), so this does not remove your passphrase - it adds an alternative way to unlock the volume.

   ```bash
   sudo cryptsetup luksAddKey /dev/sdb /root/flowintel-keyfile
   ```

   Enter the existing passphrase when prompted.

3. **Update /etc/crypttab**

   The crypttab file tells the system which encrypted devices to unlock at boot and which key files to use. Adding an entry here ensures the volume is unlocked automatically during the boot process.

   ```bash
   sudo vi /etc/crypttab
   ```

   Add:

   ```
   flowintel_encrypted /dev/sdb /root/flowintel-keyfile luks
   ```

4. **Update /etc/fstab**

   The fstab file defines which filesystems to mount at boot. Adding the encrypted volume here ensures it is mounted automatically after being unlocked by crypttab.

   Edit fstab:

   ```bash
   sudo vi /etc/fstab
   ```

   Add:

   ```
   /dev/mapper/flowintel_encrypted /opt/flowintel ext4 defaults 0 2
   ```

5. **Test automatic unlock and mount**

   The configuration you have created is processed during system boot. The most reliable way to test it is to reboot and verify that the encrypted volume is unlocked and mounted without manual intervention.

   The crypttab configuration is processed during boot. Test by rebooting the system:

   ```bash
   sudo reboot
   ```

   After the system comes back up, verify that `/opt/flowintel` is automatically mounted:

   ```bash
   df -h | grep flowintel
   lsblk | grep flowintel
   ```

   Expected output:

   ```
   └─flowintel_encrypted     252:1    0   10G  0 crypt /opt/flowintel
   ```

   You should see the encrypted volume mounted at `/opt/flowintel` without requiring manual intervention.

### Continue with Flowintel installation

Your encrypted volume is now configured and ready. All data stored in `/opt/flowintel` will be encrypted at rest.

**Return to the [installation manual](installation-manual.md#database-postgresql)** to continue with PostgreSQL and Flowintel installation. The installation manual will guide you through:
- Installing PostgreSQL with the data directory on the encrypted volume
- Installing Flowintel on the encrypted volume
- Configuring all services

When you return to the installation manual, all Flowintel components (application files, database, uploads, logs) will automatically be protected by encryption because they will be stored on the encrypted `/opt/flowintel` volume.

## Encryption key management

### Key backup

Losing the encryption key means permanent data loss. Create secure backups:

1. **Backup LUKS header**

   The LUKS header contains key slots and metadata. Back it up:

   ```bash
   sudo cryptsetup luksHeaderBackup /dev/sdb --header-backup-file /root/luks-header-backup-sdb.img
   ```

   Store this file securely (encrypted USB drive, password manager, secure storage).

2. **Document passphrase**

   Store the encryption passphrase in:
   - Password manager (recommended)
   - Sealed envelope in a physical safe
   - Secure documentation system

   **Never** store the passphrase on the same server.

3. **Test recovery**

   Periodically verify you can decrypt the volume with your backup passphrase.

### Key rotation

Change encryption passphrases periodically (recommended every 12 months):

1. **Add new passphrase**

   ```bash
   sudo cryptsetup luksAddKey /dev/sdb
   ```

   Enter existing passphrase, then enter new passphrase twice.

2. **Remove old passphrase**

   ```bash
   sudo cryptsetup luksRemoveKey /dev/sdb
   ```

   Enter the old passphrase to remove it.

3. **Update documentation**

   Update your password manager or secure storage with the new passphrase.

## Recovery procedures

### Recovering from lost passphrase

If the passphrase is lost and no backup exists, **data is unrecoverable**. This is by design for security.

If you have a LUKS header backup:

1. **Restore LUKS header**

   ```bash
   sudo cryptsetup luksHeaderRestore /dev/sdb --header-backup-file /root/luks-header-backup-sdb.img
   ```

2. **Attempt to unlock with backup passphrase**

   ```bash
   sudo cryptsetup luksOpen /dev/sdb flowintel_encrypted
   ```

### Recovering from corrupted LUKS header

If the LUKS header is corrupted but you have a backup:

```bash
sudo cryptsetup luksHeaderRestore /dev/sdb --header-backup-file /root/luks-header-backup-sdb.img
sudo cryptsetup luksOpen /dev/sdb flowintel_encrypted
sudo mount /dev/mapper/flowintel_encrypted /opt/flowintel
```

### Emergency access

In an emergency where the system won't boot but the encrypted volume is intact:

1. **Boot from Ubuntu live USB**

2. **Install cryptsetup** (if not present)

   ```bash
   sudo apt update
   sudo apt install cryptsetup
   ```

3. **Unlock the volume**

   ```bash
   sudo cryptsetup luksOpen /dev/sdb flowintel_encrypted
   ```

4. **Mount the volume**

   ```bash
   sudo mkdir /mnt/recovery
   sudo mount /dev/mapper/flowintel_encrypted /mnt/recovery
   ```

5. **Access data**

   You can now copy data from `/mnt/recovery` or repair the system.

## Compliance verification

### Documenting encryption

For compliance audits, document:

1. **Encryption method**: LUKS with AES-256-XTS
2. **Encrypted components**: Flowintel application directory, PostgreSQL data directory
3. **Key management**: Passphrase storage, backup procedures, rotation schedule
4. **Access controls**: Who has access to encryption keys

### Verification commands

Provide these commands to auditors to verify encryption:

```bash
# Show encrypted volumes
sudo cryptsetup status flowintel_encrypted

# Show encryption details
sudo cryptsetup luksDump /dev/sdb

# Verify mount points
lsblk -o NAME,FSTYPE,MOUNTPOINT | grep -E 'crypto_LUKS|flowintel'

# Confirm PostgreSQL data location
sudo -u postgres psql -c "SHOW data_directory;"
```

### Compliance checklist

- [ ] Encryption implemented using LUKS with AES-256
- [ ] All Flowintel data stored on encrypted volume
- [ ] PostgreSQL data directory on encrypted volume
- [ ] Encryption passphrase meets complexity requirements (minimum 20 characters)
- [ ] Passphrase stored securely (password manager or secure storage)
- [ ] LUKS header backup created and stored securely
- [ ] Key rotation schedule defined (recommended annually)
- [ ] Access controls documented (who has encryption keys)
- [ ] Recovery procedures tested
- [ ] Encryption status documented for audits

## Best practices summary

1. **Use full disk encryption for new installations** whenever possible
2. **Store encryption keys securely** separate from the server
3. **Create LUKS header backups** immediately after encryption setup
4. **Test recovery procedures** before going into production
5. **Rotate encryption keys annually** or per organisational policy
6. **Document everything** for compliance and operational continuity
7. **Verify AES-NI support** for optimal performance
8. **Monitor system performance** after implementing encryption
9. **Train administrators** on recovery procedures
10. **Regular backups** of encrypted data (encryption does not replace backups)

## Support and troubleshooting

### Common issues

**Issue**: System won't boot after enabling encryption

**Solution**: Boot from live USB, unlock volume manually, check `/etc/crypttab` and `/etc/fstab` configuration.

**Issue**: Performance degradation after enabling encryption

**Solution**: Verify AES-NI is enabled, check CPU supports hardware acceleration, consider SSD storage.

**Issue**: PostgreSQL won't start after moving data directory

**Solution**: Check permissions on new directory (`chmod 700`, owned by `postgres:postgres`), verify `postgresql.conf` points to correct path, check SELinux/AppArmor if enabled.

**Issue**: Forgot encryption passphrase

**Solution**: If no backup exists, data is unrecoverable. Restore from LUKS header backup if available and passphrase is documented.

For additional support, consult the Ubuntu documentation on LUKS encryption or contact your system administrator.
