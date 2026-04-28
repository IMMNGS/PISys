# Patient Information System on Synology NAS — Setup Guide

This guide walks you through deploying the HA (Patient Information System) on a Synology NAS using Docker and Container Manager.

## Prerequisites

- Synology NAS with DSM 7.x (DSM 6.x may differ; check Synology docs)
- Container Manager installed from Package Center
- SSH access enabled (Control Panel → Terminal & SNMP → Enable SSH)
- At least 20 GB free space for database and application
- Basic command-line familiarity

## Before You Start

### 1. Generate Secure Credentials

Open a terminal on your Mac and generate secrets for the `.env` file:

```bash
# Generate Flask SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Generate MySQL password
python3 -c "import secrets; print('MYSQL_PASSWORD=' + secrets.token_hex(16))"

# Generate MySQL root password
python3 -c "import secrets; print('MYSQL_ROOT_PASSWORD=' + secrets.token_hex(16))"
```

Save these values—you'll need them in the `.env` file.

### 2. SSH into Your Synology NAS

```bash
ssh admin@192.168.1.100  # Replace with your NAS IP
# Or: ssh admin@your-nas-hostname
```

## Setup Steps

### Step 1: Create Directory Structure

```bash
# Create base directory for the project
sudo mkdir -p /volume1/docker/ha
sudo mkdir -p /volume1/docker/ha/mysql
sudo mkdir -p /volume1/docker/ha/app
sudo mkdir -p /volume1/docker/ha/env

# Set permissions (replace 'admin' with your Synology username if different)
sudo chown -R admin:users /volume1/docker/ha
sudo chmod -R 755 /volume1/docker/ha
```

### Step 2: Copy Application Files to NAS

From your Mac, copy the entire HA repository to the NAS:

```bash
# From /Users/hi/Documents/code/HA/
scp -r ./* admin@192.168.1.100:/volume1/docker/ha/app/

# Or use rsync (faster for repeated syncs)
rsync -av --exclude='.venv' --exclude='node_modules' --exclude='.git' \
  ./ admin@192.168.1.100:/volume1/docker/ha/app/
```

### Step 3: Create `.env` File

SSH into the NAS and create the `.env` file:

```bash
ssh admin@192.168.1.100

# Create .env from the example
cp /volume1/docker/ha/app/.env.synology.example /volume1/docker/ha/.env

# Edit the .env file
vi /volume1/docker/ha/.env
```

**Update these required fields:**

```env
# Replace with values from Step 1
SECRET_KEY=<your-generated-secret-key>
MYSQL_PASSWORD=<your-generated-mysql-password>
MYSQL_ROOT_PASSWORD=<your-generated-root-password>

# Optional: customize these
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me_in_production

# If you used a different timezone
TZ=America/Chicago
```

Exit the editor (`:wq` for vi).

### Step 4: Verify File Permissions

```bash
# Make sure the .env file is readable by Docker
chmod 644 /volume1/docker/ha/.env

# Verify structure
ls -la /volume1/docker/ha/
# Expected output:
# drwxr-xr-x ... mysql
# drwxr-xr-x ... app
# -rw-r--r-- ... .env
```

### Step 5: Start Containers via Container Manager (GUI)

1. Open your browser and go to your Synology NAS:

   ```
   https://192.168.1.100:5000  (or your NAS hostname)
   ```

2. Login to DSM.

3. Open **Package Center** and search for **Container Manager** (or Docker if on older DSM versions). Install if needed.

4. Open **Container Manager**.

5. Navigate to **Projects** (left sidebar).

6. Click **Create** → **Create with docker compose file**.

7. Select **Upload from file** and upload `docker-compose.yml` from your Mac:

   ```bash
   # On your Mac, in the HA directory:
   scp docker-compose.yml admin@192.168.1.100:/volume1/docker/ha/
   ```

8. Or copy/paste the contents of `docker-compose.yml` directly into the text area.

9. Click **Next**.

10. For **Project Name**, enter: `ha-patient-info`

11. Click **Create**.

12. Wait for the build and startup to complete (2-5 minutes). Check **Logs** for progress.

### Step 6: Start Containers via CLI (Alternative)

If you prefer the command line:

```bash
ssh admin@192.168.1.100

cd /volume1/docker/ha

# Start the containers
sudo docker compose up -d

# Check status
sudo docker compose ps

# View logs
sudo docker compose logs -f app
```

### Step 7: Verify Startup

Check that both containers are running:

```bash
sudo docker compose ps
```

**Expected output:**

```
NAME       STATUS          PORTS
ha-db      Up (healthy)    3306/tcp
ha-app     Up (healthy)    0.0.0.0:18000->8000/tcp
```

View application logs:

```bash
sudo docker compose logs app
```

Look for:

```
Starting Patient Information System (production)
...
Listening at: 0.0.0.0:8000
```

### Step 8: Test Local Access

From your Mac, test the application on your NAS:

```bash
curl -v http://192.168.1.100:18000/
# Should return HTML (React app)
```

Or open in browser:

```
http://192.168.1.100:18000/
```

Login with:

- Username: `admin`
- Password: (whatever you set in `ADMIN_PASSWORD`)

## Step 9: Set Up HTTPS Reverse Proxy (Recommended)

For external/secure access, use Synology's reverse proxy:

1. In DSM, go to **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**.

2. Click **Create**.

3. Fill in:
   | Field | Value |
   |-------|-------|
   | Description | HA Patient Info |
   | Protocol (source) | HTTPS |
   | Hostname (source) | ha.yourdomain.com |
   | Port (source) | 443 |
   | Protocol (destination) | HTTP |
   | Hostname (destination) | localhost |
   | Port (destination) | 18000 |

4. Click **OK**.

5. Go to **Control Panel** → **Security** → **Certificate** to install a Let's Encrypt certificate for `ha.yourdomain.com`.

6. Test external access:
   ```
   https://ha.yourdomain.com
   ```

## Backup & Maintenance

### Automatic Backup (Hyper Backup)

1. In DSM, open **Hyper Backup**.

2. Create a new backup task:
   - **Backup source**: Select folders `/volume1/docker/ha/mysql` and `/volume1/docker/ha/app/data`.
   - **Backup destination**: External drive or cloud storage.
   - **Schedule**: Daily at 3 AM.

3. This ensures your database and uploaded VCF files are backed up.

### Manual Database Backup

```bash
ssh admin@192.168.1.100

cd /volume1/docker/ha

# Backup MySQL database
sudo docker compose exec db mysqldump \
  -u root -p${MYSQL_ROOT_PASSWORD} \
  --all-databases > /volume1/docker/ha/backup_$(date +%Y%m%d).sql
```

### Update Application Code

When you have new code:

```bash
ssh admin@192.168.1.100

cd /volume1/docker/ha/app

# Pull the latest code
git pull origin main

# Rebuild the Docker image
sudo docker compose build --no-cache

# Restart containers
sudo docker compose up -d

# Check logs
sudo docker compose logs -f app
```

## Troubleshooting

### 1. Containers Won't Start

**Problem**: Containers are stuck in "unhealthy" state.

**Solution**:

```bash
# Check logs
sudo docker compose logs app

# Common issues:
# - MySQL port already in use (change APP_PORT in .env to a different value)
# - Insufficient disk space (check: df -h /volume1)
# - Secret keys not set in .env (check: cat /volume1/docker/ha/.env)
```

### 2. Database Connection Errors

**Problem**: App logs show "Can't connect to MySQL server".

**Solution**:

```bash
# Verify MySQL is healthy
sudo docker compose logs db

# Check credentials in .env match what's in docker-compose
# Restart both services
sudo docker compose restart db
sudo docker compose restart app
```

### 3. Out of Disk Space

**Problem**: Docker containers can't write to disk.

**Solution**:

```bash
# Check available space
df -h /volume1

# Clean up old Docker images
sudo docker image prune -a

# Reduce MySQL data retention if needed
# Or expand storage on NAS (add drives)
```

### 4. Slow Uploads

**Problem**: Large VCF files are timing out.

**Solution**:

- Increase `GUNICORN_TIMEOUT` in `.env` (e.g., 300 for 5 minutes).
- Increase `MAX_UPLOAD_MB` if files are larger.
- Restart containers: `sudo docker compose restart app`

### 5. Access Denied - Permission Errors

**Problem**: App can't write to `/app/data`.

**Solution**:

```bash
# Fix permissions
sudo chown -R 1000:1000 /volume1/docker/ha/app/data
sudo chmod -R 755 /volume1/docker/ha/app/data
```

## Performance Tuning

### For Synology with 4 CPU Cores + 8 GB RAM (Recommended):

```env
GUNICORN_WORKERS=8          # (4 cores * 2) + 1, capped at 8
GUNICORN_THREADS=4          # Keep threads moderate
GUNICORN_TIMEOUT=120        # Generous for large uploads
MAX_UPLOAD_MB=5000          # Adjust based on available RAM/disk
```

### For Synology with 2 CPU Cores + 4 GB RAM (Entry Level):

```env
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=180        # More lenient
MAX_UPLOAD_MB=2000          # Restrict upload size
```

## Additional Resources

- Synology Container Manager docs: https://kb.synology.com/en-global/DSM/help/ContainerManager
- Docker Compose reference: https://docs.docker.com/compose/
- Let's Encrypt on Synology: https://kb.synology.com/en-global/DSM/help/DSM/Tutorial/lets_encrypt

## Support & Debugging

If containers fail to start or run, save logs for debugging:

```bash
ssh admin@192.168.1.100

cd /volume1/docker/ha

# Full diagnostic dump
sudo docker compose logs > /volume1/docker/ha/debug_$(date +%Y%m%d_%H%M%S).log

# Copy back to your Mac for analysis
scp admin@192.168.1.100:/volume1/docker/ha/debug_*.log ~/Downloads/
```

---

**Happy deploying!** Once confirmed running, the Patient Information System will be accessible at `http://<nas-ip>:18000` (or `https://ha.yourdomain.com` if HTTPS reverse proxy is configured).
