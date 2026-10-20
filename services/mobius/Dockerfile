# Möbius for Railway: the official image plus a small owner-bootstrap wrapper.
#
# Nothing of Möbius is rebuilt. The wrapper (railway/) runs before upstream's
# entrypoint, keeps the owner credentials out of the server's environment, and
# makes sure the owner account exists before the server opens its port
# (upstream lets the first visitor of a fresh instance create the owner).
#
# Pinned by immutable tag and index digest: upstream publishes no releases;
# every merge to main is built as ghcr.io/mobius-os/mobius:sha-<commit>, and
# :main moves. This is commit c1e525f3239b73a0b899d7e7879a7fefce95c43c
# (2026-10-19, image built 2026-10-19, linux/amd64 only).
# Upgrade: pick a newer sha-<commit> tag and its digest, check that the
# entrypoint still ends in `exec $_env_scrub uvicorn app.main:app` (the RUN
# check below fails the build otherwise), redeploy. /data keeps everything.
FROM ghcr.io/mobius-os/mobius:sha-c1e525f3239b73a0b899d7e7879a7fefce95c43c@sha256:e7b6da2a45ee2869e6b2e53bf532b7e5544adbf6aa5ad07439f70eefd3dcfbf2

ENV PORT=8000

COPY --chmod=0755 railway/railway-entrypoint.sh /opt/mobius-railway/railway-entrypoint.sh
COPY --chmod=0755 railway/uvicorn-shim.sh /opt/mobius-railway/uvicorn-shim.sh
COPY --chmod=0644 railway/owner_bootstrap.py /opt/mobius-railway/owner_bootstrap.py

# Fail the build, not the first boot, when the upstream hooks the wrapper
# relies on have moved: the final uvicorn exec in upstream's entrypoint, the
# pip console script it runs, and the backend symbols owner_bootstrap.py uses
# (checked in the baked checkout, which seeds /data/platform on first boot).
RUN set -eu; \
    sh -n /opt/mobius-railway/railway-entrypoint.sh; \
    sh -n /opt/mobius-railway/uvicorn-shim.sh; \
    python3 -I -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' /opt/mobius-railway/owner_bootstrap.py; \
    grep -qF 'exec $_env_scrub uvicorn app.main:app' /app/scripts/entrypoint.sh; \
    grep -qF 'from uvicorn.main import main' /usr/local/bin/uvicorn; \
    b=/app/platform-baked/backend/app; \
    grep -q '^def _init_db' "$b/main.py"; \
    grep -q '^def hash_password' "$b/auth.py"; \
    grep -q '^def verify_password' "$b/auth.py"; \
    grep -q '^def write_service_token' "$b/auth.py"; \
    grep -q '__tablename__ = "owner"' "$b/models.py"; \
    grep -q 'token_epoch = Column' "$b/models.py"; \
    grep -q '^SessionLocal' "$b/database.py"; \
    grep -q 'def mobius_sso_enabled' "$b/config.py"; \
    for tool in timeout awk sed su tini; do \
      command -v "$tool" >/dev/null || { echo "missing in base image: $tool" >&2; exit 1; }; \
    done; \
    id mobius >/dev/null; \
    mv /usr/local/bin/uvicorn /opt/mobius-railway/uvicorn-real; \
    cp /opt/mobius-railway/uvicorn-shim.sh /usr/local/bin/uvicorn; \
    chmod 0755 /usr/local/bin/uvicorn /opt/mobius-railway/uvicorn-real

EXPOSE 8000

# Same init as upstream (tini as subreaper, a child of Railway's podman-init);
# only the command changes. railway-entrypoint.sh ends by exec'ing upstream's
# /app/scripts/entrypoint.sh.
ENTRYPOINT ["/usr/bin/tini", "-s", "--"]
CMD ["/opt/mobius-railway/railway-entrypoint.sh"]
