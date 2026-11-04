"""Dibuja redes pequeñas con Graphviz; con 2383 barras es ilegible y lento."""

from graphviz import Digraph, Graph


def Adjshow(G, directed=False):  # noqa: N802, N803
  """Devuelve el grafo Graphviz de una lista de adyacencia."""
  dot = Digraph() if directed else Graph()
  dot.attr("node", shape="circle")
  added = set()
  for u in range(len(G)):
    dot.node(str(u))
    for item in G[u]:
      if isinstance(item, tuple):
        v, w = item
      else:
        v, w = item, None
      label = "" if w is None else str(w)
      if directed:
        #En un grafo dirigido se dibujan todas las aristas.
        dot.edge(str(u), str(v), label=label)
      else:
        #En un grafo no dirigido se evita repetir la misma arista.
        key = tuple(sorted((u, v)))
        if key not in added:
          added.add(key)
          dot.edge(str(u), str(v), label=label)
  return dot


def show(G, tree=None, directed=False):  # noqa: N803
  """Devuelve el grafo Graphviz de una Grid o de una lista de adyacencia."""
  if not hasattr(G, "buses"):
    return Adjshow(G, directed)
  dot = Digraph() if directed else Graph()
  dot.attr("node", shape="circle")
  for bus in G.buses:
    dot.node(str(bus.id), str(bus.id))
  chosen = set(tree) if tree is not None else None
  #Cada rama se dibuja una vez, aunque haya ramas paralelas.
  for branch in G.branches:
    a = str(G.buses[branch.from_bus].id)
    b = str(G.buses[branch.to_bus].id)
    if chosen is not None and branch.index in chosen:
      dot.edge(a, b, color="red", penwidth="2")
    else:
      dot.edge(a, b)
  return dot
