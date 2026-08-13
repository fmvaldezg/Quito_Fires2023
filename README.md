# Mapa de incendios Ecuador

Fuente de los datos https://firms.modaps.eosdis.nasa.gov/ (VIIRS NRT, vía la [FIRMS Area API](https://firms.modaps.eosdis.nasa.gov/api/area/)).

Los datos se actualizan automáticamente todos los días mediante un workflow de GitHub Actions ([.github/workflows/update-fire-data.yml](.github/workflows/update-fire-data.yml)) que corre [data/update_fires.py](data/update_fires.py): descarga las detecciones recientes, las combina con `data/output_file.json`, y mantiene una ventana móvil de 90 días. El mapa (`index.html`) obtiene su rango de fechas directamente de ese archivo, así que no requiere ningún paso manual.

Para una descarga histórica puntual fuera de esta ventana de 90 días, `data/transform.py` sigue disponible para convertir un archivo descargado manualmente desde el sitio de FIRMS.

