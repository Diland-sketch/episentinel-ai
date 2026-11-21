"""Versioned HTTP contract. Canonical input validation is delegated to B04/B05."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Error(Model):
    code: str
    message: str
    details: Any = None


class ErrorResponse(Model):
    error: Error
    request_id: str


class Health(Model):
    status: Literal["ok"] = "ok"
    version: str = "2.0.0"
    historical_source_available: bool


class Source(Model):
    path: str
    sha256: str
    calendar: str = "technical_7D_not_official"


class Indicator(Model):
    name: str
    value: float | int | None
    source: str
    period: str
    universe: str
    aggregation: str
    validation_status: str


class Overview(Model):
    source: Source
    indicators: list[Indicator]
    limitations: list[str]


class Territories(Model):
    source: Source
    codes: list[str]
    total: int
    offset: int
    catalog_validation: str = "pending"


class HistoricalPoint(Model):
    position: int
    technical_date: str
    observed: float


class HistoricalSeries(Model):
    source: Source
    series: str
    points: list[HistoricalPoint]
    limitations: list[str]


class ForecastInput(Model):
    series: str = Field(pattern=r"^[0-9]{5}$")
    cut: StrictInt
    method: Literal["ultimo_valor", "ingenua_estacional", "sarima_sin_estacional", "sarima_estacional"]
    horizon: Literal[8] = 8


class ForecastPoint(Model):
    date: str
    yhat: float
    lo: float | None
    hi: float | None


class Forecast(Model):
    request_id: str
    status: str
    fit_status: str
    points: list[ForecastPoint]
    interval_level: float | None
    parameters: dict[str, Any]
    diagnostics: dict[str, Any] | None
    error: dict[str, Any] | None
    warnings: list[dict[str, Any]]
    elapsed_s: float | None = None


class EvaluationRow(ForecastPoint):
    position: int
    technical_date: str
    observed: float | None


class Evaluation(Model):
    rows: list[EvaluationRow]
    metrics: dict[str, float | None]
    limitations: list[str]


class ExperimentRequest(Model):
    version: str
    source_sha256: str
    series: str
    cut: int
    method: str
    horizon: int
    alpha: float
    partition: str
    protocol: dict[str, int]
    dates: list[str]
    values: list[float | None]
    temporal_scope: str
    request_id: str


class Retrospective(Model):
    schema_: str = Field(alias="schema")
    created_utc: str
    request: ExperimentRequest
    forecast: Forecast
    evaluation: Evaluation
    environment: dict[str, str]
    limitations: list[str]
    indicators: list[Indicator]


class Session(Model):
    token: str
    expires_in_s: int


class ManualRow(Model):
    cod_mun: StrictStr
    ano: StrictInt
    semana: StrictInt
    cod_eve: StrictInt
    conteo: StrictInt


class ManualInput(Model):
    rows: list[ManualRow] = Field(min_length=1, max_length=1000)


class Dataset(Model):
    dataset_id: str
    source: str
    sha256: str
    contract_version: str
    report: dict[str, Any]
    pending_decisions: list[dict[str, str]]
    records: list[dict[str, Any]]
    trained: Literal[False] = False
    forecast_eligibility: str = "not_evaluated"


class Calendar(Model):
    calendar_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source: str = Field(min_length=1)
    # A client assertion is not accredited evidence.
    verification: Literal["unverified"] = "unverified"


class PipelineInput(Model):
    version: str = Field(min_length=1, max_length=100)
    territory: str = Field(pattern=r"^[0-9]{5}$")
    event_codes: list[StrictInt] = Field(min_length=1, max_length=3)
    periods: list[tuple[StrictInt, StrictInt]] = Field(min_length=1, max_length=832)
    calendar: Calendar


class PipelineOutput(Model):
    dataset_id: str
    status: str
    config: dict[str, Any] | None
    load_diagnostic: dict[str, Any] | None
    series: dict[str, Any] | None
    warnings: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    trained: Literal[False] = False


class Catalogue(Model):
    items: list[dict[str, Any]]
    limitations: list[str]


class Methodology(Model):
    forecast_methods: list[str]
    allowed_cuts: list[int]
    horizon: int
    timeout_s: int
    max_concurrent_forecasts_per_process: int
    csv_fields: list[str]
    documents: list[str]
    limitations: list[str]
