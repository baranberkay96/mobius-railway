#!/bin/sh
# shellcheck shell=sh
# Möbius on Railway: a thin wrapper that runs before the official image's own
# entrypoint (/app/scripts/entrypoint.sh) and then hands over to it.
#
# Railway's podman-init is PID 1, the image's tini (-s, subreaper) is its
# child, and this script is tini's command. Everything upstream does at boot
# (volume permissions, platform checkout, identity broker, cron, dropping to
# the mobius user) is unchanged. This wrapper only:
#   1. validates PORT and strips settings that would weaken the server
#      (FORWARDED_ALLOW_IPS / UVICORN_*, an empty DOMAIN that crashes config);
#   2. creates /data/.secret-key before upstream's ownership pass when it is
#      missing, so the mobius user can read it from the very first boot;
#   3. moves the owner credentials out of the environment into a file only
#      the mobius user can read, and marks this boot so /usr/local/bin/uvicorn
#      creates or rotates the owner account before the port opens.
set -eu

log() {
    printf '[railway] %s\n' "$*" >&2
}

PORT="${PORT:-8000}"
case "$PORT" in
    ''|*[!0-9]*) log "FATAL: PORT must be a port number, got '${PORT}'"; exit 1 ;;
esac
if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    log "FATAL: PORT must be between 1 and 65535, got '${PORT}'"
    exit 1
fi
export PORT

# Möbius rate-limits logins and guards its local MCP broker by the TCP peer
# address. uvicorn would replace that address with X-Forwarded-For for peers
# listed in FORWARDED_ALLOW_IPS (or UVICORN_FORWARDED_ALLOW_IPS), so a forged
# header could pose as 127.0.0.1. Keep uvicorn's default: trust loopback only.
if [ -n "${FORWARDED_ALLOW_IPS:-}" ]; then
    log "FORWARDED_ALLOW_IPS ignored: forged proxy headers could pose as a local client"
fi
unset FORWARDED_ALLOW_IPS
for _var in $(env | sed -n 's/^\(UVICORN_[A-Za-z0-9_]*\)=.*/\1/p'); do
    log "${_var} ignored: server options are fixed by the Möbius entrypoint"
    unset "$_var"
done

# Upstream derives its HTTPS origin from RAILWAY_PUBLIC_DOMAIN unless DOMAIN
# is set. An empty DOMAIN would yield the origin "https://" and stop the boot,
# and a scheme or trailing slash would produce a wrong origin.
if [ "${DOMAIN+x}" = x ]; then
    _domain=$(printf '%s' "$DOMAIN" | sed -e 's#^[Hh][Tt][Tt][Pp][Ss]*://##' -e 's#/*$##' | tr '[:upper:]' '[:lower:]')
    if [ -z "$_domain" ]; then
        unset DOMAIN
    else
        if [ "$_domain" != "$DOMAIN" ]; then
            log "DOMAIN normalised to '${_domain}' (bare host name expected)"
        fi
        export DOMAIN="$_domain"
        log "public origin: https://${DOMAIN} (DOMAIN)"
    fi
fi

if ! awk '$5 == "/data" { found = 1 } END { exit !found }' /proc/self/mountinfo 2>/dev/null; then
    log "WARNING: /data is not a mounted volume; chats, apps, memory, the owner account and provider sign-ins are lost on redeploy"
fi

# The signing key for logins and the key that encrypts stored secrets. Upstream
# generates the same 64-hex key when it is missing, but only after its
# ownership pass, which leaves the file root-only until the next restart and
# breaks helpers that run as the mobius user (for example a password change
# from inside Möbius). An explicit SECRET_KEY variable still wins upstream.
if [ -z "${SECRET_KEY:-}" ] && [ ! -e /data/.secret-key ]; then
    mkdir -p /data
    (
        umask 077
        python3 -I -c 'import secrets; print(secrets.token_hex(32))' > /data/.secret-key.railway-tmp
        mv /data/.secret-key.railway-tmp /data/.secret-key
    )
    log "generated SECRET_KEY at /data/.secret-key (keep this volume: it encrypts stored provider and app secrets)"
fi

# Owner credentials: out of the environment of everything upstream starts.
python3 -I /opt/mobius-railway/owner_bootstrap.py stash
unset MOBIUS_OWNER_USERNAME MOBIUS_OWNER_PASSWORD
export MOBIUS_RAILWAY_OWNER_BOOTSTRAP=1

log "starting the Möbius entrypoint (port ${PORT}, agent root: MOBIUS_AGENT_SUDO=${MOBIUS_AGENT_SUDO:-1})"
cd /app
exec /app/scripts/entrypoint.sh "$@"
