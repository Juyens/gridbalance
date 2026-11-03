# GridBalance interface

## Direction

An engineering workspace: controls on the left, the network in the centre,
results on the right. Keep Vue, Cytoscape, pywebview, the existing English
interface and system fonts. No added dependencies or decorative motion.

## Hallmark review and changes

- The original left sidebar scrolled horizontally. Shrinkable grid tracks,
  minimum widths and compact presets now keep the controls within the panel.
- Four metric cards repeated the always-visible comparison table. Results
  are now plain rows; the full comparison is available in native details.
- Bridge highlighting and unused lines made the initial graph crowded.
  Both remain available as layers, initially off; their legend entries follow
  the layer state. Bridges also use dashed lines to distinguish them by shape.
- Repeated slider instructions now live in accessible value descriptions
  and title hints. Percentages remain visible and presets expose their state.
- The graph has a Fit view button and observes container resizing. The legend
  occupies its own area instead of covering the drawing.
- Narrow windows move results below the network; small windows stack sections.

## Colours and identity

`tokens.css` holds the shared palette. Graph tokens use sRGB because Cytoscape
does not parse OKLCH. System typography is intentional for an offline desktop
tool. Green denotes added connections; red is reserved for bridges and errors.

The icon is an original vector network with a reinforced diagonal and central
junction, using the same quiet green identity. `frontend/public/favicon.svg`
is the editable source; `gridbalance.png` is 256px; `gridbalance.ico` contains
16, 24, 32, 48, 64, 128 and 256px images. pywebview uses the ICO on Windows.

## Verification

Build/typecheck, ESLint, Ruff and all 55 Python tests passed. Desktop inspection
confirmed the icon, Economic preset recalculation, layer toggles and comparison.
The complete Prettier check reports seven unchanged source files; edited files
were formatted. Exact mobile widths and other operating systems were not tested.
