# Deploy and Host Möbius with Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/mobius-v01-personal-ai-os?referralCode=20H68q)

Run Möbius, the open-source personal AI OS, on your own Railway project. You chat with an agent (Claude Code or Codex, on the plan you already have) that builds small apps beside the conversation, runs scheduled tasks, and keeps a memory of how you work. Your login is created before the app goes online.

## About Hosting Möbius

Möbius is one container: a FastAPI server with an installable web app (PWA), the Claude Code and Codex agent runtimes, a headless browser, an app compiler, cron and a SQLite database. Everything it keeps, from chats and memory to the apps it builds and your provider sign-ins, lives under `/data`. Self-hosting it needs a volume, HTTPS and, above all, a login: upstream lets the first visitor of a fresh instance create the owner account. This community template runs the official image pinned to an exact build, creates the owner from generated credentials before the port opens, and checks readiness through the database and chat writer.

## Common Use Cases

- Describe a tracker, dashboard or small tool and use it a minute later on your phone as an installed app
- Daily briefs, reports and checks that run on a schedule and wait for you in the morning
- A long-running assistant that remembers your projects, decisions and preferences across chats
- Long goals broken into steps that the agent keeps working on, asking only when it needs you
- Publishing a finished app or page as a public link without exposing your workspace

## Dependencies for Möbius Hosting

- A Claude (Claude Code) or ChatGPT (Codex) subscription, connected after the first login in Settings. No API key is needed to deploy.
- A Railway volume at `/data` (included)
- Optional: a GitHub account for publishing apps and sending contributions

### Deployment Dependencies

- Möbius repository (MIT): https://github.com/mobius-os/mobius
- Container image: https://github.com/mobius-os/mobius/pkgs/container/mobius
- Self-hosting notes and variables: https://github.com/mobius-os/mobius/blob/c1e525f3239b73a0b899d7e7879a7fefce95c43c/.env.example
- Security model: https://github.com/mobius-os/mobius/blob/c1e525f3239b73a0b899d7e7879a7fefce95c43c/SECURITY.md
- Architecture (app tiers, data layout, updates): https://github.com/mobius-os/mobius/blob/c1e525f3239b73a0b899d7e7879a7fefce95c43c/ARCHITECTURE.md

### Implementation Details

| Service | Source | Purpose |
|---|---|---|
| Mobius | Dockerfile in `services/mobius` on `ghcr.io/mobius-os/mobius:sha-c1e525f…` (pinned by digest) | Web app, API, agents, app compiler, headless browser, cron and SQLite on port 8000; healthcheck `/api/ready`; volume at `/data`; restart policy always |

**First login**

1. Wait until the deployment is healthy. The first boot copies the platform source onto the volume and installs the default apps, which takes a few minutes.
2. Open the public URL and sign in with `MOBIUS_OWNER_USERNAME` and `MOBIUS_OWNER_PASSWORD` from the service's Variables tab. There is no setup screen to claim: the owner already exists.
3. In **Settings**, connect Claude Code (sign in to claude.ai and paste the code) or Codex (device code).
4. Ask for something, for example "Build a simple habits app". On a phone, add Möbius to the home screen.

**Login**: change `MOBIUS_OWNER_PASSWORD` or `MOBIUS_OWNER_USERNAME` and redeploy to reset it; every session is signed out. A password changed inside Möbius is kept until you change the variable. If the variables are missing or invalid on a fresh volume, Möbius does not start.

**What is public**: only the login screen, static assets, health endpoints, and what you choose to publish: published sites (`/sites/{token}/`), public apps (`/{app-slug}`) and app routes an installed app marks public. They run in sandboxed, anonymous contexts with no access to your chats or the agent. Everything else needs your login.

**Apps and services**: mini-apps, installable app pages (`/apps/{app-slug}/`) and scheduled jobs run inside this one service and need no extra ports. A full web service the agent sets up (for example a recipe manager) is reached through `/services/{name}/`; scripted pages there need a second hostname: attach a custom domain such as `services.{your-domain}` to this service and set `MOBIUS_SERVICE_GATEWAY_ORIGIN` to `https://services.{your-domain}`. Railway gives each service one generated domain, so this needs your own DNS name.

**Custom domain**: attach it in Railway, then set `DOMAIN` to the bare host name (for example `ai.{your-domain}`) and redeploy, and open Möbius from that domain.

**Security notes**: the agent runs shell commands without asking and, by default, has passwordless root inside the container (`MOBIUS_AGENT_SUDO=0` removes root). It can read everything on the volume, including your provider sign-ins. Treat the login like a server password and connect only the accounts you want the agent to use. The default apps come from upstream's app catalog at first boot; Memory and Reflection run nightly jobs that use your connected AI plan.

**Scaling**: one replica only (SQLite and the files on `/data` have one writer). Give the service more RAM for parallel agents and app builds. Hobby's 5 GB volume suits light use; heavy use needs Pro.

**Pinning and upgrades**: the Dockerfile pins one upstream build (`sha-` tag plus digest). Upstream publishes every merge as `ghcr.io/mobius-os/mobius:sha-{commit}`; to upgrade, change both values and redeploy. Platform updates offered in Settings change the source on the volume, not this image. Back up `/data` before large jumps.

### Why Deploy Möbius on Railway?

An agent that works while you are away needs a machine that never sleeps, a persistent disk and HTTPS. Railway provides all three in one service with restarts, logs and SSH, so you keep Möbius and everything it learns in your own project without running a server yourself.
