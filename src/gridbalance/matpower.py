"""Reader for MATPOWER case files (.m), case format version 2.

A case file is a MATLAB function that fills a struct named 'mpc'. We do not run
MATLAB: we read the text and pull out the assignments we need.
    mpc.baseMVA = 100; -> scalar
    mpc.bus = [ ... ]; -> matrix, one row per bus, columns separated by spaces
"""

import re
from dataclasses import dataclass
from pathlib import Path

REQUIRED_MATRICES = ("bus", "gen", "branch")

# mpc.<name> = [ <body> ];  The body spans many lines, hence DOTALL.
MATRIX_PATTERN = re.compile(r"mpc\.(\w+)\s*=\s*\[(.*?)\]\s*;", re.DOTALL)
# mpc.<name> = <number>;
SCALAR_PATTERN = re.compile(r"mpc\.(\w+)\s*=\s*([-+]?[\d.]+(?:[eE][-+]?\d+)?)\s*;")
# mpc.version = '2';
VERSION_PATTERN = re.compile(r"mpc\.version\s*=\s*'(\d+)'\s*;")


class CaseFormatError(ValueError):
    """The text is not a valid MATPOWER version 2 case."""


@dataclass(frozen=True)
class RawCase:
    """Case contents as read from the file, before giving meaning to each column."""

    name: str
    base_mva: float
    matrices: dict[str, list[list[float]]]


def strip_comments(text: str) -> str:
    """Drops everything after '%' on each line (MATLAB comments)."""
    return "\n".join(line.split("%", 1)[0] for line in text.splitlines())


def parse_matrix(name: str, body: str) -> list[list[float]]:
    """
    Turns a matrix body into rows of floats.
    Rows end with ';' or a line break; values are separated by spaces, tabs or
    commas. float() also accepts MATLAB's 'Inf' and 'NaN'.
    """
    rows = []
    for row_text in re.split(r"[;\n]", body):
        values = row_text.replace(",", " ").split()
        if values:
            try:
                rows.append([float(value) for value in values])
            except ValueError as error:
                raise CaseFormatError(f"mpc.{name}: {error}") from error

    widths = {len(row) for row in rows}
    if len(widths) > 1:
        raise CaseFormatError(f"mpc.{name}: rows have different lengths {widths}")
    return rows


def parse_case(name: str, text: str) -> RawCase:
    text = strip_comments(text)

    version = VERSION_PATTERN.search(text)
    if version is None or version.group(1) != "2":
        raise CaseFormatError(
            f"{name}: only MATPOWER case format version 2 is supported"
        )

    scalars = {key: float(value) for key, value in SCALAR_PATTERN.findall(text)}
    if "baseMVA" not in scalars:
        raise CaseFormatError(f"{name}: missing mpc.baseMVA")

    matrices = {
        key: parse_matrix(key, body) for key, body in MATRIX_PATTERN.findall(text)
    }
    for required in REQUIRED_MATRICES:
        if not matrices.get(required):
            raise CaseFormatError(f"{name}: missing or empty mpc.{required}")

    return RawCase(name=name, base_mva=scalars["baseMVA"], matrices=matrices)


def read_case(path: Path) -> RawCase:
    """Reads a .m case file; the case name is the file name without extension."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_case(path.stem, text)
