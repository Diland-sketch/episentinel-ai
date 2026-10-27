# Decisiones técnicas

> Toda propuesta nueva de Claude o de un integrante se anota aquí como
> **propuesta** y pasa a **aprobada** solo cuando el equipo (o Diland) lo
> confirma explícitamente.

## Heredadas de la Fase 1 (aprobadas, según la propuesta ya sustentada)

- Evento: dengue, códigos 210 (casos) + 220 (dengue grave); 580 (mortalidad)
  se trata como panel separado. Malaria queda opcional.
- Unidad de análisis: municipio (`cod_mun`) x semana epidemiológica.
- Métricas: PR-AUC, F1 y tiempo de detección; nunca accuracy (desbalance
  extremo confirmado en el EDA real).
- Validación: rolling origin / partición cronológica, sin mezcla aleatoria.
- Semana 53 plegada a la 52; duplicados por clave sumados.

## Propuestas pendientes de aprobación

| ID | Propuesta | Estado |
|---|---|---|
| P-01 | Definición operativa de "difícil acceso" (índice multicriterio) | Propuesta |
| P-02 | Definición operativa de "brote" y conjuntos de etiquetas | Propuesta |
| P-03 | Alcance por niveles para la Fase 2 (núcleo vs. pospuesto a Fase 3) | Propuesta |
| P-04 | Prototipo Streamlit/FastAPI; Power BI opcional | Propuesta |
| P-05 | Tratamiento definitivo de la semana 53 | Propuesta |
| P-06 | Buscar datos 2023 en adelante | Propuesta |
| P-07 | Qué municipios se modelan individualmente vs. agregados | Propuesta |
| P-08 | Mortalidad (580) como panel separado | Propuesta |
| P-09 | Estructura del repositorio y convención de commits | Implementada en este esqueleto; pendiente de que el equipo la ratifique |
