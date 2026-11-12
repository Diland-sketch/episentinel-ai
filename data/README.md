# Procedencia de los datos

> Completar en la tarea A7. Sin campos "PENDIENTE" antes de citar cifras en
> el documento técnico.

- Fuente: SIVIGILA — Instituto Nacional de Salud (INS)
- ID del dataset / URL de descarga: PENDIENTE
- Fecha de descarga: PENDIENTE
- Eventos incluidos: 210 (dengue), 220 (dengue grave), 580 (mortalidad por dengue)
- Licencia / condiciones de uso: PENDIENTE
- Archivos originales: Dengue_210.csv, Dengue_220.csv, Dengue_580.csv (nombres verificados en los originales facilitados)


## Originales auditados en B01/B02 — 2026-11-11

Fuente declarada por el equipo: SIVIGILA/INS. La procedencia institucional aún
no está acreditada por URL, diccionario, fecha de extracción o licencia.
Fecha original de descarga: PENDIENTE; la fecha de auditoría no la sustituye.
El paquete de trabajo de Fase 2 es contexto histórico, no autorización ni
sustituto del diccionario oficial. Los archivos permanecen fuera de Git.

| Archivo | Bytes | Registros sin encabezado | SHA-256 |
|---|---:|---:|---|
| Dengue_210.csv | 13815423 | 200583 | 57fa15911fa360a624c3557d4593c2ad7b7de28cf44e7750325f21c771b78914 |
| Dengue_220.csv | 1605487 | 21557 | 541836debc708dbd2b4f429b812d44b6a337069e89d620de6afc7f479d4385eb |
| Dengue_580.csv | 125512 | 1511 | 80520bbc136acb69fbf2862dbf76499f4fd7ebe4ac3d75bdfb788c4cbfaf6854 |

Los tres contienen nueve columnas, periodo 2007–2022, conteos positivos y
22 registros de eventos ajenos en total. Ausencia de celda vacía no significa
cobertura completa. No contienen identificadores individuales ni etiquetas de brote.
Para reconstruir la comprobación, obtener estos mismos archivos por un canal
permitido y ejecutar `scripts/audit_csv_sources.py --source-dir <carpeta>`.
No existe todavía una descarga pública documentada que permita reconstruirlos
solo desde el repositorio. Ver `docs/CONTRATO_CSV.md` para alcance y limitaciones.


## Estado de B02: parcial y abierto

La identificación por huella y la conciliación están verificadas. Aún no existe
procedencia suficiente para que un tercero recupere los originales desde cero.
Estos pendientes pertenecen a B02; no se consideran resueltos por las decisiones B03.

| Campo de procedencia | Estado y evidencia requerida |
|---|---|
| URL o identificador institucional | **PENDIENTE**: enlace/ID oficial del conjunto y de la exportación de cada evento. |
| Fecha de descarga o extracción | **PENDIENTE**: fecha y, si existe, versión/corte de la fuente; no usar fecha de auditoría. |
| Condiciones de uso | **PENDIENTE**: enlace o texto institucional aplicable, atribución y condiciones de redistribución. |
| Procedimiento de recuperación | **PENDIENTE**: consulta/filtros, eventos, periodo, opciones de exportación y pasos exactos para obtener los mismos bytes o explicar cambios de versión. |

Procedimiento disponible hoy: quien ya posea los archivos puede colocarlos fuera
de Git y ejecutar `scripts/audit_csv_sources.py --source-dir <carpeta>` para
verificar las huellas. Esto verifica una copia existente; **no es un procedimiento
de recuperación institucional**. La solicitud de esa evidencia al custodio de los
originales sigue pendiente. No se ha inferido una URL ni licencia desde sus nombres.
