#!/bin/sh
# shellcheck shell=sh
# Installed as /usr/local/bin/uvicorn in this template's image; the original
# console script lives at /opt/mobius-railway/uvicorn-real.
#
# Upstream's entrypoint ends with
#   cd <served platform> && exec env -u ... uvicorn app.main:app --host 0.0.0.0 ...
# as the mobius user, after it has chosen the platform source. When the
# Railway wrapper marked this boot, ensure the owner account exists (created
# or rotated from Railway variables) with exactly that code, user and
# environment, before the server opens its port. If that fails, the server
# does not start. Every other uvicorn call (for example an app the agent
# builds) passes straight through.

if [ "${MOBIUS_RAILWAY_OWNER_BOOTSTRAP:-}" = "1" ] && [ "${1:-}" = "app.main:app" ]; then
    unset MOBIUS_RAILWAY_OWNER_BOOTSTRAP
    if ! timeout 900 /usr/local/bin/python3 -I /opt/mobius-railway/owner_bootstrap.py apply; then
        printf '[railway] FATAL: no usable owner account; Möbius is not started (its first-visitor setup would be open)\n' >&2
        exit 1
    fi
fi
unset MOBIUS_RAILWAY_OWNER_BOOTSTRAP

exec /opt/mobius-railway/uvicorn-real "$@"
