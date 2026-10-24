"""Unmodified, attributed SDXorg scalar imports against independent reference data."""
import csv
from pathlib import Path

import numpy as np
import pytest

from app.core.xmile_parser import parse_xmile
from app.core.simulator import simulate

FIXTURES = Path(__file__).parent / "fixtures" / "sdxorg"


@pytest.mark.parametrize("sample,filename,rows", [("SIR", "SIR.xmile", 3201), ("teacup", "teacup.xmile", 241)])
def test_scalar_export_with_empty_dimensions_matches_reference(sample, filename, rows):
    model = parse_xmile((FIXTURES / sample / filename).read_text())
    result = simulate(model)
    with (FIXTURES / sample / "output.csv").open(newline="") as stream:
        reference = list(csv.DictReader(stream))
    assert len(result.time) == len(reference) == rows
    normalize = lambda name: name.lower().replace(" ", "_")
    columns = {normalize(name): name for name in reference[0]}
    # Historical Vensim CSV exports have about six significant digits;
    # tolerance includes reference rounding and small implementation differences.
    np.testing.assert_allclose(result.time, [float(row["Time"]) for row in reference], rtol=6e-6, atol=5e-6)
    for name, values in result.values.items():
        column = columns[normalize(name)]
        np.testing.assert_allclose(values, [float(row[column]) for row in reference], rtol=6e-6, atol=5e-6)


@pytest.mark.parametrize("declaration", ['<dim name="Region" size="2"/>', '<dim name="Region"><elem name="North"/></dim>'])
def test_nonempty_dimension_declarations_remain_unsupported(declaration):
    xml = '<xmile><dimensions>' + declaration + '</dimensions><model><variables/></model></xmile>'
    with pytest.raises(ValueError, match="arrays are not supported"):
        parse_xmile(xml)


def test_empty_dimensions_does_not_allow_nested_models():
    with pytest.raises(ValueError, match="Nested models"):
        parse_xmile('<xmile><dimensions/><model/><model/></xmile>')
