# Deployment Automation

The `Backend CI and Deploy` workflow (`.github/workflows/backend-deploy.yml`) turns pushes to `main` into a tested container image plus an optional restart of the Fedora droplet (`fedora-agentic-finsearch-beta-1`). The flow:

1. Checks out this repo and installs Python `3.12` with `uv`.
2. Runs `uv sync --frozen`, `uv run python manage.py check`, and `uv run python manage.py test` inside `Main/backend`.
3. Builds the backend container with the Dockerfile in `Main/backend/` and pushes three tags to GHCR:
   - `ghcr.io/<owner>/<repo>-backend:${GITHUB_SHA}`
   - `ghcr.io/<owner>/<repo>-backend:main`
   - `ghcr.io/<owner>/<repo>-backend:latest`
4. Uses SSH to reach `deploy@agenticfinsearch.org`, pulls the `:main` tag with `podman`, and restarts the user-level systemd unit `fingpt-api`.

## Required GitHub secrets

| Secret | Description |
| --- | --- |
| `DEPLOY_SSH_KEY` | Private key that matches `/home/deploy/.ssh/authorized_keys`. The workflow uses it to SSH into the droplet. |
| `GHCR_READ_TOKEN` | GitHub Personal Access Token with the `read:packages` scope. Needed so the droplet can `podman login ghcr.io …` during deploy. |

`GITHUB_TOKEN` is injected automatically by Actions for the GHCR push and does **not** need to be created manually.

## Droplet prerequisites

- Systemd user services must be enabled (`loginctl enable-linger deploy`) so `systemctl --user restart fingpt-api` works from non-interactive SSH sessions.
- The `fingpt-api` unit should reference the GHCR image (`ghcr.io/<owner>/<repo>-backend:main`) instead of a locally loaded tarball. A simple `podman run --rm ghcr.io/...` wrapper script is sufficient.
- Ensure `/home/deploy/.config/containers` allows logins to GHCR (the workflow already executes `podman login`, so no persistent config is strictly required).
- Confirm that `.env` / `.env.production` and the Caddy config are already on the droplet; the workflow only handles code + container restarts.

After creating the secrets above, push to `main` (or use the manual `workflow_dispatch`) to trigger the pipeline. Watch the workflow logs for the deploy step; it will be skipped automatically if either secret is missing.
