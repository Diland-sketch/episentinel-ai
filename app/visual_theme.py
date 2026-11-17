"""Presentation only: shared figure surfaces and complete heatmap tick labels."""
from html import escape
import textwrap


def style_figure(figure):
    """Keep trace data, scales, annotations and analytical transformations intact."""
    figure.update_layout(
        paper_bgcolor="#FFFEFA", plot_bgcolor="#FFFEFA",
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color="#24353D"),
        title=dict(font=dict(size=17, color="#102F3A"), x=0, xanchor="left"),
        margin=dict(l=55, r=24, t=80, b=65),
        legend=dict(orientation="h", y=-0.25, x=0, font=dict(size=11)),
    )
    figure.update_xaxes(automargin=True, gridcolor="#E6EBE5", zerolinecolor="#C7D6CD")
    figure.update_yaxes(automargin=True, gridcolor="#E6EBE5", zerolinecolor="#C7D6CD")
    # Long analytical titles remain intact but wrap on narrow figures.
    if figure.layout.title.text:
        figure.update_layout(title_text="<br>".join(textwrap.wrap(figure.layout.title.text, 38)))
    return figure


def heatmap_labels(figure):
    """Reserve a real label gutter, wrap full names and display every territory."""
    labels = list(figure.data[0].y)
    ticktext = ["<br>".join(escape(part) for part in textwrap.wrap(str(label), 18, break_long_words=False)) for label in labels]
    figure.update_layout(height=max(360, sum(24 + 12 * text.count("<br>") for text in ticktext) + 150),
                         margin=dict(l=138, r=16, t=95, b=65))
    figure.update_yaxes(tickmode="array", tickvals=labels, ticktext=ticktext,
                        tickfont=dict(size=11), automargin=True, title=None)
    figure.update_xaxes(tickmode="array", tickvals=list(figure.data[0].x)[::2], tickangle=-45, tickfont=dict(size=11))
    figure.update_traces(colorbar=dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom",
                                      len=1, thickness=8, title=dict(text="log(1+casos)", side="top"), tickfont=dict(size=10)))
    return figure
