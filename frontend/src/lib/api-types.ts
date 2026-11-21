/** Consumed fields of the existing FastAPI schemas; no scientific contract added. */
export interface Source { path: string; sha256: string; calendar: string }
export interface Health { status: 'ok'; version: string; historical_source_available: boolean }
export interface Indicator { name: string; value: number | null; source: string; period: string; universe: string; aggregation: string; validation_status: string }
export interface Overview { source: Source; indicators: Indicator[]; limitations: string[] }
export interface Territories { source: Source; codes: string[]; total: number; offset: number; catalog_validation: string }
export interface HistoricalPoint { position: number; technical_date: string; observed: number }
export interface HistoricalSeries { source: Source; series: string; points: HistoricalPoint[]; limitations: string[] }
export interface Methodology { forecast_methods: string[]; allowed_cuts: number[]; horizon: 8; limitations: string[] }
export interface ForecastInput { series: string; cut: number; method: string; horizon: 8 }
export interface EvaluationRow { position: number; technical_date: string; yhat: number; observed: number | null; lo: number | null; hi: number | null }
export interface Retrospective {
  request: ForecastInput & { request_id: string; source_sha256: string }
  forecast: { status: string; fit_status: string; interval_level: number | null; warnings: { message: string }[]; points: unknown[] }
  evaluation: { rows: EvaluationRow[]; metrics: Record<string, number | null> }
  limitations: string[]
}
