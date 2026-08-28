# TLS setup (Let's Encrypt via certbot)

`nginx/nginx.conf` ships in HTTP-only "bootstrap" mode so it can start before a
certificate exists (Let's Encrypt needs to reach your server over plain HTTP
first, to prove you control the domain). Do this once, after DNS is pointed
at your VPS and `docker compose up -d` is running:

1. Obtain the certificate (replace the domain):

   ```
   docker run --rm \
     -v certbot_www:/var/www/certbot \
     -v certbot_certs:/etc/letsencrypt \
     certbot/certbot certonly --webroot \
     -w /var/www/certbot \
     -d tscp.knsca.in \
     --email you@knsca.in --agree-tos --no-eff-email
   ```

   This works because `nginx.conf` already proxies `/.well-known/acme-challenge/`
   to the same `certbot_www` volume certbot writes into.

2. Edit `nginx/nginx.conf`: delete the single bootstrap `server {}` block at the
   top and uncomment the HTTPS pair at the bottom, replacing
   `your-domain.example` with your real domain in both places.

3. Reload nginx: `docker compose exec nginx nginx -s reload`

4. Flip the HTTPS settings on in your real `.env`:

   ```
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   SECURE_HSTS_SECONDS=31536000
   SECURE_HSTS_INCLUDE_SUBDOMAINS=True
   CSRF_TRUSTED_ORIGINS=https://tscp.knsca.in
   SITE_URL=https://tscp.knsca.in
   ```

   Then `docker compose up -d` again to pick up the new env values.

## Renewal

Let's Encrypt certs expire every 90 days. Add a cron job on the host running:

```
docker run --rm -v certbot_www:/var/www/certbot -v certbot_certs:/etc/letsencrypt \
  certbot/certbot renew --webroot -w /var/www/certbot -q \
  && docker compose exec nginx nginx -s reload
```
