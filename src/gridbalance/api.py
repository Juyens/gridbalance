"""Methods exposed to the frontend as window.pywebview.api."""

from importlib.metadata import version


class Api:
    def ping(self) -> str:
        return f"Backend ready (gridbalance {version('gridbalance')})"
