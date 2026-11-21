"""Real Linux cgroup/RSS profiling; run in a 512 MiB Docker container, not Render."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def rss(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError):
        pass
    return 0


def cg(name):
    try:
        return int(Path("/sys/fs/cgroup/" + name).read_text())
    except (OSError, ValueError):
        return None


def main():
    started_utc = datetime.now(timezone.utc).isoformat()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a NEW evidence path")
    if cg("memory.max") != 512 * 1024**2:
        parser.error("Run with Docker --memory=512m --memory-swap=512m")
    env = dict(os.environ)
    key = secrets.token_urlsafe(32)
    env.update(EPISENTINEL_OPERATOR_KEY=key, EPISENTINEL_CORS_ORIGINS="https://frontend.example.org",
               EPISENTINEL_FORECAST_METHODS="ultimo_valor,sarima_sin_estacional", EPISENTINEL_SARIMA_ACCEPTED="1", PORT="10000")
    source = Path(env["EPISENTINEL_PANEL_FILE"])
    inspect_code = "import json,pandas as pd; f=pd.read_parquet(__import__('sys').argv[1]); print(json.dumps({'shape':list(f.shape),'decoded_dataframe_bytes':int(f.memory_usage(index=True,deep=True).sum()),'columns_type':type(f.columns).__name__,'index_type':str(f.index.dtype),'only_numeric_values':all(pd.api.types.is_numeric_dtype(t) for t in f.dtypes)}))"
    info = json.loads(subprocess.check_output([sys.executable, "-c", inspect_code, str(source)], env=env, text=True))
    info.update(bytes=source.stat().st_size, sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    process = subprocess.Popen([sys.executable, "-m", "deploy.start"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    phase = "startup"
    peaks, samples = {}, {}
    stop = threading.Event()

    def monitor():
        while not stop.wait(.01):
            name = phase
            parent = rss(process.pid)
            children = 0
            for entry in Path("/proc").iterdir():
                if entry.name.isdigit():
                    try:
                        status = (entry / "status").read_text()
                        if f"PPid:\t{process.pid}\n" in status:
                            children += rss(int(entry.name))
                    except OSError:
                        pass
            sample = {"server_rss_bytes": parent, "forecast_children_rss_bytes": children, "cgroup_current_bytes": cg("memory.current") or 0}
            existing = peaks.setdefault(name, {k: 0 for k in sample})
            for k, v in sample.items():
                existing[k] = max(existing[k], v)
            samples[name] = samples.get(name, 0) + 1

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    results = []

    def request(path, body=None):
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json", "X-Operator-Key": key}
        try:
            with urlopen(Request("http://127.0.0.1:10000/api/v1/" + path, data=data, headers=headers), timeout=55) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)

    try:
        start = time.monotonic()
        while True:
            if process.poll() is not None:
                raise RuntimeError("Server failed before ready; no credentials printed")
            try:
                status, result = request("ready")
                if status == 200:
                    break
            except URLError:
                pass
            if time.monotonic() - start > 90:
                raise RuntimeError("Startup timeout")
            time.sleep(.1)
        results.append({"phase": "startup", "status": status, "elapsed_s": time.monotonic() - start})
        for name, path in (("overview", "overview"), ("series", "series?series=76001")):
            phase = name
            start = time.monotonic()
            status, response = request(path)
            results.append({"phase": name, "status": status, "elapsed_s": time.monotonic() - start})
        for method in ("ultimo_valor", "sarima_sin_estacional"):
            phase = method
            start = time.monotonic()
            status, response = request("forecasts/retrospective", {"series": "76001", "cut": 779, "horizon": 8, "method": method})
            record = {"phase": method, "status": status, "elapsed_s": time.monotonic() - start}
            if status == 200:
                reference = json.loads((ROOT / f"docs/experiments/ia_i1_cali_779_{method}.json").read_text())
                rows = response["evaluation"]["rows"]
                actual, expected = response["forecast"]["points"], reference["forecast"]["points"]
                strict = all(abs(a[k] - b[k]) <= 1e-8 * abs(b[k]) for a, b in zip(actual, expected) for k in ("yhat", "lo", "hi") if a[k] is not None and b[k] is not None)
                max_delta = max(abs(a[k] - b[k]) for a, b in zip(actual, expected) for k in ("yhat", "lo", "hi") if a[k] is not None and b[k] is not None)
                phase = "direct_b06_control_" + method
                control = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/run_retrospective.py"), "--worker"],
                                         input=json.dumps(response["request"]), text=True, capture_output=True, timeout=45, env=env, check=True)
                direct = json.loads(control.stdout)
                record.update(metrics=response["evaluation"]["metrics"], fit_status=response["forecast"]["fit_status"],
                              experiment={k: response["request"][k] for k in ("request_id", "source_sha256", "series", "cut", "horizon", "method")},
                              indicators=response["indicators"],
                              observed=[r["observed"] for r in rows], diagnostics=response["forecast"]["diagnostics"],
                              historical_predictions_intervals_match_rtol_1e8=strict,
                              historical_max_absolute_difference=max_delta,
                              same_runtime_direct_b06_points_exact_match=actual == direct["points"],
                              same_runtime_direct_b06_fit_status_match=response["forecast"]["fit_status"] == direct["fit_status"])
            else:
                record["error"] = response.get("error", {}).get("code")
            results.append(record)
    finally:
        stop.set()
        thread.join()
        process.terminate()
        process.wait(timeout=10)
    evidence = {"schema": "episentinel-render-memory-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
                "platform": platform.platform(), "python": platform.python_version(), "panel": info,
                "code_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
                    "api/render.py", "api/main.py", "app/retrospective.py", "scripts/run_retrospective.py",
                    "scripts/profile_render.py", "deploy/requirements.lock", "deploy/provision.py", "deploy/start.py")},
                "dependencies": {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "statsmodels", "scipy", "pyarrow", "fastapi")},
                "memory_max_bytes": cg("memory.max"), "memory_swap_max_bytes": cg("memory.swap.max"),
                "cpu_max": Path("/sys/fs/cgroup/cpu.max").read_text().strip(), "cgroup_lifetime_peak_bytes": cg("memory.peak"),
                "memory_events": Path("/sys/fs/cgroup/memory.events").read_text(),
                "measurement_context": {"source": "Linux /proc VmRSS and cgroup v2 memory.current, memory.peak, memory.events",
                    "period": {"started_utc": started_utc, "ended_utc": datetime.now(timezone.utc).isoformat()},
                    "universe": "One local 512 MiB container, server and children; Cali 76001, cut 779, horizon 8",
                    "aggregation": "Maximum of 10 ms samples per phase; cgroup lifetime peak read from kernel; elapsed wall time per HTTP request",
                    "validation_status": "measured_local_docker_not_Render_hardware"},
                "sampling_interval_s": .01, "phase_sample_counts": samples, "peaks": peaks, "results": results,
                "limitations": ["Local Docker Linux evidence, not a measurement on Render hardware", "Cgroup includes profiler, server, children, kernel and page cache", "RSS sums share pages and are not unique physical memory", "One manually selected Cali origin; not a benchmark over all municipalities", "CPU quota .5 is a local test configuration, not a claimed Render CPU guarantee", "No RSS hard limit per request; container OOM could kill the service"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(evidence, handle, indent=2, allow_nan=False)
    print(json.dumps(evidence, indent=2))
    if any(r["status"] != 200 for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
