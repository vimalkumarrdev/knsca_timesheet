# Running without Docker (RHEL / EC2)

Alternative to the Docker-based deployment (`docker-compose.yml`) — everything
installed directly on the host: Python venv, MariaDB, gunicorn as a systemd
service, nginx in front. Adjust `/home/ec2-user/knsca_timesheet` throughout to
your actual path/user if different.

## 1. System packages

```bash
sudo dnf install -y python3 python3-devel gcc pkgconfig \
    mariadb-server mariadb-connector-c-devel nginx git
```

## 2. Database

```bash
sudo systemctl enable --now mariadb
sudo mysql_secure_installation

sudo mysql -u root -p
```
```sql
CREATE DATABASE knsca_timesheet CHARACTER SET utf8mb4;
CREATE USER 'knsca'@'localhost' IDENTIFIED BY 'replace-with-a-strong-password';
GRANT ALL PRIVILEGES ON knsca_timesheet.* TO 'knsca'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 3. App setup

```bash
cd ~/knsca_timesheet
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env
```
Set `DB_HOST=localhost` (not `db` — that name only exists in the Docker network), plus `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, and the `DB_*` values matching what you created in step 2.

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 4. Run gunicorn as a systemd service

```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/knsca-timesheet.service
sudo nano /etc/systemd/system/knsca-timesheet.service   # fix paths/user if needed
sudo systemctl daemon-reload
sudo systemctl enable --now knsca-timesheet
sudo systemctl status knsca-timesheet
```

## 5. nginx in front

```bash
sudo cp deploy/nginx-no-docker.conf /etc/nginx/conf.d/knsca-timesheet.conf
sudo nano /etc/nginx/conf.d/knsca-timesheet.conf   # fix paths/domain
sudo nginx -t
sudo systemctl enable --now nginx
```

If SELinux blocks nginx from proxying to gunicorn (`502 Bad Gateway` with an
AVC denial in `sudo journalctl -xe`), allow it:
```bash
sudo setsebool -P httpd_can_network_connect 1
```

## 6. HTTPS

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tscp.knsca.in
```
Certbot edits the nginx config and sets up auto-renewal itself in this mode —
no manual swap needed (unlike the Docker/webroot path).

## Restarting after code changes

```bash
cd ~/knsca_timesheet
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart knsca-timesheet
```
