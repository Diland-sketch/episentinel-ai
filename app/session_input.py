"""Session-only canonical input adapter. No new scientific schema or model calls."""
import csv
import io
from uuid import uuid4
from episentinel.data.csv_contract import FIELDS
from episentinel.data.csv_loader import load_csv
from app.analysis_presenter import set_source

CSV_MODE="Cargar CSV"
MANUAL_MODE="Registro manual"
MAX_MANUAL=1000


def new_inputs():
    return {"session_id":uuid4().hex,"version":0,"mode":CSV_MODE,"csv_payload":None,"csv_name":None,
            "csv_load":None,"manual_rows":[],"include_csv":False,"rejected_attempts":0,"feedback":None}


def observe_work(inputs,work):
    """Adopt already loaded B08 sessions without resetting their results."""
    if inputs["mode"]==CSV_MODE and work["payload"] is not None:
        identity=(inputs["csv_payload"],inputs["csv_name"])
        if identity!=(work["payload"],work["filename"]):
            inputs.update(csv_payload=work["payload"],csv_name=work["filename"],csv_load=work["load"],version=inputs["version"]+1)


def encode_rows(rows):
    stream=io.StringIO(newline="")
    writer=csv.DictWriter(stream,fieldnames=FIELDS,lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if set(row)!=set(FIELDS):raise ValueError("El registro debe contener exactamente los cinco campos canónicos")
        writer.writerow(row)
    return stream.getvalue().encode("utf-8")


def base_rows(inputs):
    loaded=inputs["csv_load"]
    if not inputs["include_csv"]:return []
    if loaded is None or loaded.blocked:raise ValueError("Solo puede combinarse un CSV aceptado por B04")
    return [{field:row[field] for field in FIELDS} for row in loaded.data]


def current_payload(inputs,rows=None):
    if inputs["mode"]==CSV_MODE:return inputs["csv_payload"],inputs["csv_name"]
    records=base_rows(inputs)+(inputs["manual_rows"] if rows is None else rows)
    if not records:return None,None
    kind="combinado" if inputs["include_csv"] else "manual"
    return encode_rows(records),f"sesion_{inputs['session_id'][:8]}_{kind}_v{inputs['version']}.csv"


def apply(inputs,work):
    inputs["version"]+=1
    payload,name=current_payload(inputs)
    set_source(work,payload,name)


def change_csv(inputs,work,payload,name):
    if (payload,name)==(inputs["csv_payload"],inputs["csv_name"]):return False
    inputs.update(csv_payload=payload,csv_name=name,csv_load=None,include_csv=False,feedback=None)
    if payload is not None:inputs["csv_load"]=load_csv(payload,source_name=name)
    if inputs["mode"]==CSV_MODE:apply(inputs,work)
    return True


def change_mode(inputs,work,mode):
    if mode not in (CSV_MODE,MANUAL_MODE):raise ValueError("Método de entrada no admitido")
    if mode==inputs["mode"]:return False
    inputs.update(mode=mode,feedback=None)
    apply(inputs,work)
    return True


def combine(inputs,work,enabled):
    old=inputs["include_csv"]
    if old==enabled:return True
    inputs["include_csv"]=enabled
    try:
        rows=base_rows(inputs)+inputs["manual_rows"]
        if rows:
            loaded=load_csv(encode_rows(rows),source_name="validacion_combinada.csv")
            if loaded.blocked:
                inputs["include_csv"]=old
                inputs["feedback"]={"accepted":False,"message":"No se combinó: B04 detectó un conflicto o duplicado. Ningún registro se sustituyó ni sumó.","report":loaded.report}
                return False
    except ValueError as exc:
        inputs["include_csv"]=old
        inputs["feedback"]={"accepted":False,"message":str(exc),"report":None}
        return False
    inputs["feedback"]=None
    apply(inputs,work)
    return True


def add_manual(inputs,work,row):
    if inputs["mode"]!=MANUAL_MODE:raise ValueError("Activa Registro manual antes de agregar")
    if len(inputs["manual_rows"])>=MAX_MANUAL:
        inputs["feedback"]={"accepted":False,"message":"Límite de interfaz: 1000 registros manuales en memoria.","report":None}
        return False
    prospective=inputs["manual_rows"]+[dict(row)]
    loaded=load_csv(encode_rows(base_rows(inputs)+prospective),source_name="validacion_manual.csv")
    if loaded.blocked:
        inputs["rejected_attempts"]+=1
        duplicate=any(e["code"]=="duplicate" for e in loaded.report["errors"])
        inputs["feedback"]={"accepted":False,"message":
            "Registro rechazado por clave duplicada o conflictiva. No se suma ni reemplaza el conteo." if duplicate else
            "Registro rechazado por B04. Revisa los cinco campos; el conjunto activo no cambió.","report":loaded.report}
        return False
    inputs["manual_rows"]=prospective
    apply(inputs,work)
    inputs["feedback"]={"accepted":True,"message":"Registro agregado y conjunto completo validado por B04. No se entrenó ningún modelo.","report":None}
    return True


def clear_active(inputs,work):
    if inputs["mode"]==CSV_MODE:
        inputs.update(csv_payload=None,csv_name=None,csv_load=None,include_csv=False)
    else:
        inputs.update(manual_rows=[],include_csv=False,rejected_attempts=0)
    inputs["feedback"]=None
    apply(inputs,work)


def counters(inputs,work):
    loaded=work["load"]
    summary=loaded.report["summary"] if loaded else {}
    total=summary.get("rows_read",0)
    rejected=min(total,summary.get("records_with_errors",0)) if loaded and loaded.blocked else 0
    valid=summary.get("rows_delivered",0)
    csv_active=inputs["mode"]==CSV_MODE or inputs["include_csv"]
    csv_total=(inputs["csv_load"].report["summary"]["rows_read"] if inputs["csv_load"] else 0) if csv_active else 0
    manual=len(inputs["manual_rows"]) if inputs["mode"]==MANUAL_MODE else 0
    return {"csv":csv_total,"manual":manual,"valid":valid,"rejected":rejected,
            "pending":max(0,total-valid-rejected),"total":total,"rejected_attempts":inputs["rejected_attempts"]}


def provenance(inputs,limit=100):
    from itertools import islice,chain
    csv_origins=()
    if inputs["mode"]==CSV_MODE or inputs["include_csv"]:
        loaded=inputs["csv_load"]
        if loaded and not loaded.blocked:
            csv_origins=({"Origen":"CSV","Fuente original":inputs["csv_name"],"Registro original":r["record"]} for r in loaded.data)
    manual_origins=()
    if inputs["mode"]==MANUAL_MODE:
        manual_origins=({"Origen":"Manual declarado","Fuente original":inputs["session_id"],"Registro original":i} for i in range(1,len(inputs["manual_rows"])+1))
    return [{"Registro CSV activo":i+2,**row} for i,row in enumerate(islice(chain(csv_origins,manual_origins),limit))]


def partition_context(inputs,work):
    loaded=work["load"]
    result=work["result"]
    identity={"Sesión":inputs["session_id"],"Versión local":inputs["version"],
              "SHA-256 conjunto":loaded.sha256 if loaded else None,"Contrato CSV":loaded.contract_version if loaded else None,
              "CSV original SHA-256":inputs["csv_load"].sha256 if inputs["csv_load"] and (inputs["mode"]==CSV_MODE or inputs["include_csv"]) else None}
    reasons=[];rows=[];series_rows=[]
    if not loaded or loaded.blocked:reasons.append("Se requiere un conjunto aceptado completamente por B04.")
    if result is None or result.status!="completed" or result.series is None:
        reasons.append("Aún no existe una serie construida para la selección vigente. Filas y posiciones temporales no son equivalentes.")
    else:
        bundle=result.series
        for series in bundle.series:
            series_rows.append({"Evento":series.event_code,"Posiciones declaradas":len(series.points),
                "Observadas":series.coverage.observed_periods,"Ausentes":len(series.coverage.missing_periods),
                "Elegibilidad":series.eligibility.status})
            rows.extend({"Evento":series.event_code,"Año":p.period[0],"Semana":p.period[1],"Conteo":p.observed_count,
                "Estado":p.observation_status,"Partición":"Sin asignación a entrenamiento/validación/prueba"} for p in series.points)
        reasons.append("B03 mantiene elegibilidad no evaluada, fechas sin asignar y catálogo territorial pendiente.")
        if bundle.grid.metadata.verification!="verified":reasons.append("La malla temporal no tiene calendario verificado.")
        if any(s.coverage.missing_periods for s in bundle.series):reasons.append("Existen posiciones sin observación; no se imputan ceros.")
        if len(bundle.grid.periods)<17:reasons.append("B10 exige validación y prueba con ocho objetivos cada una y entrenamiento no vacío: esta malla no alcanza 17 posiciones.")
    return {"identity":identity,"eligible_positions":None,"partitions":None,"reasons":reasons,"series":series_rows,"rows":rows}
