# NOTICE: Möbius template

## Software deployed

| Component | Source | License | How it is used |
|---|---|---|---|
| Möbius | https://github.com/mobius-os/mobius, commit `c1e525f3239b73a0b899d7e7879a7fefce95c43c` (2026-10-19); image `ghcr.io/mobius-os/mobius:sha-c1e525f3239b73a0b899d7e7879a7fefce95c43c@sha256:e7b6da2a45ee2869e6b2e53bf532b7e5544adbf6aa5ad07439f70eefd3dcfbf2` | MIT License, Copyright (c) 2025 Hamza Merzić (repository `LICENSE`) | Used unmodified as the base image. The only change to the image's file system is that the pip-generated `uvicorn` console script is moved to `/opt/mobius-railway/uvicorn-real` and replaced by the template's shim. Third-party software inside the image (Debian packages, Python and npm dependencies, Claude Code and Codex CLIs, Chrome for Testing, tectonic, GitHub CLI) keeps its own licenses and terms. |

Möbius and the Möbius logo belong to their owners. The listing icon is upstream's `frontend/public/moebius.png`, loaded from the upstream repository at the pinned commit. This is a community template and is not affiliated with or endorsed by the Möbius project or mobius.you. Claude Code is a product of Anthropic and Codex of OpenAI; using them requires the owner's own accounts and is subject to their terms.

## Template files

All template files (TEMPLATE.md, template.json, README.md, this NOTICE, `services/mobius/Dockerfile`, `railway/railway-entrypoint.sh`, `railway/uvicorn-shim.sh`, `railway/owner_bootstrap.py`) were written for this package. No upstream file or text was copied into them.

`owner_bootstrap.py` calls upstream's own functions at runtime (`app.main._init_db`, `app.models.Owner`, `app.auth.hash_password`, `verify_password`, `write_service_token`, `app.database.SessionLocal`, `app.config.get_settings`) from the Möbius code inside the running container; it mirrors the behaviour of upstream's `POST /api/auth/setup` route and `backend/scripts/update-owner-credentials.py` without reproducing their code.

MIT License text: https://github.com/mobius-os/mobius/blob/c1e525f3239b73a0b899d7e7879a7fefce95c43c/LICENSE

## Upstream files checked (commit `c1e525f`, checked 2026-10-20)

- Deployment: `Dockerfile`, `railway.toml`, `docker-compose.yml`, `docker-compose.prod.yml`, `Caddyfile`, `.env.example`, `.github/workflows/main-image.yml`, `protected-files.txt`, `deployment/`
- Boot: `backend/scripts/entrypoint.sh`, `backend/scripts/agent_sudo.sh`, `backend/scripts/init_data_repo.py`, `backend/scripts/update-owner-credentials.py`, `backend/runtime/served_runtime_launcher.py`
- Backend: `app/config.py`, `app/main.py` (health and readiness routes, security-header and service-gateway middleware, SPA fallback, rate limiter), `app/startup.py`, `app/bootstrap.py`, `app/database.py`, `app/models.py`, `app/auth.py`, `app/routes/auth.py`, `app/deps.py`, `app/routes/local_services.py`, `app/routes/public_apps.py`, `app/routes/published.py`, `app/routes/public_storage.py`, `app/routes/standalone.py`, `app/app_services.py`, `app/providers.py`, `app/claude_sdk_runner.py`, `app/codex_sdk_runner.py`, `app/saved_secure_inputs.py`, `app/restart_util.py`, `app/deployment_control.py`, `app/platform_activation.py`, `app/capacity.py`, `app/resource_pressure.py`, `app/routes/connectors.py`
- Documentation: `README.md`, `SECURITY.md`, `ARCHITECTURE.md`, `CAPABILITIES.md`, `MODEL-PROVIDERS.md`, `COMPATIBILITY.md`, `CONTRIBUTING.md`, `skill/core.md`
- Image: GHCR manifests and config for the pinned digest; the pip layer `sha256:bd3c25cebb1fbbd42049f414aba8e638347658a0730f052f6f459f7aba48385f` was downloaded to confirm the uvicorn console script (nothing from it is redistributed).

The local `_upstream/mobius-os__mobius` copy matches the pinned commit for the boot, auth, config, database, model and main files (git blob hashes compared with the GitHub contents API).

## Market template reviewed (ideas only, nothing copied)

| Template | License | Use |
|---|---|---|
| `mobius` ("Möbius", image `ghcr.io/mobius-os/mobius:main`) | marketplace configuration only, no license | Read for the starting point (one service, `/data` volume). Its readme prose was not reused. |
