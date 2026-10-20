"""Source-table restorations: original native output and independent source RHS.

No network access or application-generated expected trajectories. General
scientific validity and unsupported source nonnegative constraints are separate.
"""
import csv
import hashlib
import io
import json
from pathlib import Path

import pytest

from app.core.model import Model, TimeSettings
from app.core.simulator import simulate

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = json.loads((ROOT / "operations/lookup-source-review-v16.json").read_text())
FILES = {"hares": "models/economics/hares-and-lynxes-population-model-eco.json",
         "capability": "models/management/capability-trap-man.json",
         "rookies": "models/management/rookies-and-experts-workforce-model-man.json"}


def load(name):
    return Model.model_validate_json((ROOT / FILES[name]).read_text())


def linear_clamped(x, points):
    """Independent literal source-table arithmetic, without engine lookup code."""
    if x <= points[0][0]:
        return points[0][1]
    for (left, low), (right, high) in zip(points, points[1:]):
        if x <= right:
            return low + (x - left) * (high - low) / (right - left)
    return points[-1][1]


def structure(data):
    data = json.loads(json.dumps(data))
    for field in ("description", "source", "reference", "tables"):
        data.pop(field, None)
    for kind in ("flows", "variables"):
        for element in data[kind]:
            element.pop("equation", None)
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@pytest.mark.parametrize("row", RECEIPT["models"], ids=lambda r: r["id"])
def test_receipt_preserves_every_existing_node_link_setting_and_input(row):
    raw = (ROOT / row["file"]).read_bytes()
    data = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == row["after_sha256"]
    assert structure(data) == row["before_preserved_structure_sha256"]
    assert row["before_preserved_structure_sha256"] == row["after_preserved_structure_sha256"]
    # Equations that were constants remain byte-for-byte unchanged. This also
    # prevents changing parameter inputs merely to make a default complete.
    old_variables = row["changed_fields"]["variables"]["before"]
    after = {v["id"]: v for v in data["variables"]}
    for variable in old_variables:
        try:
            float(variable["equation"])
        except ValueError:
            continue
        recovered_table_nodes = {
            "var-hares-killed-lookup-table", "var-death-fraction-lookup-table",
            "var-influence-of-pressure-on-work-time-table",
            "var-influence-of-capability-pressure-on-improvement-time-table",
            "var-influence-of-work-pressure-on-improvement-time-table",
        }
        if variable["id"] not in recovered_table_nodes:
            assert after[variable["id"]]["equation"] == variable["equation"]


def test_hares_entire_default_grid_and_all_14_series_match_native_stella_csv():
    source = RECEIPT["canonical_output"]
    raw = source["csv_utf8"].encode("utf-8")
    assert hashlib.sha256(raw).hexdigest() == source["sha256"]
    rows = list(csv.DictReader(io.StringIO(source["csv_utf8"])))
    result = simulate(load("hares"))
    assert result.time == [float(row["time"]) for row in rows]
    assert len(rows) == 25
    assert len(source["column_mapping"]) == 14
    for column, current in source["column_mapping"].items():
        for i, row in enumerate(rows):
            # Original CSV prints about 12 significant digits.
            assert result.values[current][i] == pytest.approx(float(row[column]), rel=2e-10, abs=1e-8)
    assert min(result.values["Hares"]) > 0
    assert min(result.values["Lynxes"]) > 0
    assert sum(result.values["Lynx Harvest"]) * .5 == pytest.approx(100)
    # This is a real endpoint-clamping observation in the native trajectory,
    # rather than an assertion that density never leaves the table's domain.
    assert any(value > 100 for value in result.values["Hare Density"])
    for density, mortality in zip(result.values["Hare Density"], result.values["Death Fraction (Lynxes)"]):
        if density > 100:
            assert mortality == pytest.approx(0.00673794699908547)


@pytest.mark.parametrize("name", ["hares", "capability", "rookies"])
def test_every_source_graphical_function_knots_midpoints_and_outside_bounds(name):
    model = load(name)
    sources = RECEIPT["source_graphical_functions"][name]
    names = RECEIPT["table_name_mappings"].get(name, {})
    for table in model.tables:
        expected = sources[names.get(table.name, table.name)]
        assert table.to_list() == [tuple(point) for point in expected]
        assert table.interpolation == "continuous"
        inputs = [expected[0][0] - 100, expected[-1][0] + 100]
        inputs += [p[0] for p in expected]
        inputs += [(a[0] + b[0]) / 2 for a, b in zip(expected, expected[1:])]
        # An unsaved algebraic probe uses the model's actual table objects.
        for x in inputs:
            probe = Model(tables=[table], variables=[{
                "name": "Output", "equation": f'LOOKUP("{table.name}", {x})'}],
                time_settings=TimeSettings(start=0, end=1, dt=1))
            assert simulate(probe).values["Output"][0] == pytest.approx(linear_clamped(x, expected))


@pytest.mark.parametrize("performance,pressure", [(0, 0), (500, 0), (500, .01)])
def test_capability_entire_grid_against_independent_literal_source_euler(performance, pressure):
    model = load("capability")
    for variable in model.variables:
        if variable.name == "Performance Step":
            variable.equation = str(performance)
        if variable.name == "Pressure Step":
            variable.equation = str(pressure)
    result = simulate(model)
    points = RECEIPT["source_graphical_functions"]["capability"]
    capability, work_pressure, improve_pressure = 100., 1., 1.
    dt = .0625
    assert result.time == [i * dt for i in range(1601)]
    for i, time in enumerate(result.time):
        assert result.values["Capability"][i] == pytest.approx(capability, abs=2e-9)
        assert result.values["Pressure to Do Work"][i] == pytest.approx(work_pressure, abs=2e-10)
        assert result.values["Pressure to Improve Capability"][i] == pytest.approx(improve_pressure, abs=2e-10)
        improvement = 10 * linear_clamped(improve_pressure, points["Influence of Capability Pressure on Improvement Time"])
        improvement *= linear_clamped(work_pressure, points["Influence of Work Pressure on Improvement Time"])
        work = min(30 * linear_clamped(work_pressure, points["Influence of Pressure on Work Time"]), 40 - improvement)
        stretch = (3000 + (performance if time >= 10 else 0)) / (capability * work)
        dc = .5 * improvement - capability / 20
        dp = (stretch - work_pressure) / 3
        dq = (stretch - improve_pressure) / 9 + (pressure if time >= 10 else 0)
        capability += dt * dc
        work_pressure += dt * dp
        improve_pressure += dt * dq


def test_rookies_entire_grid_against_independent_literal_source_euler():
    result = simulate(load("rookies"))
    points = RECEIPT["source_graphical_functions"]["rookies"]["Effect of Pressure on Hiring"]
    rookies, experts, backlog, dt = 5., 50., 500., 1 / 32
    assert result.time == [i * dt for i in range(4801)]
    for i in range(len(result.time)):
        for name, value in [("Rookies", rookies), ("Experts", experts), ("Task Backlog", backlog)]:
            assert result.values[name][i] == pytest.approx(value, rel=2e-11, abs=2e-8)
        hiring = linear_clamped((backlog - 500) / 500, points)
        maturation, departure = rookies / 15, experts / 35
        completion = min((40 * experts - 20 * rookies) / 10 + 40 * rookies / 30, backlog)
        assert result.values["Hiring"][i] == pytest.approx(hiring, abs=2e-9)
        assert result.values["Task Completion"][i] == pytest.approx(completion, abs=2e-8)
        rookies, experts, backlog = (rookies + dt * (hiring - maturation),
                                     experts + dt * (maturation - departure),
                                     backlog + dt * (230 - completion))


def test_source_nonnegative_constraint_is_an_explicit_unresolved_semantic_boundary():
    model = load("hares")
    next(v for v in model.variables if v.name == "Size of One-Time Lynx Harvest").equation = "10000"
    result = simulate(model, TimeSettings(start=0, end=5, dt=.5))
    # Do not silently add a clamp or imply arbitrary scenarios are equivalent to
    # the native model's explicit nonnegative stock and flow declarations.
    assert min(result.values["Lynxes"]) < 0
