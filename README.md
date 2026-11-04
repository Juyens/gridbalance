# GridBalance

Aplicación de escritorio para diseñar redes eléctricas con algoritmos sobre grafos. Parte del árbol de expansión mínima (Kruskal) y lo refuerza con un algoritmo voraz según tres pesos configurables en vivo: costo, robustez (puentes, Tarjan) y abastecimiento (flujo máximo, Edmonds-Karp). Lee cualquier caso en formato MATPOWER (`.m`).

Trabajo del curso 1ACC0184 Complejidad Algorítmica (UPC, 2026-20).

## Stack

| Parte | Herramientas |
|---|---|
| Backend | Python 3.13, algoritmos implementados sin librerías de grafos |
| Ventana | pywebview (usa WebView2, incluido en Windows 11) |
| Frontend | Vue 3, TypeScript, Vite, Cytoscape.js con fcose |
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

`visualizacion.py` es opcional y solo sirve para redes pequeñas. Para dibujar hace
falta instalar Graphviz en el sistema y tener `dot` en el `PATH`; el paquete de
Python `graphviz` por sí solo no basta. En Google Colab ya viene instalado.

## Ejecutar

```powershell
uv run gridbalance
```

La primera vez que se abre una red se calcula la posición de los nodos y se guarda en `cases/<caso>.layout.json`; las siguientes veces abre al instante.

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
cases/                  redes MATPOWER (.m) y layouts guardados
src/gridbalance/
  matpower.py           lector de archivos .m
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

`cases/case2383wp.m` es la red de transmisión de Polonia (2383 barras, 2896 ramas), tomada del [repositorio de MATPOWER](https://github.com/MATPOWER/matpower/blob/master/data/case2383wp.m). Se usa con fines académicos.
