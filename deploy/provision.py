"""Runtime-only exact-byte provisioning. URLs and credentials are never logged."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

MANIFEST = Path(__file__).with_name("panel-manifest.json")


class ProvisionError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ProvisionError("PANEL_REDIRECT_REJECTED")


def verify(path, manifest):
    if path.stat().st_size != manifest["bytes"]:
        raise ProvisionError("PANEL_SIZE_MISMATCH")
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ProvisionError("PANEL_HASH_MISMATCH")
    # Import only after byte identity is established. No schema conversion.
    from app.retrospective import load_panel
    frame, digest = load_panel(path.parents[2])
    if frame.shape != (manifest["rows"], manifest["positions"]):
        raise ProvisionError("PANEL_SHAPE_MISMATCH")
    return digest


def provision(environ=None, opener=None):
    env = os.environ if environ is None else environ
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if env.get("EPISENTINEL_PANEL_APPROVED_SHA256") != manifest["sha256"]:
        raise ProvisionError("PANEL_CUSTODIAN_APPROVAL_REQUIRED")
    root = Path(env.get("EPISENTINEL_RUNTIME_ROOT", "/tmp/episentinel")).resolve()
    target = root / "data/processed/panel_casos.parquet"
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.exists():
        verify(target, manifest)
        return target
    source = env.get("EPISENTINEL_PANEL_FILE")
    url = env.get("EPISENTINEL_PANEL_URL")
    if bool(source) == bool(url):
        raise ProvisionError("PANEL_SELECT_EXACTLY_ONE_SOURCE")
    temp_root = Path(tempfile.mkdtemp(prefix="panel-", dir=root))
    staged = temp_root / "data/processed/panel_casos.parquet"
    staged.parent.mkdir(parents=True)
    try:
        if source:
            # Render Secret File or an explicitly mounted local file, not an image asset.
            with Path(source).open("rb") as reader, staged.open("xb") as writer:
                copy_bounded(reader, writer, manifest["bytes"])
        else:
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                    or parsed.fragment or parsed.port not in (None, 443)
                    or parsed.hostname != env.get("EPISENTINEL_PANEL_HOST")):
                raise ProvisionError("PANEL_SOURCE_NOT_ALLOWED")
            request = Request(url)
            token = env.get("EPISENTINEL_PANEL_BEARER")
            if token:
                request.add_header("Authorization", "Bearer " + token)
            client = opener or build_opener(NoRedirect())
            with client.open(request, timeout=20) as reader, staged.open("xb") as writer:
                copy_bounded(reader, writer, manifest["bytes"])
        verify(staged, manifest)
        # Refuse replacement, including simultaneous provisioning attempts.
        with staged.open("rb") as reader, target.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
        target.chmod(0o600)
        return target
    except ProvisionError:
        raise
    except Exception:
        # Never echo a signed URL, secret, response body, or exception text.
        raise ProvisionError("PANEL_PROVISION_FAILED") from None
    finally:
        if temp_root.resolve().parent != root:
            raise ProvisionError("PANEL_TEMP_PATH_INVALID")
        shutil.rmtree(temp_root)


def copy_bounded(reader, writer, maximum):
    size, start = 0, time.monotonic()
    while True:
        chunk = reader.read(min(65536, maximum - size + 1))
        if not chunk:
            break
        size += len(chunk)
        if size > maximum or time.monotonic() - start > 45:
            raise ProvisionError("PANEL_TRANSFER_LIMIT")
        writer.write(chunk)
