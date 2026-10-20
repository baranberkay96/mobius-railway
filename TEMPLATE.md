# Möbius v0.1 Personal AI OS: Railway template spec

## Listing

| Field | Value |
|---|---|
| Name | **Möbius v0.1 Personal AI OS** (`v0.1` = the version upstream declares in `frontend/package.json` and the FastAPI app, `0.1.0`; upstream publishes no releases, builds are identified by commit) |
| Description | Self-hosted AI agent that builds and runs apps for you, with memory. (68 chars, unchanged) |
| Category | AI/ML |
| Tags | mobius, ai-agent, personal-ai, app-builder, claude-code, codex, pwa, self-hosted |
| Icon | `https://cdn.jsdelivr.net/gh/mobius-os/mobius@c1e525f3239b73a0b899d7e7879a7fefce95c43c/frontend/public/moebius.png` (upstream logo pinned to the commit, HTTP 200 `image/png`, 384×384) |

The description holds as written:
- **Self-hosted**: one service in the user's own Railway project; all state on its volume.
- **Builds and runs apps**: the agent writes JSX mini-apps that Möbius compiles (Rolldown) and serves as installable PWAs, schedules server-side app jobs through cron, and can run reviewed app services; all inside this one container.
- **With memory**: per-chat summaries are always on; the Memory and Reflection apps are installed on the first boot (from upstream's catalog).

What the description does not say: the agent needs a **Claude (Claude Code) or ChatGPT (Codex) subscription**, connected after deploy (or the optional Möbius · You account service run by the Möbius team). The README states this under Dependencies.

## Base market template

| Market template | Source | State on 2026-10-20 | Verdict |
|---|---|---|---|
| `mobius` ("Möbius") | image `ghcr.io/mobius-os/mobius:main` with Railway image auto-updates (every day, all hours), volume `/data`, healthcheck `/recover/health` | 175 projects, 78 active, 165 deploys in 30 days | Base for the topology (one service, one `/data` volume), which matches upstream's own `railway.toml`. Problems: **no owner account**: upstream lets whoever first opens a fresh instance create the owner (`POST /api/auth/setup`), so the race for an agent with root, a shell and the owner's AI subscription is open until the owner gets there; moving `:main` tag plus auto-updates (upstream merges about 20 commits a day, each redeploy restarts the volume-bound service); healthcheck `/recover/health` is a retired path that now falls through to the SPA and returns 200 as soon as the port is open, whatever the database state; no restart policy set, so Railway's default (on failure) never revives the clean exit 0 that upstream uses for Settings → Restart and platform updates (upstream's `railway.toml` sets `ALWAYS` for exactly this reason); no `PORT`, no draining time. |

Upstream references checked at commit `c1e525f3239b73a0b899d7e7879a7fefce95c43c` (= the pinned image's `org.opencontainers.image.revision`): `Dockerfile`, `railway.toml`, `docker-compose.yml`, `.env.example`, `Caddyfile`, `backend/scripts/entrypoint.sh`, `backend/app/config.py`, `routes/auth.py`, `auth.py`, `models.py`, `database.py`, `main.py` (health, readiness, security headers, service-gateway host guard, SPA fallback), `startup.py`, `bootstrap.py`, `routes/local_services.py`, `routes/public_apps.py`, `routes/published.py`, `providers.py`, `claude_sdk_runner.py`, `codex_sdk_runner.py`, `saved_secure_inputs.py`, `scripts/update-owner-credentials.py`, `scripts/agent_sudo.sh`, `runtime/served_runtime_launcher.py`, `SECURITY.md`, `ARCHITECTURE.md`, `CAPABILITIES.md`, `MODEL-PROVIDERS.md`, `.github/workflows/main-image.yml`. The local `_upstream` copy is byte-identical to that commit for the files the wrapper depends on (git blob hashes compared through the GitHub API).

## Pinned versions

| Component | Source | Version | Date | Checked |
|---|---|---|---|---|
| Möbius | `ghcr.io/mobius-os/mobius:sha-c1e525f3239b73a0b899d7e7879a7fefce95c43c@sha256:e7b6da2a45ee2869e6b2e53bf532b7e5544adbf6aa5ad07439f70eefd3dcfbf2` (OCI index; linux/amd64 manifest `sha256:d7994e7e…` plus a build attestation; 54 layers, 1.07 GB compressed) | commit `c1e525f` "Offer standby-safe continuation for active Goals (#1710)", declared version 0.1.0 | committed 2026-10-19, image built 2026-10-19 | 2026-10-20 |

Checked through the GHCR registry API with an anonymous pull token: the `sha-c1e525f…` tag and `:main` resolve to the same index digest; the image config has `Entrypoint ["/usr/bin/tini","-s","--"]`, `Cmd ["./scripts/entrypoint.sh"]`, `WorkingDir /app`, runs as root (the entrypoint drops to `mobius`), exposes 8000, label `org.opencontainers.image.revision=c1e525f…`. The pip layer (`sha256:bd3c25ce…`) was downloaded and listed: `/usr/local/bin/uvicorn` is the standard pip console script of uvicorn 0.52.4 (`#!/usr/local/bin/python3.12`).

Upstream has no releases (one old tag `v0.1.0` from 2026-05-27). Every merge to `main` is published as an immutable `sha-<commit>` tag (821 tags on 2026-10-20) and promoted to the moving `:main` tag.

The service is built from `services/mobius/Dockerfile` (repo `baranberkay96/mobius-railway`, root `/services/mobius`), a thin layer on the pinned image that adds `railway/` (wrapper entrypoint, uvicorn shim, owner bootstrap). Upgrade: replace the `sha-` tag and digest in the Dockerfile with a newer build from https://github.com/mobius-os/mobius/pkgs/container/mobius and redeploy; the build fails early if the upstream hooks the wrapper uses have moved.

## Architecture

```
 Browser / installed PWA ──HTTPS (Railway edge)──► :8000, healthcheck GET /api/ready
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │ Mobius (ghcr.io/mobius-os/mobius:sha-c1e525f… + railway/ wrapper)            │
 │ podman-init (PID 1) → tini -s → railway-entrypoint.sh (root)                 │
 │   checks PORT/DOMAIN, drops FORWARDED_ALLOW_IPS/UVICORN_*, creates           │
 │   /data/.secret-key if missing, stashes owner credentials (0600, mobius)     │
 │   → exec upstream /app/scripts/entrypoint.sh (root, unchanged):              │
 │       volume permissions, first-boot seed of /data/platform (git clone       │
 │       of the platform), import probe, identity broker (root), restart        │
 │       poller, health probe that starts cron                                  │
 │       → su mobius → uvicorn app.main:app --host 0.0.0.0 --port 8000          │
 │            = /usr/local/bin/uvicorn (template shim):                         │
 │              owner_bootstrap.py apply  (create / rotate owner, fail closed)  │
 │              → exec real uvicorn: FastAPI API + PWA + SSE, one worker        │
 │                 agent turns: Claude Code SDK / Codex SDK subprocesses,       │
 │                 agent-browser (Chrome headless shell), Rolldown/Vite builds  │
 │ cron (root daemon, jobs as mobius): app jobs, self-reminders                 │
 │ volume /data: db/ultimate.db (SQLite), platform/ (editable source), apps/,   │
 │   compiled/, shared/ (memory, skills), cli-auth/ (Claude/Codex/GitHub        │
 │   sign-ins), app-secrets/, published/, .secret-key, service-token.txt        │
 └──────────────────────────────────────────────────────────────────────────────┘
```

One service and no database service: SQLite is the only persistence runtime upstream supports and tests (ARCHITECTURE.md, "Data layout"); upstream's compose file is the app container plus Caddy for TLS, which Railway's edge replaces. There is no worker, queue or cache to add.

### How the apps it builds are run and served

| What the agent builds | How it runs | URL on Railway's single domain | Works here |
|---|---|---|---|
| Mini-app (JSX) | Compiled into `/data/compiled`, runs in the browser in an opaque sandboxed iframe with an app-scoped token | inside the workspace; installable page `/apps/{slug}/` (owner login required) | yes |
| Scheduled app job | Script started by cron through upstream's job runner with a short-lived app token; runs with the Möbius process's file access | none | yes (cron runs in the container) |
| Reviewed app service | One Python process per request (or forked from a preloaded host), 15 s limit, JSON in/out | `/api/apps/{id}/service/…`; routes the app declares public answer without login | yes |
| Public app | Owner explicitly publishes an app; anonymous sandboxed runtime with a public token that has no owner identity | `/{slug}` | yes |
| Published site | Static snapshot of a project build, CSP sandbox (opaque origin) | `/sites/{token}/` | yes |
| Full web service (e.g. Tandoor, Grafana) | A loopback process the agent starts, declared in `/data/local-services.json` with `access: upstream_auth` (the service must have its own login) | `/services/{slug}/` on the main domain serves it as inert content (no scripts); scripted UIs need the separate gateway origin | partly: needs a custom domain for the gateway (below) |

No app gets its own port on the public edge: everything goes through the FastAPI process on port 8000, so the single Railway domain is enough. The one exception is the **service gateway** for full web services, which upstream keeps on a different hostname so those services cannot act as the Möbius shell. Railway allows one generated domain per service but several custom domains, so: attach a custom domain (e.g. `services.example.com`) to this service, set `MOBIUS_SERVICE_GATEWAY_ORIGIN=https://services.example.com`, redeploy. The backend itself enforces that this host serves only `/services/{slug}` prefixes that opted in (`_ServiceSurfaceHostMiddleware`), and every other path returns 404, so no proxy is needed.

Long-running services the agent starts by hand (outside upstream's job runner) are ordinary child processes: a container restart stops them.

### Network binding

Upstream's entrypoint runs uvicorn with one worker on `0.0.0.0:$PORT` (Rule 8.2: an asyncio socket on `::` would be IPv6-only and Railway's IPv4 healthcheck would fail). Nothing else in the project connects to it. There is no in-container proxy: upstream rate-limits logins and guards its local MCP broker (`_require_loopback`) by the TCP peer address, and a proxy inside the container would make every request look local.

## Service: Mobius

| Setting | Value |
|---|---|
| Source | repo `baranberkay96/mobius-railway`, root `/services/mobius` (Dockerfile) |
| Start | image ENTRYPOINT `tini -s --`, CMD `/opt/mobius-railway/railway-entrypoint.sh` (no start command override) |
| Healthcheck | `GET /api/ready` on `PORT=8000`, timeout 600 s. Upstream's own Railway healthcheck: 200 only when the database schema is complete and the chat writer runs. The first boot seeds the platform checkout, initialises the database and installs six default apps from GitHub before the server listens, so the window is double upstream's 300 s. |
| Public domain | yes, target port 8000 |
| TCP proxy | none |
| Volume | `/data` (upstream's `requiredMountPath`) |
| Restart policy | `ALWAYS`, no retry cap (upstream exits 0 for planned restarts and platform updates; Rule 8.5) |
| Replicas | 1 (SQLite, single-writer chat actor, files on the volume) |
| Draining | `RAILWAY_DEPLOYMENT_DRAINING_SECONDS=15` (upstream's `drainingSeconds`; uvicorn's graceful shutdown is 10 s) |

### What the wrapper does

| Step | Where | Effect |
|---|---|---|
| `PORT` | entrypoint (root) | Must be 1-65535, else the boot stops. |
| `FORWARDED_ALLOW_IPS`, `UVICORN_*` | entrypoint | Unset (logged). uvicorn would otherwise take the client address from `X-Forwarded-For`, letting a forged header pose as a loopback client to the MCP broker check and the login rate limiter. |
| `DOMAIN` | entrypoint | Empty → unset (upstream would build the origin `https://` and refuse to start); scheme, trailing slash and case normalised. |
| `/data` check | entrypoint | Warning when `/data` is not a mounted volume. |
| `/data/.secret-key` | entrypoint | Created (64 hex characters, as upstream does) only when it is missing and `SECRET_KEY` is not set. Upstream creates it after its ownership pass, so on the first boot it stays root-only until the next restart and helpers that run as `mobius` (e.g. changing the password inside Möbius) cannot read it. Created earlier, upstream's own pass hands it to `mobius` and sets mode 600. |
| Owner credentials | entrypoint → `owner_bootstrap.py stash` | `MOBIUS_OWNER_USERNAME` / `MOBIUS_OWNER_PASSWORD` are written to `/run/mobius-railway/owner.json` (dir 0700, file 0600, owner `mobius`) and unset, so neither upstream's entrypoint nor the server or the agent inherits them. The boot is marked with `MOBIUS_RAILWAY_OWNER_BOOTSTRAP=1`. |
| Upstream entrypoint | `/app/scripts/entrypoint.sh` | Runs unchanged. |
| Owner account | `/usr/local/bin/uvicorn` shim → `owner_bootstrap.py apply` (as `mobius`, in the platform directory upstream selected, with the server's environment, before the port opens) | See below. On failure the server does not start (exit 1), so a fresh instance never serves the first-visitor setup. |
| Server | shim | Unsets the marker and execs the original uvicorn console script (moved to `/opt/mobius-railway/uvicorn-real`). Any other `uvicorn` call, such as an app the agent builds, passes through unchanged. |

Owner bootstrap rules (`apply`), all using the served code's own `models.Owner`, `auth.hash_password` / `verify_password` / `write_service_token` and `main._init_db`:

| Situation | Result |
|---|---|
| No owner table yet (fresh volume) | Credentials validated first (username 1-64 characters, password 12-1024); then upstream's `_init_db()` creates and migrates the schema (idempotent; the server's startup runs it again and finds it current), the owner row is inserted with the same single-row check as upstream's setup route, the 90-day service token is written, and a salted PBKDF2 digest of the applied pair is stored in `/data/cli-auth/railway-template/owner-applied.json` (0600; `cli-auth/` is excluded from Möbius's `/data` Git repository and file viewer). |
| No owner, variables empty or invalid | Boot stops with the reason in the deploy log. |
| Owner exists, variables equal the last applied pair | Nothing changes, so a password changed inside Möbius is kept. |
| Owner exists, variables changed | Username and password are reset to the variables, `token_epoch` is incremented (signs out every session and the service token) and the service token is re-minted; the same steps as upstream's `update-owner-credentials.py`. |
| Owner exists, variables empty | Nothing changes (logged). |
| Owner exists, variables set but invalid | Boot stops (logged), so a mistyped rotation is not silently ignored. |
| Applied-pair record lost, variables match the database | Record rewritten, no sign-out. |
| Owner in mobius.you sign-in mode, or managed SSO configured | Skipped (logged). |

### Variables

None is required at deploy.

| Variable | Default | Notes |
|---|---|---|
| `PORT` | `8000` | Healthcheck port = app port = domain target port (Rule 8.1); upstream's default |
| `MOBIUS_OWNER_USERNAME` | `owner-${{secret(8, "…")}}` | Random so nobody can put the owner's name into upstream's per-username login cooldown (1 min after 10 failures, up to 15 min after 30) |
| `MOBIUS_OWNER_PASSWORD` | `${{secret(32)}}` | Applied when it changes (see above) |
| `MOBIUS_AGENT_SUDO` | `1` | Upstream variable and default: passwordless root for the agent inside the container; `0` removes the sudoers rule on the next deploy |
| `DOMAIN` | empty | Upstream variable. Bare custom host name; empty = derived from `RAILWAY_PUBLIC_DOMAIN` |
| `MOBIUS_SERVICE_GATEWAY_ORIGIN` | empty | Upstream variable. HTTPS origin of a second (custom) domain for full web services; empty = off |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `15` | Graceful stop window |

Not set on purpose:
- `SECRET_KEY`: upstream generates it on the volume (`/data/.secret-key`) and its helpers that run without the server's environment (password change from inside Möbius, scripts the agent runs) read it from there; with the key only in an environment variable they would fail. Keeping key and encrypted data on the same volume also means deleting a variable can never strand the stored secrets.
- LLM keys: Möbius has no provider-key variables. Claude Code (OAuth with a pasted code) and Codex (device code) are connected in Settings and stored in `/data/cli-auth`; app-provided model connections keep their keys as encrypted app secrets. The app boots and serves without any provider.
- `GITHUB_OAUTH_CLIENT_ID`, `MOBIUS_ACCOUNT_ORIGIN`, contribution relay variables: upstream's defaults apply (an empty value would disable the GitHub device flow).
- `DATABASE_URL`, `DATA_DIR`: upstream defaults (`sqlite:////data/db/ultimate.db`, `/data`).

## Security model and what is reachable publicly

**Requires the owner login** (JWT in the shell's localStorage, 30-day expiry, bcrypt-12 over SHA-256): the workspace and chat, all agent, file, settings, app management and provider APIs, the standalone app pages `/apps/{slug}/` (the page loads, the app opens only after login), and `/services/{slug}/` on the main domain (served inert, and the upstream service must have its own login).

**Public by upstream design** (no owner identity): the login screen and static shell assets; `/api/health`, `/api/ready`, `/api/ready/agent`, `/api/version` (build and served commit), `/api/auth/setup/status`; and only what the owner publishes:
- published sites `/sites/{token}/` (unguessable token, CSP sandbox without same-origin, so their scripts cannot read the owner token);
- public apps `/{slug}` (an app the owner explicitly made public; runs in the opaque app frame with a public token that cannot reach owner, chat or agent APIs; its only network capability is GET against the app's reviewed allowlist);
- app-service routes an installed app declares public, and anonymous public storage scoped to that app's `public/` tree;
- on the optional gateway host: only the `/services/{slug}` prefixes the owner enabled.

So nothing the agent publishes exposes the agent itself: anonymous principals carry no owner identity, every non-platform response is served with an inert or sandboxed CSP, and chats run only for owner (or owner-delegated) tokens.

**Inside the container** (upstream's single-owner trust model, SECURITY.md "Agent security model"): every agent turn auto-approves tool calls (Claude SDK `can_use_tool` allows all but a few scheduling tools; Codex runs with `Sandbox.full_access` because its bubblewrap sandbox cannot run under the container's seccomp profile), the agent receives the owner JWT (`$AGENT_TOKEN`), and with the default `MOBIUS_AGENT_SUDO=1` it has passwordless root. It can therefore read the database, `/data/.secret-key`, the Claude/Codex/GitHub credentials in `/data/cli-auth`, decrypted app secrets, and (as root) the container's initial environment in `/proc/1/environ`, which still holds the owner variables. A prompt injection through a web page the agent browses, a fetched document or an installed app could make it run commands with that authority, spend the connected subscription, or push to the connected GitHub account. Server-side app jobs run with the Möbius process's file access too. Upstream accepts this deliberately; the template documents it and keeps upstream's switch. `MOBIUS_AGENT_SUDO=0` is coarse: the agent still owns `/data`, and upstream runs the identity broker from the agent-editable served source as root at boot, so a persistent agent could regain root after a restart.

**Default apps**: the first boot installs Store, Skills, Memory, Reflection, Integrations and Möbius · You from the `main` branch of their `mobius-os/app-*` repositories (not pinned by upstream or by this template). Store, Memory and Reflection run scheduled server-side jobs and Memory and Reflection app services, with the same file access as other app jobs.

**Rate limiting**: upstream limits login (5/min), setup (3/min) and provider sign-in by TCP peer address. Behind Railway's edge many clients may share that address, so a flood of wrong logins can delay the owner's login by a minute; the random username keeps the per-username cooldown out of reach. Not changed, because trusting `X-Forwarded-For` would weaken the loopback checks (see the wrapper table).

## First login

1. Wait for the deployment to turn healthy (first build pulls a ~1.1 GB image; the first boot seeds the platform and installs the default Store, Skills, Memory, Reflection, Integrations and Möbius · You apps from GitHub).
2. Open the public URL, sign in with `MOBIUS_OWNER_USERNAME` / `MOBIUS_OWNER_PASSWORD` from the service's Variables tab.
3. Settings → AI provider: connect Claude Code (open the claude.ai link, paste the code back) or Codex (device code at chatgpt.com). Optional: link a Möbius · You account for its hosted models.
4. Ask for an app ("Build a simple habits app"). On a phone, install Möbius (and any app) to the home screen.

## Improvements over market templates

1. **No first-visitor takeover**: the owner account exists before the server opens its port, created from generated, random credentials; a fresh instance with missing or invalid credentials refuses to start (market: the first person to open the URL becomes the owner of an agent with root and the owner's AI subscription).
2. **Login reset from Railway**: change the variables and redeploy; sessions are revoked; a password changed inside Möbius is kept otherwise. Credentials never enter the server's or the agent's environment.
3. **Pinned build** by immutable `sha-` tag and digest, with a build-time check of the upstream hooks the wrapper relies on (market: moving `:main` with daily auto-updates).
4. **Real readiness healthcheck** `/api/ready` (market: `/recover/health`, a retired path answered by the SPA fallback).
5. **Restart policy `ALWAYS`** so Settings → Restart and platform updates, which exit 0, come back (market: Railway's default policy, which leaves a clean exit down).
6. `PORT`/target port 8000 and 15 s draining set explicitly, as in upstream's `railway.toml`.
7. `/data/.secret-key` readable by the Möbius user from the first boot, so an in-app password change works before the first restart.
8. Hardening of the server's launch: forwarded-IP trust and `UVICORN_*` overrides removed, `DOMAIN` normalised, warning when `/data` is not a volume.
9. Documented public surface, app hosting tiers on one domain, and the custom-domain gateway for full web services.

## Resource estimate

Railway prices: RAM $10/GB-month, vCPU $20/vCPU-month, volume $0.15/GB-month. Not measured (no container run); derived from the process set above.

| Service | Idle RAM / CPU | Typical RAM / CPU | Notes |
|---|---|---|---|
| Mobius | ~0.4-0.7 GB / 0.02-0.05 vCPU | 1.5-2.5 GB / 0.2-0.5 vCPU during agent turns | Idle: FastAPI server with a large module set, identity broker, cron. Turns add the Claude Code or Codex runtime (0.3-0.5 GB), Chrome headless shell for screenshots (0.2-0.4 GB) and Rolldown/Vite builds (0.3-0.8 GB). Parallel chats and subagents add up; upstream's compose caps the container at 6 GB. |
| Volume | ~0.1-0.2 GB after the first boot (platform checkout, default apps, database) | 1-5 GB | Chats, compiled apps, browser profiles, provider CLI data (upstream once traced a full volume to Codex telemetry), published sites |

Estimated monthly cost: **idle ≈ $6**, **typical ≈ $15-25** for daily use (about 1-1.5 GB average RAM, 0.2 vCPU, 2-3 GB volume); heavy parallel building $30-50. Model usage is billed by the owner's Claude or ChatGPT plan.

Minimum plan: **Hobby**. Trial's 1 GB RAM per service is too small for app builds and browser use. Hobby's 5 GB volume fits light use; heavy use or many apps need Pro (upstream's own deployment runs a 45 GiB volume).

## Verification results (2026-10-20, no Docker)

Docker was not used. **The Dockerfile has not been built and the container has not been run.**

| Check | How | Result |
|---|---|---|
| Image tag and digest | GHCR registry API (anonymous token): manifest HEAD for `sha-c1e525f…` and `:main`, index, amd64 manifest, config blob | both resolve to index `sha256:e7b6da2a…`; amd64 only; entrypoint, cmd, workdir, labels as described |
| Image contents the wrapper needs | pip layer `sha256:bd3c25ce…` downloaded and listed | `/usr/local/bin/uvicorn` is the pip console script (`from uvicorn.main import main`), uvicorn 0.52.4 |
| Commit and local copy | `gh api` commit and contents | `c1e525f` is `main` HEAD (2026-10-19); entrypoint, Dockerfile, `railway.toml`, auth, config, main, models, database identical to `_upstream` |
| Dockerfile RUN checks | each `grep` run against the matching upstream file locally | all match |
| Scripts | `sh -n`, `dash -n`, `bash -n`, shellcheck 0.11 (`-s sh`), ruff 0.17 (E,F,W,B,UP,S), `py_compile`, `json` parse of template.json | clean |
| `owner_bootstrap.py` logic | 23 scenarios against a stub backend written for the test (same interfaces: `Owner` model, `hash_password`, `verify_password`, `write_service_token`, `_init_db`, `get_settings`) on SQLAlchemy 2.0.52; upstream code was not executed | first boot creates owner, state 0600 without the password, service token, schema initialised once; reboot unchanged; in-app password change kept; rotation renames, re-hashes, bumps epoch; empty variables no-op; invalid variables fail closed; lost record without sign-out; mobius.you mode and managed SSO skipped; table without row; corrupt credentials file and wrong cwd fail closed |
| uvicorn shim | copy with test paths and a fake real uvicorn | pass-through without marker or for other apps; first boot without credentials exits 1 before the server; with credentials creates the owner and then execs the server without the marker |
| Wrapper entrypoint | copy with test paths and a stub upstream entrypoint | bad `PORT` stops; `FORWARDED_ALLOW_IPS` and `UVICORN_*` removed; `DOMAIN` normalised/unset when empty; secret key created once (64 hex, 0600) and kept on reboot, not created when `SECRET_KEY` is set; credentials stashed (0700/0600) and absent from the upstream environment; marker set |
| Links and icon | curl | all README/TEMPLATE links and the icon return 200 |
| Docker build, container run, Railway behaviour | | **not run (unverified)** |

## Verification checklist

- [ ] Build log: the `RUN` check passes and the build finishes (base image ~1.1 GB).
- [ ] Deploy log: `[railway] generated SECRET_KEY …`, `starting the Möbius entrypoint`, `Platform layer: seed complete`, `[railway] first boot: initialising the database …`, `[railway] owner account 'owner-…' created …`; no `/data is not a mounted volume`; healthcheck `/api/ready` passes within 600 s.
- [ ] `curl https://{domain}/api/auth/setup/status` → `{"configured":true,…}`; `curl -X POST https://{domain}/api/auth/setup -H 'Content-Type: application/json' -d '{"username":"x","password":"y"}'` → 400 "Already configured."; `curl https://{domain}/api/chats` → 401.
- [ ] Sign in with the generated credentials; connect Claude Code or Codex; a chat reply arrives; ask for a small app and open it, also at `/apps/{slug}/`.
- [ ] `railway ssh`: `ls -l /data/.secret-key` → owner `mobius`, mode 600; `tr '\0' '\n' < /proc/$(pgrep -of 'uvicorn-real')/environ | grep -c MOBIUS_OWNER` → 0; `ls /run/mobius-railway` → empty.
- [ ] Persistence: redeploy; log shows `owner account … unchanged`; chats, apps and the provider sign-in survive.
- [ ] Rotation: change `MOBIUS_OWNER_PASSWORD`, redeploy → log `owner login reset …`; the old session is signed out and the new password works.
- [ ] Settings → Restart: the deployment exits and comes back healthy by itself (restart policy `ALWAYS`).
- [ ] Publish a project as a site and an app as public; open both in a private window: they load without login and expose no chat or settings.
- [ ] Optional: attach a custom domain, set `DOMAIN`, redeploy, sign in on that domain.

## Open questions

- **The image has never been built or run by us.** The upstream image runs on Railway every day (market template, upstream's managed deployments), but the shim path (owner bootstrap before uvicorn) is new. Likely failure points: `import app.main` plus `_init_db()` inside the shim on the first boot (the same import upstream's own probe runs), and SQLite file ownership if a root step touched the database after upstream's ownership repair.
- First-boot duration on Railway (seed copy, import probes, schema creation, default app installs from GitHub) is not measured; 600 s is a guess with margin.
- Settings → container updates: on a Railway deployment that is not linked to upstream's account service, upstream reports image updates as unavailable; platform source updates still work. Not exercised.
- The service gateway on a second custom domain is implemented upstream in the backend and should work behind Railway's edge, but was not exercised.
- RAM and volume figures are estimates.
- Default apps are installed from each catalog repository's `main` at first boot (upstream design), so two deployments of the same template can start with different app versions, and new instances trust the current state of those repositories. They are not only browser code: Store, Memory and Reflection declare scheduled server-side jobs (09:00, 05:30, 06:00 by default) and Memory and Reflection declare app services (checked in their `mobius.json` on 2026-10-20); the nightly Memory and Reflection runs use the connected AI plan.
