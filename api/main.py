"""Local REST API. Start from this checkout with one Uvicorn worker."""
from dataclasses import asdict
import csv
import hashlib
import io
import json
import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import Body, Depends, FastAPI, Query, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.exceptions import HTTPException
from starlette.concurrency import run_in_threadpool

from app import retrospective as ia
from episentinel.data.csv_contract import FIELDS
from episentinel.data.csv_loader import load_csv
from episentinel.data.epidemiological_series import (
    CalendarMetadata, MunicipalIdentity, PeriodGrid, SeriesValidationError,
)
from episentinel.services.isolated_pipeline import PipelineConfig, run_pipeline
from . import schemas as s
from .store import SessionStore

ROOT = Path(__file__).resolve().parents[1]
MAX_BODY = 1024 * 1024
LIMITATIONS = [
    "Panel histórico: eventos 210+220 combinados, S53 sumada a S52 y ausencias completadas con cero.",
    "Fechas técnicas de siete días; no son calendario epidemiológico oficial.",
    "Selección manual retrospectiva sobre datos ya examinados; sin cohorte causal certificada ni prueba independiente.",
    "Las cargas B04/B05 no se conectan a B06; no se acredita riesgo ni se confirman brotes.",
]
bearer = HTTPBearer(auto_error=False)


class APIError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details


class BodyLimitMiddleware:
    """Bound all incoming bodies before parsing; uploads never spool to disk."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        chunks, total = [], 0
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            total += len(event.get("body", b""))
            if total > MAX_BODY:
                response = JSONResponse(status_code=413, content={"error": {
                    "code": "BODY_TOO_LARGE", "message": "Máximo 1 MiB por solicitud", "details": None},
                    "request_id": uuid4().hex})
                return await response(scope, receive, send)
            chunks.append(event.get("body", b""))
            if not event.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(root=ROOT, store=None):
    root = Path(root)
    store = store or SessionStore()
    app = FastAPI(title="EpiSentinel AI REST", version="2.0.0", openapi_url="/api/v1/openapi.json",
                  docs_url="/api/v1/docs", redoc_url="/api/v1/redoc",
                  responses={str(code): {"model": s.ErrorResponse} for code in (400, 401, 404, 413, 415, 422, 429, 500, 503, 504)})
    app.state.store = store
    app.add_middleware(BodyLimitMiddleware)
    origins = os.getenv("EPISENTINEL_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000").split(",")
    @app.middleware("http")
    async def request_identity(request, call_next):
        request.state.request_id = uuid4().hex
        try:
            response = await call_next(request)
        except Exception as exc:
            response = await unexpected(request, exc)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    def error_response(request, status, code, message, details=None):
        request_id = getattr(request.state, "request_id", uuid4().hex)
        return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details},
                            "request_id": request_id}, headers={"X-Request-ID": request_id, "Cache-Control": "no-store"})

    @app.exception_handler(APIError)
    async def api_error(request, exc):
        return error_response(request, exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # Exclude input values, including tokens and dataset content.
        details = [{"location": list(e["loc"]), "type": e["type"], "message": e["msg"]} for e in exc.errors()]
        return error_response(request, 422, "INVALID_REQUEST", "Entrada inválida", details)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(request, exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        logging.getLogger(__name__).error("API failure request_id=%s type=%s", request.state.request_id, type(exc).__name__)
        return error_response(request, 500, "INTERNAL_ERROR", "Fallo interno; conserve el identificador de solicitud")

    def token(credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
        value = credentials.credentials if credentials else ""
        try:
            store.check(value)
        except KeyError:
            raise APIError(401, "SESSION_INVALID", "Sesión ausente, desconocida o expirada")
        return value

    def dataset_entry(session_token, dataset_id):
        try:
            return store.get(session_token, dataset_id)
        except KeyError:
            raise APIError(404, "DATASET_NOT_FOUND", "Conjunto no disponible en esta sesión")

    def panel():
        try:
            frame, digest = ia.load_panel(root)
        except (OSError, ValueError) as exc:
            raise APIError(503, "HISTORICAL_SOURCE_UNAVAILABLE", "Panel histórico ausente o incompatible", {"type": type(exc).__name__})
        return frame, s.Source(path="data/processed/panel_casos.parquet", sha256=digest)

    @app.get("/api/v1/health", response_model=s.Health)
    def health():
        return s.Health(historical_source_available=(root / "data/processed/panel_casos.parquet").is_file())

    @app.get("/api/v1/overview", response_model=s.Overview)
    def overview():
        frame, source = panel()
        period = f"{frame.columns[0].isoformat()}/{frame.columns[-1].isoformat()}"
        indicators = [s.Indicator(name=name, value=value, source=source.sha256, period=period,
                                  universe=universe, aggregation=rule, validation_status="structural_only_not_epidemiological")
                      for name, value, universe, rule in (
                          ("historical_rows", len(frame), "all panel rows including special territories", "row count; no case aggregation"),
                          ("municipal_candidates", len(ia.candidates(frame)), "IA-I1 manual retrospective catalogue", "count of unique codes passing IA-I1 candidate filter"),
                          ("technical_positions", frame.shape[1], "original panel columns", "column count"))]
        return s.Overview(source=source, indicators=indicators, limitations=LIMITATIONS)

    @app.get("/api/v1/territories", response_model=s.Territories)
    def territories(offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=2000)):
        frame, source = panel()
        codes = ia.candidates(frame)
        return s.Territories(source=source, codes=codes[offset:offset + limit], total=len(codes), offset=offset)

    @app.get("/api/v1/series", response_model=s.HistoricalSeries)
    def series(series: str = Query(pattern=r"^[0-9]{5}$"), start: int = Query(0, ge=0, le=831),
               limit: int = Query(832, ge=1, le=832)):
        frame, source = panel()
        if series not in ia.candidates(frame):
            raise APIError(404, "SERIES_NOT_FOUND", "Serie municipal fuera del catálogo IA-I1")
        points = [s.HistoricalPoint(position=i, technical_date=date.isoformat(), observed=float(value))
                  for i, (date, value) in enumerate(frame.loc[series].items()) if start <= i < start + limit]
        return s.HistoricalSeries(source=source, series=series, points=points, limitations=LIMITATIONS)

    def catalogue(folder, pattern, limitations):
        items = []
        for path in sorted((root / folder).glob(pattern)):
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            evidence = json.loads(raw)
            item = {"path": path.relative_to(root).as_posix(), "sha256": digest, "evidence": evidence}
            if folder == "docs/experiments":
                item["indicators"] = [as_indicator(name, value, evidence["request"], evidence)
                                      for name, value in evidence["evaluation"]["metrics"].items()]
            else:
                item["metric_context"] = {
                    "source": digest, "period": evidence.get("created_utc", "not_recorded"),
                    "universe": "synthetic benchmark cases in evidence.results; not population observations",
                    "aggregation": evidence.get("methodology", {}),
                    "validation_status": "archived_synthetic_benchmark_not_reexecuted",
                }
            items.append(item)
        return s.Catalogue(items=items, limitations=limitations)

    @app.get("/api/v1/experiments", response_model=s.Catalogue)
    def experiments():
        return catalogue("docs/experiments", "ia_i1_*.json", LIMITATIONS)

    @app.get("/api/v1/benchmarks", response_model=s.Catalogue)
    def benchmarks():
        return catalogue("docs/benchmarks", "*.json", ["Benchmark sintético de rendimiento; no es evidencia epidemiológica ni rendimiento predictivo en población real."])

    @app.get("/api/v1/methodology", response_model=s.Methodology)
    def methodology():
        return s.Methodology(forecast_methods=list(ia.B06_METHODS), allowed_cuts=[o.cut for o in ia.allowed_plan().origins],
                             horizon=8, timeout_s=ia.MAX_SECONDS, max_concurrent_forecasts_per_process=1,
                             csv_fields=list(FIELDS), documents=["docs/IA_I1.md", "docs/B04_CSV_LOADER.md", "docs/CONTRATO_PIPELINE_B05.md",
                             "docs/CONTRATO_SERIES_B03.md", "docs/CONTRATO_PRONOSTICO_B06.md", "docs/CONTRATO_EVALUACION_B10.md"], limitations=LIMITATIONS)

    @app.post("/api/v1/forecasts/retrospective", response_model=s.Retrospective)
    def retrospective(body: s.ForecastInput):
        frame, source = panel()
        try:
            request = ia.prepare(frame, source.sha256, body.series, body.cut, body.method)
        except ValueError as exc:
            raise APIError(422, "FORECAST_INELIGIBLE", str(exc))
        result = ia.execute_bounded(request)
        if result["status"] != "ok":
            code = (result.get("error") or {}).get("code", "FORECAST_ERROR")
            status = {"BUSY": 429, "TIMEOUT": 504, "WORKER_ERROR": 503}.get(code, 422)
            # Worker stderr may contain internal paths; only expose scientific diagnostics.
            safe = {k: v for k, v in result.items() if k != "error"}
            safe["error"] = {k: v for k, v in (result.get("error") or {}).items()
                             if k != "details" or code != "WORKER_ERROR"}
            raise APIError(status, code, "El pronóstico no produjo una curva válida", safe)
        output = ia.evidence(request, result, frame.loc[body.series])
        output["indicators"] = [as_indicator(name, value, request, output) for name, value in output["evaluation"]["metrics"].items()]
        return output

    def as_indicator(name, value, request, output):
        rules = {"MAE": "B10 mae: mean absolute error over all 8 aligned targets", "RMSE": "B10 rmse: square root of mean squared error over all 8 aligned targets",
                 "MASE": "B10 mase: MAE divided by mean absolute seasonal difference of training prefix only, m=52",
                 "Cobertura intervalo nominal": "B10 cobertura_intervalo: fraction of 8 targets inside nominal interval",
                 "Ancho medio intervalo": "mean(hi-lo) over all 8 nominal intervals"}
        rows = output["evaluation"]["rows"]
        return s.Indicator(name=name, value=value, source=request["source_sha256"],
                           period=f"{rows[0]['technical_date']}/{rows[-1]['technical_date']}",
                           universe=f"series={request['series']}; positions={request['cut']+1}..{request['cut']+8}; n=8",
                           aggregation=rules[name], validation_status="retrospective_technical_only" if value is not None else "unavailable").model_dump()

    @app.post("/api/v1/sessions", response_model=s.Session, status_code=201)
    def new_session():
        try:
            return s.Session(token=store.create(), expires_in_s=store.ttl)
        except OverflowError as exc:
            raise APIError(429, "CAPACITY_REACHED", str(exc))

    @app.delete("/api/v1/sessions/current", status_code=204)
    def delete_session(session_token: str = Depends(token)):
        try:
            store.delete(session_token)
        except KeyError:
            raise APIError(401, "SESSION_INVALID", "Sesión expirada")
        return Response(status_code=204)

    def ingest(payload, name, session_token):
        loaded = load_csv(payload, source_name=name)
        if loaded.blocked:
            raise APIError(422, "CSV_REJECTED", "B04 rechazó el conjunto completo; no se almacenaron filas", loaded.report)
        response = dict(dataset_id=uuid4().hex, source=loaded.source, sha256=loaded.sha256,
                        contract_version=loaded.contract_version, report=loaded.report,
                        pending_decisions=loaded.pending_decisions, records=loaded.data)
        try:
            store.put(session_token, payload, response)
        except OverflowError as exc:
            raise APIError(429, "CAPACITY_REACHED", str(exc))
        except KeyError:
            raise APIError(401, "SESSION_INVALID", "Sesión expirada")
        return response

    @app.post("/api/v1/datasets/upload", response_model=s.Dataset, status_code=201)
    async def upload(request: Request, payload: bytes = Body(media_type="text/csv"), session_token: str = Depends(token)):
        if request.headers.get("content-type", "").split(";")[0].lower() != "text/csv":
            raise APIError(415, "UNSUPPORTED_MEDIA_TYPE", "Enviar bytes UTF-8 con Content-Type: text/csv")
        name = request.headers.get("x-filename", "upload.csv")
        name = name.replace("\\", "/").split("/")[-1][:128] or "upload.csv"
        return await run_in_threadpool(ingest, payload, name, session_token)

    @app.post("/api/v1/datasets/manual", response_model=s.Dataset, status_code=201)
    def manual(body: s.ManualInput, session_token: str = Depends(token)):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(row.model_dump() for row in body.rows)
        return ingest(stream.getvalue().encode("utf-8"), "manual.csv", session_token)

    @app.get("/api/v1/datasets/{dataset_id}", response_model=s.Dataset)
    def get_dataset(dataset_id: str, session_token: str = Depends(token)):
        return dataset_entry(session_token, dataset_id)[1]

    @app.delete("/api/v1/datasets/{dataset_id}", status_code=204)
    def delete_dataset(dataset_id: str, session_token: str = Depends(token)):
        try:
            store.delete(session_token, dataset_id)
        except KeyError:
            raise APIError(404, "DATASET_NOT_FOUND", "Conjunto no disponible en esta sesión")
        return Response(status_code=204)

    @app.post("/api/v1/datasets/{dataset_id}/series", response_model=s.PipelineOutput)
    def build_dataset_series(dataset_id: str, body: s.PipelineInput, session_token: str = Depends(token)):
        payload, record = dataset_entry(session_token, dataset_id)
        try:
            config = PipelineConfig(body.version, MunicipalIdentity(body.territory), tuple(body.event_codes),
                                    PeriodGrid(tuple(body.periods), CalendarMetadata(**body.calendar.model_dump())))
        except SeriesValidationError as exc:
            raise APIError(422, exc.code, str(exc))
        result = run_pipeline(payload, config=config, source_name=record["source"])
        if result.status != "completed":
            raise APIError(422, "PIPELINE_BLOCKED", "B05 no construyó una serie", asdict(result))
        return {"dataset_id": dataset_id, **asdict(result)}

    # Outermost application middleware also covers structured unexpected errors.
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in origins if o.strip()],
                       allow_methods=["GET", "POST", "DELETE"],
                       allow_headers=["Authorization", "Content-Type", "X-Filename"],
                       expose_headers=["X-Request-ID"], allow_credentials=False)
    return app


app = create_app()
