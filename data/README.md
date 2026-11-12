# Procedencia y reproducción de los datos — B02

## Identificación y fechas

- Portal: Portal Nacional de Datos Abiertos de Colombia.
- Conjunto: **Datos de Vigilancia en Salud Pública de Colombia**.
- Identificador institucional: **`4hyg-wa9d`**.
- [Ficha oficial](https://www.datos.gov.co/Salud-y-Protecci-n-Social/Datos-de-Vigilancia-en-Salud-P-blica-de-Colombia/4hyg-wa9d/about_data).
- [Metadatos oficiales consultados](https://www.datos.gov.co/api/views/4hyg-wa9d.json).
- Entidad atribuida en los metadatos: Instituto Nacional de Salud - INS, Bogotá D.C.
- Descarga histórica: **23/09/2026**, según evidencia del historial comunicada por
  Diland, responsable del proyecto. No se inspeccionó ni incorporó el historial
  personal al repositorio; la fecha tiene ese respaldo declarado por el responsable.
- Consulta de metadatos y actualización documental: **11/11/2026**.
- Fecha de publicación, actualización del portal y fecha de extracción/corte interno:
  no se equiparan a la descarga del usuario. El corte exacto de extracción histórico
  no está acreditado; el periodo observado en los archivos es 2007–2022.

## Condiciones de reutilización verificadas

Los metadatos actuales del conjunto declaran `licenseId: CC_40_BY_SA` y
`Creative Commons Attribution | Share Alike 4.0 International`.
Ver [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) y su
[código legal](https://creativecommons.org/licenses/by-sa/4.0/legalcode.es).
La reutilización requiere atribución, enlace de licencia e identificación de cambios;
el material adaptado que se comparta queda sujeto a CompartirIgual y no se deben
imponer restricciones adicionales incompatibles. Conservar los avisos aplicables.
Esto documenta la licencia de los datos, no asigna una licencia al software del proyecto.

La ficha HTML no expuso su contenido al lector de páginas; se verificaron sus
metadatos JSON oficiales mediante consulta de solo lectura. Se confirma la licencia
publicada actualmente, no una captura de sus términos exactos el 23/09/2026.

## Manifiesto de originales históricos

Los tres archivos facilitados por Diland son las copias de referencia utilizadas
por el proyecto. No se incluyen en Git. Auditoría técnica ya ejecutada el 11/11/2026:
223.651 registros en total, nueve columnas, periodo 2007–2022 y 22 filas de eventos
ajenos. La ausencia de celdas vacías no acredita cobertura temporal completa.

| Archivo | Bytes | Registros sin encabezado | SHA-256 |
|---|---:|---:|---|
| Dengue_210.csv | 13815423 | 200583 | 57fa15911fa360a624c3557d4593c2ad7b7de28cf44e7750325f21c771b78914 |
| Dengue_220.csv | 1605487 | 21557 | 541836debc708dbd2b4f429b812d44b6a337069e89d620de6afc7f479d4385eb |
| Dengue_580.csv | 125512 | 1511 | 80520bbc136acb69fbf2862dbf76499f4fd7ebe4ac3d75bdfb788c4cbfaf6854 |


## Recuperación, comprobación y reconstrucción

Ver [procedimiento B02](../docs/PROCEDENCIA_B02.md) para:

1. Recuperar una copia histórica conservada y contrastar las tres huellas.
2. Hacer una nueva exportación del portal sin atribuirle identidad histórica.
3. Ejecutar la auditoría de solo lectura y reconstruir salidas heredadas en una
   carpeta nueva, sin sobrescribir las salidas del proyecto de trabajo.

La igualdad de huellas acredita identidad de bytes. Una exportación nueva puede
cambiar contenido, orden, formato o encabezados y no debe sustituir los originales.

## Estado documental y evidencias restantes

Fuente, identificador, fecha de descarga declarada, condiciones actuales de uso,
huellas y pasos de reconstrucción desde originales conservados están documentados.
Se reutiliza la evidencia técnica de la segunda iteración: 82 pruebas aprobadas y
25 controles verdaderos; no se repitió esa auditoría en esta actualización documental.

Pendientes de trazabilidad histórica:

- Referencia compartible y no sensible que respalde el historial de descarga,
  si el equipo necesita verificarlo sin depender de la declaración del responsable.
- Consulta/filtros y opciones exactas de las exportaciones del 23/09/2026, o un
  archivo institucional versionado que permita recuperarlas byte a byte.
- Ubicación de resguardo histórico accesible al equipo: las copias locales están
  recuperadas, pero no se ha acreditado un archivo compartido de preservación.

No se inventan URL de descarga histórica ni filtros que expliquen las 22 filas
ajenas. B02 tiene documentación suficiente para reproducir el procesamiento desde
las copias identificadas; no se acredita recuperación institucional exacta desde
cero. El cierre debe explicitar ese límite o completar la evidencia histórica.
No se ha cerrado el Issue #2.
