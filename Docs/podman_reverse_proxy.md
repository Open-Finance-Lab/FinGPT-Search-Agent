# Podman Reverse Proxy Deployment (Caddy + FinGPT Backend)

This runbook extends the production setup guide and shows how to run the FinGPT backend together with a Caddy reverse proxy inside a Podman pod. The goal is to expose HTTPS to beta testers while keeping the backend container unchanged (still built with the existing `Main/backend/Dockerfile`).

## 1. Prerequisites

- Registered domain pointing to the host public IP (for example `fingpt.example.com`).
- A Linux VM with Podman and systemd (Fedora, CentOS Stream, RHEL, Ubuntu).
- Non-root deploy user with linger enabled so rootless services survive logout:
  ```bash
  sudo loginctl enable-linger deploy
  ```
- Podman socket initialized once under that user:
  ```bash
  podman info
  ```
- Production environment file stored outside the repo, e.g. `/opt/fingpt/.env.production` (follow `Docs/production_setup.md` to populate it).

## 2. Directory Layout on the Host

```bash
sudo mkdir -p /opt/fingpt/{config,data,logs}
sudo chown -R deploy:deploy /opt/fingpt

cp Deploy/podman/Caddyfile.example /opt/fingpt/config/Caddyfile
# Edit the copy: change domain, email, origins, etc.
nano /opt/fingpt/config/Caddyfile
```

Keep the production environment file alongside the configuration:

```bash
cp Main/backend/.env.production.example /opt/fingpt/.env.production
# Fill in strong secrets and provider keys (do not commit this file).
chmod 600 /opt/fingpt/.env.production
```

## 3. Create the Pod and Containers

```bash
podman pod create \
  --name fingpt \
  --publish 80:80 \
  --publish 443:443
```

Run the backend container inside the pod:

```bash
podman run -d \
  --name fingpt-api \
  --pod fingpt \
  --restart unless-stopped \
  --env-file /opt/fingpt/.env.production \
  --volume /opt/fingpt/logs:/app/logs \
  ghcr.io/your-org/fingpt-api:latest
```

Start Caddy as the reverse proxy:

```bash
podman run -d \
  --name fingpt-proxy \
  --pod fingpt \
  --restart unless-stopped \
  --volume /opt/fingpt/config/Caddyfile:/etc/caddy/Caddyfile:ro \
  --volume /opt/fingpt/data/caddy:/data \
  --volume /opt/fingpt/data/caddy-config:/config \
  caddy:2
```

Caddy reads the mounted `Caddyfile`, negotiates TLS certificates via Let's Encrypt, and forwards traffic to the `fingpt-api` container inside the pod network.

## 4. Enable HTTPS-Specific Django Flags

Once TLS is active, update `/opt/fingpt/.env.production`:

```
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
```

Then restart only the backend container (Caddy continues serving existing connections):

```bash
podman restart fingpt-api
```

To confirm, inspect the runtime environment:
```bash
podman exec fingpt-api env | grep SECURE_
```

## 5. Converting to systemd Units

Generate units for both containers so they respawn on boot:

```bash
podman generate systemd \
  --name fingpt-api \
  --files --new --restart-policy=always

podman generate systemd \
  --name fingpt-proxy \
  --files --new --restart-policy=always
```

Copy the resulting `.service` files to `~/.config/systemd/user/`, reload, and enable:

```bash
mkdir -p ~/.config/systemd/user
mv container-fingpt-api.service ~/.config/systemd/user/
mv container-fingpt-proxy.service ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now container-fingpt-api.service
systemctl --user enable --now container-fingpt-proxy.service
```

If the host should start them automatically after reboot, enable the lingering user service (`loginctl enable-linger deploy`) and optionally create a dependency on the pod itself (`podman generate systemd --name fingpt --files --new`).

## 6. Health Checks and Monitoring

- Endpoint: `https://fingpt.example.com/health/` (mirrors the container health probe).
- Logs:
  ```bash
  podman logs -f fingpt-api
  podman logs -f fingpt-proxy
  ```
- Static assets are collected by `entrypoint.sh` whenever `DJANGO_SETTINGS_MODULE=django_config.settings_prod`. Ensure `RUN_COLLECTSTATIC=1` remains set in the env file unless you move the step into CI.
- For automated updates, label the backend container before running `podman auto-update`:
  ```bash
  podman run ... \
    --label io.containers.autoupdate=registry \
    ghcr.io/your-org/fingpt-api:latest
  ```

## 7. Smoke Testing

Run simple checks after deployment:

```bash
curl -I https://fingpt.example.com/health/

curl -H "Origin: https://finance.yahoo.com" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Authorization" \
     -X OPTIONS \
     https://fingpt.example.com/api/get_available_models/
```

Expect a `200` preflight with the `Access-Control-Allow-Origin` header matching the request origin. Any `307`/`308` redirects usually indicate `SECURE_SSL_REDIRECT` flipped on before TLS was ready.

## 8. Updating the Image

1. Build locally with Podman using the repo Dockerfile.
2. Tag and push to your registry (`ghcr.io/your-org/fingpt-api:latest`).
3. On the host:
   ```bash
   podman pull ghcr.io/your-org/fingpt-api:latest
   podman stop fingpt-api
   podman rm fingpt-api
   podman run ... ghcr.io/your-org/fingpt-api:latest
   ```
   (or rely on `podman auto-update` if labels are set).

Document the tag you deploy so rollbacks simply mean re-running `podman run` with the previous version.

---

With this setup you can invite beta testers to the hosted backend without requiring local installs, while keeping your existing Podman build pipeline and production configuration.
