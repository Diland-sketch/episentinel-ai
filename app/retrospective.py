"""Historical-only B06 consumer. Prefix-only fitting and separate retrospective evaluation."""
from collections.abc import Mapping
from datetime import datetime,timezone
import hashlib,json,math,os,platform,subprocess,sys,threading,time
from numbers import Real
from pathlib import Path
import numpy as np
import pandas as pd
from episentinel.evaluation.temporal_protocol import TemporalProtocol,B06_METHODS
from episentinel.evaluation.rolling_origin import plan_rolling_origin
from episentinel.evaluation.forecast_metrics import mae,rmse,mase,cobertura_intervalo

ROOT=Path(__file__).resolve().parents[1]
MAX_SECONDS=45
SLOT=threading.BoundedSemaphore(1)
VERSION="ia-i1-historical-b06-v1"


def plain(value):
    if isinstance(value,Mapping): return {k:plain(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)): return [plain(v) for v in value]
    if isinstance(value,np.generic): return value.item()
    return value


def load_panel(root=ROOT):
    path=Path(root)/"data/processed/panel_casos.parquet"
    frame=pd.read_parquet(path)
    if not isinstance(frame.columns,pd.DatetimeIndex) or frame.columns.tz is not None:
        raise ValueError("El panel debe conservar su DatetimeIndex técnico original; no se generan fechas alternativas")
    frame.index=frame.index.astype(str)
    if not frame.index.is_unique: raise ValueError("Identidad territorial duplicada")
    if frame.shape[1]!=832: raise ValueError("IA-I1 requiere la malla histórica revisada de 832 posiciones")
    return frame,hashlib.sha256(path.read_bytes()).hexdigest()


def allowed_plan():
    return plan_rolling_origin(TemporalProtocol(728,780,832))


def candidates(frame):
    # Explicit manual catalogue, lexical order. Never rank using future counts.
    return sorted(c for c in frame.index if len(c)==5 and c.isdigit() and not c.startswith("01") and not c.endswith("000"))


def prepare(frame,digest,code,cut,method):
    if code not in candidates(frame): raise ValueError("Seleccione un municipio disponible del catálogo retrospectivo")
    if method not in B06_METHODS: raise ValueError("Método B06 no permitido")
    origin=next((o for o in allowed_plan().origins if type(cut) is int and o.cut==cut),None)
    if origin is None: raise ValueError("Corte fuera de la cuadrícula B10 permitida")
    series=frame.loc[code]
    prefix=series.iloc[:cut+1]
    dates=prefix.index
    if dates.hasnans or not dates.is_unique or not dates.is_monotonic_increasing or not all(d==pd.Timedelta(days=7) for d in dates[1:]-dates[:-1]):
        raise ValueError("Prefijo incompatible: fechas técnicas no únicas, crecientes o separadas exactamente siete días. No se corrige el índice")
    values=[None if pd.isna(v) else plain(v) for v in prefix.tolist()]
    request={"version":VERSION,"source_sha256":digest,"series":code,"cut":cut,"method":method,"horizon":8,"alpha":0.05,
             "partition":origin.partition,"protocol":{"train_size":728,"validation_end":780,"total_size":832},
             "dates":[d.isoformat() for d in dates],"values":values,
             "temporal_scope":"Original technical 7D index; not official epidemiological calendar"}
    request["request_id"]=hashlib.sha256(json.dumps(request,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return request


def fit_prefix(request):
    """Worker only: receives no future observations or dates."""
    from episentinel.services import generar_pronostico
    if request["horizon"]!=8 or len(request["values"])>832 or len(request["values"])!=request["cut"]+1:
        raise ValueError("Worker request exceeds bounded prefix/horizon")
    series=pd.Series(request["values"],index=pd.DatetimeIndex(request["dates"]),dtype=object)
    start=time.perf_counter()
    result=generar_pronostico(series,request["cut"],8,request["method"],alpha=request["alpha"])
    error=None if result.error is None else {"code":result.error.codigo,"field":result.error.campo,
        "message":result.error.mensaje,"details":plain(result.error.detalles)}
    points=[]
    if result.estado_ejecucion=="ok":
        predictions=result.predicciones
        intervals=result.intervalos
        for date,row in predictions.iterrows():
            points.append({"date":date.isoformat(),"yhat":float(row.yhat),
                "lo":float(intervals.loc[date,"lo"]) if intervals is not None else None,
                "hi":float(intervals.loc[date,"hi"]) if intervals is not None else None})
    return {"request_id":request["request_id"],"status":result.estado_ejecucion,"fit_status":result.estado_ajuste,
            "points":points,"interval_level":result.nivel_intervalo,"parameters":plain(result.parametros),
            "diagnostics":plain(result.diagnostico_ajuste),"error":error,
            "warnings":[{"code":w.codigo,"message":w.mensaje,"phase":w.fase} for w in result.advertencias],
            "elapsed_s":time.perf_counter()-start}


def failure(request,code,message):
    return {"request_id":request["request_id"],"status":"error","fit_status":"no_evaluado","points":[],
            "interval_level":None,"diagnostics":None,"parameters":{},"warnings":[],
            "error":{"code":code,"message":message}}


def execute_bounded(request,timeout=MAX_SECONDS):
    if not 1<=timeout<=MAX_SECONDS: raise ValueError("Tiempo permitido: 1 a 45 segundos")
    if not SLOT.acquire(blocking=False): return failure(request,"BUSY","Otro ensayo está en ejecución; espere antes de volver a intentar")
    try:
        env=dict(os.environ,OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1",NUMEXPR_NUM_THREADS="1")
        process=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/run_retrospective.py"),"--worker"],
            input=json.dumps(request,allow_nan=False),text=True,encoding="utf-8",capture_output=True,
            timeout=timeout,env=env,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if process.returncode:
            failed=failure(request,"WORKER_ERROR","El proceso no produjo un resultado válido; consulte el diagnóstico")
            failed["error"]["details"]={"exit_code":process.returncode,"stderr":process.stderr[-1500:]}
            return failed
        output=json.loads(process.stdout)
        if output.get("request_id")!=request["request_id"]: return failure(request,"IDENTITY_MISMATCH","La respuesta no corresponde a esta solicitud")
        return output
    except subprocess.TimeoutExpired: return failure(request,"TIMEOUT","Se alcanzó el límite de tiempo; proceso terminado, sin curva parcial")
    except (OSError,ValueError) as exc: return failure(request,"WORKER_ERROR",str(exc))
    finally: SLOT.release()


def evaluate(request,result,series):
    """Post-fit only. Full horizon or explicit unavailable metrics; no truncation."""
    if result["request_id"]!=request["request_id"]:raise ValueError("Resultado asociado a una configuración distinta")
    if result["status"]!="ok": return [],{},["Pronóstico fallido o rechazado; sin métricas"]
    expected=pd.date_range(pd.Timestamp(request["dates"][-1])+pd.Timedelta(days=7),periods=8,freq="7D")
    points=result["points"]
    if len(points)!=8 or [p["date"] for p in points]!=[d.isoformat() for d in expected]:
        return [],{},["Predicciones no alineadas con los ocho objetivos previstos"]
    rows=[]
    for step,(date,prediction) in enumerate(zip(expected,points),1):
        position=request["cut"]+step
        available=position<len(series) and series.index[position]==date
        value=series.iloc[position] if available else None
        valid=not isinstance(value,(bool,np.bool_)) and isinstance(value,Real) and math.isfinite(float(value)) and value>=0
        rows.append({"position":position,"technical_date":date.isoformat(),"observed":float(value) if valid else None,**prediction})
    if any(r["observed"] is None for r in rows):return rows,{},["Objetivos ausentes, inválidos o desalineados: no se evalúa un horizonte parcial"]
    y=[r["observed"] for r in rows]; p=[r["yhat"] for r in rows]
    train=request["values"]
    scaled=mase(y,p,train,m=52)
    metrics={"MAE":mae(y,p),"RMSE":rmse(y,p),"MASE":scaled if math.isfinite(scaled) else None}
    for name,value in list(metrics.items()):
        if value is not None and not math.isfinite(value):metrics[name]=None
    reasons=[] if metrics["MASE"] is not None else ["MASE no disponible: prefijo insuficiente o escala estacional de entrenamiento igual a cero"]
    if result["interval_level"] is not None:
        metrics["Cobertura intervalo nominal"]=cobertura_intervalo(y,[r["lo"] for r in rows],[r["hi"] for r in rows])
        metrics["Ancho medio intervalo"]=float(np.mean([r["hi"]-r["lo"] for r in rows]))
    return rows,metrics,reasons


def evidence(request,result,series):
    rows,metrics,reasons=evaluate(request,result,series)
    import importlib.metadata
    return {"schema":"episentinel-retrospective-ia-i1","created_utc":datetime.now(timezone.utc).isoformat(),
        "request":request,"forecast":result,"evaluation":{"rows":rows,"metrics":metrics,"limitations":reasons},
        "environment":{"python":platform.python_version(),**{p:importlib.metadata.version(p) for p in ("numpy","pandas","statsmodels")}},
        "limitations":["Retrospective manual selection from historical catalogue; not a certified causal cohort",
        "Historical panel combines 210+220, folds S53 into S52 and fills missing combinations with zero",
        "Technical dates retained unchanged; not official epidemiological calendar",
        "2022 and other historical observations already inspected; not independent untouched test",
        "No B03/B05 session input; no outbreak confirmation or validated epidemiological prediction"]}
