from pathlib import Path

import pytest

from gridbalance.matpower import CaseFormatError, parse_case, read_case

CASES_DIR = Path(__file__).resolve().parents[1] / "cases"

TINY_CASE = """
function mpc = tiny
%% MATPOWER Case Format : Version 2
mpc.version = '2';
mpc.baseMVA = 100;

%% bus data
%	bus_i	type	Pd
mpc.bus = [
	1	3	0;   % slack bus
	2	1	50.5;
	3	1	-2e1;
];

mpc.gen = [1, 100, Inf];

mpc.branch = [
	1	2	0.01;	2	3	0.02;
];
"""


def test_parse_case_reads_scalars_and_matrices():
    case = parse_case("tiny", TINY_CASE)

    assert case.name == "tiny"
    assert case.base_mva == 100
    assert case.matrices["bus"] == [[1, 3, 0], [2, 1, 50.5], [3, 1, -20]]
    # Commas as separators and MATLAB's Inf.
    assert case.matrices["gen"] == [[1, 100, float("inf")]]
    # Two rows on the same line, separated by ';'.
    assert case.matrices["branch"] == [[1, 2, 0.01], [2, 3, 0.02]]


def test_parse_case_rejects_other_versions():
    with pytest.raises(CaseFormatError, match="version 2"):
        parse_case("old", TINY_CASE.replace("'2'", "'1'"))


def test_parse_case_requires_branch_matrix():
    text = TINY_CASE.replace("mpc.branch", "mpc.other")
    with pytest.raises(CaseFormatError, match=r"mpc\.branch"):
        parse_case("tiny", text)


def test_parse_case_rejects_ragged_rows():
    text = TINY_CASE.replace("2	1	50.5;", "2	1;")
    with pytest.raises(CaseFormatError, match="different lengths"):
        parse_case("tiny", text)


def test_read_case_polish_grid():
    case = read_case(CASES_DIR / "case2383wp.m")

    assert case.name == "case2383wp"
    assert case.base_mva == 100
    assert len(case.matrices["bus"]) == 2383
    assert len(case.matrices["branch"]) == 2896
    assert len(case.matrices["gen"]) == 327
    # MATPOWER column counts: 13 for bus and branch, 21 for gen.
    assert len(case.matrices["bus"][0]) == 13
    assert len(case.matrices["branch"][0]) == 13
    assert len(case.matrices["gen"][0]) == 21
