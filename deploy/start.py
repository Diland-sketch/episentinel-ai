"""Render entrypoint: hydrate exact source, then one Uvicorn worker."""
import os
import sys
from .provision import provision, ProvisionError


def main():
    try:
        provision()
        port = int(os.getenv("PORT", "10000"))
        if not 1 <= port <= 65535:
            raise ValueError("port")
        # Validate fail-closed public configuration before accepting traffic.
        from api.render import application
        application()
    except (ProvisionError, ValueError) as exc:
        print("Startup refused: " + (str(exc) if isinstance(exc, ProvisionError) else "INVALID_PUBLIC_CONFIGURATION"), file=sys.stderr)
        raise SystemExit(1)
    # Storage credentials are only needed during hydration, not by API/model children.
    for name in ("EPISENTINEL_PANEL_URL", "EPISENTINEL_PANEL_BEARER"):
        os.environ.pop(name, None)
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "api.render:application", "--factory",
                             "--host", "0.0.0.0", "--port", str(port), "--workers", "1",
                             "--limit-concurrency", "4", "--timeout-keep-alive", "5", "--no-access-log"])


if __name__ == "__main__":
    main()
