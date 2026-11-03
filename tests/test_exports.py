import base64
from pathlib import Path
from types import SimpleNamespace

import pytest
import webview

from gridbalance.api import Api, design_to_json
from gridbalance.bridges import find_bridges
from gridbalance.reinforcement import Reinforcer, Weights


def test_replay_bridge_changes_match_every_intermediate_network(make_grid):
    grid = make_grid(4, [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 2, 3), (1, 3, 4)])
    design = Reinforcer(grid).design(Weights(0, 1, 0))
    payload = design_to_json(grid, design, 1)
    active = list(design.tree)
    remaining = set(active)
    for step in payload["steps"]:
        active.append(step["branch"])
        remaining.difference_update(step["removedBridges"])
        assert remaining == set(find_bridges(grid, active))
        assert len(remaining) == step["bridges"]
    assert remaining == set(payload["bridgeBranches"])


def set_dialog(monkeypatch, result):
    monkeypatch.setattr(
        webview,
        "windows",
        [SimpleNamespace(create_file_dialog=lambda *_args, **_kwargs: result)],
    )


def test_csv_export_supports_excel_and_cancel_preserves_files(tmp_path, monkeypatch):
    target = tmp_path / "report.csv"
    set_dialog(monkeypatch, (str(target),))
    api = Api(tmp_path)
    assert api.save_export("csv", "name,cost\r\nEspaña,12.5\r\n") is True
    assert target.read_bytes().startswith(b"\xef\xbb\xbf")
    before = target.read_bytes()
    set_dialog(monkeypatch, None)
    assert api.save_export("csv", "replacement") is False
    assert target.read_bytes() == before


def test_png_export_decodes_binary(tmp_path, monkeypatch):
    target = tmp_path / "network.png"
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8"
        "AAwMCAO+jRZkAAAAASUVORK5CYII="
    )
    set_dialog(monkeypatch, (str(target),))
    assert Api(tmp_path).save_export("png", base64.b64encode(png).decode()) is True
    assert target.read_bytes() == png


@pytest.mark.parametrize(
    "kind,content", [("exe", "x"), ("png", "!!!"), ("png", "aGVsbG8="), ("csv", None)]
)
def test_invalid_export_is_rejected_before_dialog(tmp_path, monkeypatch, kind, content):
    monkeypatch.setattr(webview, "windows", [])
    with pytest.raises(ValueError):
        Api(tmp_path).save_export(kind, content)


def test_failed_export_keeps_previous_file(tmp_path, monkeypatch):
    target = tmp_path / "report.csv"
    target.write_text("original", encoding="utf-8")
    set_dialog(monkeypatch, (str(target),))

    def fail_replace(_self, _target):
        raise PermissionError("file locked")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(PermissionError, match="file locked"):
        Api(tmp_path).save_export("csv", "new content")
    assert target.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.iterdir()) == [target]
