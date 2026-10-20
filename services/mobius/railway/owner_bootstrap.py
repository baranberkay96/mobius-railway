"""Owner account for Möbius on Railway, set up before the server listens.

Upstream Möbius has no owner on a fresh volume: the first visitor of the public
URL creates one through POST /api/auth/setup. On a public Railway domain that
would hand an agent with shell, root and your AI subscription to whoever comes
first. This template therefore creates the owner from generated Railway
variables before the server opens its port.

Two modes:

  stash  (root, from railway-entrypoint.sh)
      Moves MOBIUS_OWNER_USERNAME / MOBIUS_OWNER_PASSWORD from the environment
      into /run/mobius-railway/owner.json (mode 0600, owned by the mobius
      user), so they never reach the Möbius server or the agent's environment.

  apply  (mobius user, from /usr/local/bin/uvicorn right before the server)
      Runs in the platform directory upstream's entrypoint selected (served
      checkout or baked fallback) with the server's environment, and uses that
      code's own models and password hashing:
        * no owner yet: create it from the variables (fails closed when they
          are missing or invalid, so the server never starts unowned);
        * owner exists, variables unchanged since they were last applied:
          nothing happens (a password changed inside Möbius is kept);
        * owner exists, variables changed: username and password are reset to
          them and every session is signed out (token epoch bumped).

Exit status 0 means an owner exists and the server may start.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import pwd
import secrets
import sys
import tempfile
from pathlib import Path

CREDENTIALS_DIR = Path("/run/mobius-railway")
CREDENTIALS_FILE = CREDENTIALS_DIR / "owner.json"
# Under /data/cli-auth/: ignored by Möbius's /data safety Git repository and
# hidden from its file viewer, like the provider credentials stored beside it.
STATE_RELATIVE = Path("cli-auth") / "railway-template" / "owner-applied.json"
RUNTIME_USER = "mobius"
MIN_PASSWORD = 12
MAX_PASSWORD = 1024  # upstream SetupRequest limit
MAX_USERNAME = 64  # upstream Owner.username column
PBKDF2_ROUNDS = 200_000


class BootstrapError(Exception):
  """The owner could not be ensured; the server must not start."""


def log(message: str) -> None:
  print(f"[railway] {message}", file=sys.stderr, flush=True)


def credential_problem(username: str, password: str) -> str | None:
  """Why a username/password pair cannot be used, or None."""
  if not username:
    return "MOBIUS_OWNER_USERNAME is empty"
  if len(username) > MAX_USERNAME:
    return f"MOBIUS_OWNER_USERNAME is longer than {MAX_USERNAME} characters"
  if any(ord(ch) < 32 or ord(ch) == 127 for ch in username):
    return "MOBIUS_OWNER_USERNAME contains control characters"
  if not password.strip():
    return "MOBIUS_OWNER_PASSWORD is empty"
  if len(password) < MIN_PASSWORD:
    return f"MOBIUS_OWNER_PASSWORD is shorter than {MIN_PASSWORD} characters"
  if len(password) > MAX_PASSWORD:
    return f"MOBIUS_OWNER_PASSWORD is longer than {MAX_PASSWORD} characters"
  return None


# --- stash (root) -----------------------------------------------------------


def stash() -> int:
  username = os.environ.get("MOBIUS_OWNER_USERNAME", "").strip()
  password = os.environ.get("MOBIUS_OWNER_PASSWORD", "")
  try:
    user = pwd.getpwnam(RUNTIME_USER)
  except KeyError:
    log(f"FATAL: user '{RUNTIME_USER}' is missing from the image")
    return 1
  CREDENTIALS_DIR.mkdir(mode=0o700, exist_ok=True)
  os.chown(CREDENTIALS_DIR, user.pw_uid, user.pw_gid)
  os.chmod(CREDENTIALS_DIR, 0o700)
  payload = json.dumps({"username": username, "password": password})
  fd, temp = tempfile.mkstemp(dir=CREDENTIALS_DIR, prefix=".owner-")
  try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
      handle.write(payload)
    os.chown(temp, user.pw_uid, user.pw_gid)
    os.chmod(temp, 0o600)
    os.replace(temp, CREDENTIALS_FILE)
  finally:
    Path(temp).unlink(missing_ok=True)
  return 0


# --- apply (mobius user) ----------------------------------------------------


def read_stashed_credentials() -> tuple[str, str]:
  """The stashed pair (possibly empty strings); the file is removed."""
  try:
    raw = CREDENTIALS_FILE.read_text(encoding="utf-8")
  except FileNotFoundError:
    return "", ""
  except OSError as exc:
    raise BootstrapError(f"cannot read {CREDENTIALS_FILE}: {exc}") from exc
  finally:
    try:
      CREDENTIALS_FILE.unlink()
    except FileNotFoundError:
      pass
    except OSError as exc:
      log(f"WARNING: could not remove {CREDENTIALS_FILE}: {exc}")
  try:
    data = json.loads(raw)
  except ValueError as exc:
    raise BootstrapError("stashed owner credentials are not valid JSON") from exc
  username = data.get("username") if isinstance(data, dict) else None
  password = data.get("password") if isinstance(data, dict) else None
  if not isinstance(username, str) or not isinstance(password, str):
    raise BootstrapError("stashed owner credentials have an unexpected shape")
  return username.strip(), password


def pair_digest(username: str, password: str, salt: bytes) -> str:
  material = username.encode("utf-8") + b"\0" + password.encode("utf-8")
  return hashlib.pbkdf2_hmac("sha256", material, salt, PBKDF2_ROUNDS).hex()


def state_matches(path: Path, username: str, password: str) -> bool:
  try:
    state = json.loads(path.read_text(encoding="utf-8"))
    salt = bytes.fromhex(state["salt"])
    expected = state["digest"]
  except (OSError, ValueError, KeyError, TypeError):
    return False
  if not isinstance(expected, str):
    return False
  return hmac.compare_digest(pair_digest(username, password, salt), expected)


def write_state(path: Path, username: str, password: str) -> None:
  """Remember which variable pair was applied (salted PBKDF2, no password)."""
  path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
  salt = secrets.token_bytes(16)
  payload = json.dumps({
    "version": 1,
    "salt": salt.hex(),
    "digest": pair_digest(username, password, salt),
  })
  fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".owner-applied-")
  try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
      handle.write(payload)
      handle.flush()
      os.fsync(handle.fileno())
    os.chmod(temp, 0o600)
    os.replace(temp, path)
  finally:
    Path(temp).unlink(missing_ok=True)


def owner_table_exists(engine, table_name: str) -> bool:
  from sqlalchemy import inspect

  return table_name in inspect(engine).get_table_names()


def initialize_schema() -> None:
  """Create and migrate the schema exactly as the server's startup would.

  ``app.main._init_db`` is idempotent (create_all + the migration ledger), so
  the server's own startup later finds a current schema, as on any reboot.
  """
  import app.main as server

  result = server._init_db()
  gaps = tuple(getattr(result, "schema_gaps", ()) or ())
  if gaps:
    log("WARNING: database reports schema gaps after initialisation: " + ", ".join(gaps))


def write_service_token(auth, owner) -> None:
  # Same best-effort behaviour as upstream's POST /api/auth/setup.
  try:
    auth.write_service_token(owner.username, owner.token_epoch)
  except OSError as exc:
    log(f"WARNING: could not write the service token: {exc}")


def apply() -> int:
  backend = Path.cwd()
  if not (backend / "app" / "main.py").is_file():
    raise BootstrapError(f"{backend} is not a Möbius backend directory")
  sys.path.insert(0, str(backend))
  username, password = read_stashed_credentials()

  from app.config import get_settings

  settings = get_settings()
  if settings.mobius_sso_enabled:
    log("managed mobius.you sign-in is configured; local owner bootstrap skipped")
    return 0
  state_path = Path(settings.data_dir) / STATE_RELATIVE

  from app import auth, models
  from app.database import SessionLocal, engine

  table = models.Owner.__tablename__
  if not owner_table_exists(engine, table):
    problem = credential_problem(username, password)
    if problem:
      raise BootstrapError(f"no owner account exists yet and {problem}")
    log("first boot: initialising the database before the server starts")
    initialize_schema()
    if not owner_table_exists(engine, table):
      raise BootstrapError(f"table '{table}' is still missing after initialisation")

  with SessionLocal() as db:
    owner = db.query(models.Owner).first()
    if owner is None:
      problem = credential_problem(username, password)
      if problem:
        raise BootstrapError(f"no owner account exists yet and {problem}")
      owner = models.Owner(username=username, hashed_password=auth.hash_password(password))
      db.add(owner)
      db.flush()
      if db.query(models.Owner).count() != 1:
        db.rollback()
        raise BootstrapError("more than one owner row would exist; refusing")
      db.commit()
      db.refresh(owner)
      write_service_token(auth, owner)
      write_state(state_path, username, password)
      log(f"owner account '{username}' created from MOBIUS_OWNER_USERNAME / MOBIUS_OWNER_PASSWORD")
      return 0

    if not username and not password:
      log("owner account exists; owner variables are empty, nothing applied")
      return 0
    problem = credential_problem(username, password)
    if problem:
      raise BootstrapError(
        f"{problem}; fix the variable or clear both owner variables "
        "(the existing login stays unchanged)"
      )
    if getattr(owner, "auth_mode", "local") != "local":
      log("owner signs in through mobius.you; owner variables not applied")
      return 0
    if state_matches(state_path, username, password):
      log(f"owner account '{owner.username}' unchanged (variables already applied)")
      return 0
    if owner.username == username and auth.verify_password(password, owner.hashed_password):
      write_state(state_path, username, password)
      log(f"owner account '{username}' already matches the variables")
      return 0

    previous = owner.username
    owner.username = username
    owner.hashed_password = auth.hash_password(password)
    owner.token_epoch = (owner.token_epoch or 0) + 1
    db.commit()
    db.refresh(owner)
    write_service_token(auth, owner)
    write_state(state_path, username, password)
    log(
      f"owner login reset from Railway variables ('{previous}' -> '{username}'); "
      "all sessions were signed out"
    )
    return 0


def main(argv: list[str]) -> int:
  mode = argv[1] if len(argv) > 1 else ""
  if mode == "stash":
    return stash()
  if mode == "apply":
    try:
      return apply()
    except BootstrapError as exc:
      log(f"FATAL: {exc}")
      return 3
    except Exception as exc:  # noqa: BLE001 - any failure must stop the boot
      log(f"FATAL: owner bootstrap failed: {exc.__class__.__name__}: {exc}")
      return 4
  log("usage: owner_bootstrap.py stash|apply")
  return 64


if __name__ == "__main__":
  sys.exit(main(sys.argv))
