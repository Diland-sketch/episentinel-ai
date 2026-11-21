"""Read-only remote acceptance by default. --forecast explicitly runs real B06."""
import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("api_url", help="Exact https://<backend>/api/v1")
    parser.add_argument("--frontend-origin", required=True)
    parser.add_argument("--forecast", choices=["ultimo_valor", "sarima_sin_estacional"])
    args = parser.parse_args()
    url = urlsplit(args.api_url)
    origin = urlsplit(args.frontend_origin)
    if (url.scheme != "https" or url.username or url.query or url.fragment or url.path != "/api/v1"
            or origin.scheme != "https" or origin.username or origin.path or origin.query or origin.fragment):
        parser.error("Use exact public HTTPS URLs without credentials or query strings")
    operator_key = os.getenv("EPISENTINEL_OPERATOR_KEY")
    if args.forecast and not operator_key:
        parser.error("--forecast requires EPISENTINEL_OPERATOR_KEY in the process environment")

    def request(path, body=None, headers=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        req = Request(args.api_url + path, data=data, headers=request_headers, method=method)
        try:
            with urlopen(req, timeout=120) as r:
                content = r.read()
                return r.status, r.headers, json.loads(content) if content else None
        except HTTPError as exc:
            content = exc.read()
            return exc.code, exc.headers, json.loads(content) if content else None

    report = {}
    for path in ("/health", "/ready", "/capabilities", "/overview", "/openapi.json", "/series?series=76001"):
        status, headers, body = request(path, headers={"Origin": args.frontend_origin})
        if status != 200 or headers.get("Access-Control-Allow-Origin") != args.frontend_origin:
            raise SystemExit("Remote verification failed: " + path)
        report[path] = status
        if path == "/overview":
            expected = json.loads((Path(__file__).resolve().parents[1] / "deploy/panel-manifest.json").read_text())["sha256"]
            if body["source"]["sha256"] != expected:
                raise SystemExit("Historical source identity mismatch")
        if path == "/capabilities":
            capabilities = body
        if path == "/openapi.json" and "OperatorKey" not in body["components"]["securitySchemes"]:
            raise SystemExit("Public authentication contract missing")
    status, _, _ = request("/forecasts/retrospective", {"series": "76001", "cut": 779, "method": "ultimo_valor"})
    if status != 401:
        raise SystemExit("Anonymous costly operation must return 401")
    report["anonymous_forecast_rejected"] = status
    status, headers, _ = request("/forecasts/retrospective", headers={"Origin": args.frontend_origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "x-operator-key,content-type"}, method="OPTIONS")
    if status != 200 or headers.get("Access-Control-Allow-Origin") != args.frontend_origin:
        raise SystemExit("CORS preflight failed")
    if args.forecast:
        if args.forecast not in capabilities["forecast_methods"]:
            raise SystemExit("Requested method is explicitly disabled; no substitution")
        status, _, body = request("/forecasts/retrospective", {"series": "76001", "cut": 779, "horizon": 8, "method": args.forecast}, {"X-Operator-Key": operator_key})
        if status != 200 or body["request"]["method"] != args.forecast or len(body["forecast"]["points"]) != 8:
            raise SystemExit("Real forecast rejected; no fallback or retry")
        report["forecast"] = {"method": args.forecast, "fit_status": body["forecast"]["fit_status"], "request_id": body["request"]["request_id"], "metrics": body["evaluation"]["metrics"]}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
