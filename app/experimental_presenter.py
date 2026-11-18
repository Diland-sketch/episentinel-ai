"""Read-only adapters for B10 positional planning; never fit or select models."""
from numbers import Integral
import plotly.graph_objects as go
from episentinel.evaluation.temporal_protocol import TemporalProtocol
from episentinel.evaluation.rolling_origin import plan_rolling_origin


def percentage_protocol(total, train_percent, validation_percent):
    for name, value in (("Total", total), ("Entrenamiento", train_percent), ("Validación", validation_percent)):
        if isinstance(value, bool) or not isinstance(value, Integral):
            raise ValueError(name + ": se requiere un entero")
    if total < 3 or not 0 < train_percent < 100 or not 0 < validation_percent < 100 or train_percent + validation_percent >= 100:
        raise ValueError("Reserva porcentajes positivos para entrenamiento, validación y prueba; deben sumar 100 %.")
    # Floor first two counts; allocate the exact remainder to test. No positions lost.
    train = int(total * train_percent // 100)
    validation = int(total * validation_percent // 100)
    return TemporalProtocol(train, train + validation, int(total))


def partition_rows(protocol):
    boundaries = (0, protocol.train_size, protocol.validation_end, protocol.total_size)
    return [{"Partición": label, "Inicio inclusivo": start, "Fin exclusivo": end,
             "Posiciones": end-start, "Porcentaje efectivo": round(100*(end-start)/protocol.total_size, 3)}
            for label, start, end in zip(("Entrenamiento", "Validación", "Prueba"), boundaries, boundaries[1:])]


def partition_figure(protocol):
    fig = go.Figure()
    for row, color in zip(partition_rows(protocol), ("#276D70", "#D59A70", "#8DCABA")):
        fig.add_trace(go.Bar(x=[row["Posiciones"]], base=[row["Inicio inclusivo"]], y=["Malla posicional"],
            orientation="h", name=row["Partición"], marker_color=color, text=[str(row["Posiciones"])], textposition="inside",
            hovertemplate=f'{row["Partición"]}: [{row["Inicio inclusivo"]}, {row["Fin exclusivo"]})<extra></extra>'))
    fig.update_layout(barmode="overlay", height=220, margin=dict(l=8,r=8,t=35,b=55),
        xaxis_title="Posiciones · no fechas epidemiológicas", yaxis=dict(visible=False),
        legend=dict(orientation="h", y=1.3), paper_bgcolor="#FFFEFA", plot_bgcolor="#FFFEFA")
    return fig


def origin_rows(plan):
    return [{"Partición": o.partition, "Corte inclusivo": o.cut, "Entrenamiento": f"[0, {o.cut+1})",
             "Objetivos": f"[{o.target_start}, {o.target_end})", "Pasos": len(o.target_positions),
             "Métodos": ", ".join(o.methods)} for o in plan.origins]


def rolling_figure(plan, partition):
    fig = go.Figure()
    origins = [o for o in plan.origins if o.partition == partition][:40]
    for i, o in enumerate(origins):
        fig.add_trace(go.Scatter(x=[o.target_start,o.target_end-1], y=[f"Corte {o.cut}"]*2,
            mode="lines+markers", line=dict(color="#276D70",width=5), name="Objetivos completos", showlegend=i==0,
            hovertemplate=f'Corte {o.cut} · entrenamiento [0,{o.cut+1})<br>Objetivos [{o.target_start},{o.target_end})<extra></extra>'))
    excluded = [o for o in plan.excluded if o.partition==partition]
    if excluded:
        fig.add_trace(go.Scatter(x=[o.cut+1 for o in excluded], y=[f"Descartado {o.cut}" for o in excluded],
            mode="markers", marker=dict(symbol="x",size=11,color="#A95C2B"), name="Horizonte incompleto",
            hovertemplate="No caben ocho objetivos dentro de la partición<extra></extra>"))
    fig.update_layout(height=max(260,26*(len(origins)+len(excluded))+110),
        margin=dict(l=130,r=20,t=35,b=65), yaxis=dict(autorange="reversed",automargin=True),
        xaxis_title="Posiciones objetivo<br>Planificación · sin pronósticos",
        legend=dict(orientation="h",y=1.15),paper_bgcolor="#FFFEFA",plot_bgcolor="#FFFEFA")
    return fig
