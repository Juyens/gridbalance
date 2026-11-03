# Network presentation tools

Keep the existing Vue/Cytoscape workspace, both languages and both themes.
Add no dependencies and preserve the graph algorithms' choices and scoring.

## Implementation

- Replay starts at the MST (step 0), adds one recorded branch at a time and
  updates graph layers, selection details and metrics from the same snapshot.
  Record only bridges removed at each step, reusing backend Tarjan, so intermediate
  bridge highlighting remains correct without sending full graph snapshots.
- A collapsible controller provides previous/next, a step slider, play/pause,
  the current branch's real bus IDs and changes in cost, bridges and supply.
  Closing it restores the complete design. Changing case/weights stops replay.
- Search matches an integer bus ID, selects that bus and centres/zooms the view.
  A missing ID produces a localized message without changing the selection.
- PNG uses Cytoscape's full-network renderer with the active layers and theme.
  CSV contains original/MST/final metrics plus every addition, endpoint IDs,
  cost units and weights. Numbers remain machine-readable; UTF-8 BOM supports Excel.
- Both exports use native Save dialogs. Cancellation does nothing; invalid
  payloads are rejected before opening a dialog; atomic writes preserve existing
  files when saving fails. CSV text is escaped and formula prefixes neutralized.

## Verification

Test replay boundaries, immutable snapshots, changing bridge membership, real
IDs versus array positions, missing IDs, CSV quoting/numerics/formula text and
native export save/cancel/failure. Run existing tests, typecheck/build and linters;
inspect replay, search and export in the Windows app.
