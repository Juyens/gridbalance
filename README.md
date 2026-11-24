# PwrGrid

Aplicación de escritorio para diseñar redes eléctricas con algoritmos sobre grafos. Parte del árbol de expansión mínima (Kruskal) y lo refuerza con un algoritmo voraz según tres pesos configurables en vivo: costo, robustez (puentes, Tarjan) y abastecimiento (flujo máximo, Edmonds-Karp). Se busca cualquier lugar del Perú en un mapa y la app diseña la red eléctrica de esa zona.

Trabajo del curso 1ACC0184 Complejidad Algorítmica (UPC, 2026-20).

## Stack

| Parte | Herramientas |
|---|---|
| Backend | Python 3.13, algoritmos implementados sin librerías de grafos |
| Ventana | pywebview (usa WebView2, incluido en Windows 11) |
| Frontend | Vue 3, TypeScript, Vite, MapLibre GL JS |
| Calidad | uv, ruff, pytest, ESLint, Prettier |

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala Python 3.13 solo si hace falta)
- [Node.js](https://nodejs.org/) 24 o superior

## Instalación

Desde la carpeta del repositorio:

```powershell
uv sync
npm install --prefix frontend
npm run build --prefix frontend
```

Después de cada `git pull` repite estos tres comandos: la app abre el build de `frontend/dist`, que no se sube al repositorio, así que sin recompilar se sigue viendo la interfaz anterior.

`visualizacion.py` es opcional y solo sirve para redes pequeñas. Para dibujar hace
falta instalar Graphviz en el sistema y tener `dot` en el `PATH`; el paquete de
Python `graphviz` por sí solo no basta. En Google Colab ya viene instalado.

## Ejecutar

```powershell
uv run gridbalance
```

Escribe una dirección o lugar en el buscador. Usa el control debajo del buscador para fijar el radio. En la barra superior, abre **Diseño** para ajustar las prioridades o **Resultados** para consultar las métricas y el elemento seleccionado.

### Modo desarrollo

Con recarga automática del frontend. En una terminal:

```powershell
npm run dev --prefix frontend
```

Y en otra:

```powershell
uv run gridbalance --dev
```

## Pruebas y calidad

```powershell
uv run pytest
uv run ruff check
npm run lint --prefix frontend
```

## Estructura

```
data/peru/              nodos y líneas del Perú (CSV)
tools/build_dataset.py  genera data/ desde un extracto de OpenStreetMap
src/gridbalance/
  osm.py                carga los datos y busca una zona
  zone.py               convierte la zona en el grafo (demanda, líneas, costos)
  grid.py               modelo de la red (barras, líneas, generadores)
  ufds.py               Union-Find
  mst.py                Kruskal
  bridges.py            puentes con Tarjan
  flow.py               flujo máximo con Edmonds-Karp (incremental)
  reinforcement.py      refuerzo voraz con pesos
  visualizacion.py      dibuja redes pequeñas con Graphviz (opcional)
  api.py                métodos que llama el frontend
  app.py                abre la ventana
frontend/src/           interfaz en Vue
tests/                  pruebas con pytest
```

## Datos

`data/peru` contiene las subestaciones, centrales, localidades y líneas eléctricas del Perú, extraídas de [OpenStreetMap](https://www.openstreetmap.org/copyright) (licencia ODbL) con el extracto `peru-261122.osm.pbf` de [Geofabrik](https://download.geofabrik.de/south-america/peru.html). Para volver a generarlo, descarga el extracto y ejecuta:

```powershell
uv run tools/build_dataset.py peru-261122.osm.pbf data/peru
```

OpenStreetMap no incluye demanda, capacidades ni costos: se estiman en `zone.py` (clase `Assumptions`), con las fuentes en [docs/sources.md](docs/sources.md).

El mapa es de [OpenFreeMap](https://openfreemap.org/) y el buscador de lugares de [Photon](https://photon.komoot.io/). Ambos necesitan conexión a internet.
