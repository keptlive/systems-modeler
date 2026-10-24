import json
from pathlib import Path
import pytest
from app.core.model import Model
from app.core.simulator import simulate

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("file,output,expected,changes,changed_expected", [
    ("models/other/kingman-formula-variability-ops.json", "Wait_Time", 4.0, {"Utilization": "0.5"}, 1.0),
    ("models/energy/solar-panel-power-output-ene.json", "Power", 320.0, {"Irradiance": "500.0"}, 160.0),
    ("models/transportation/lighthill-whitham-richards-traffic-tra.json", "Flow", 20*100*(1-20/150), {"Free_Flow_Speed": "50.0"}, 20*50*(1-20/150)),
])
def test_calculator_outputs_and_fixed_inputs(file, output, expected, changes, changed_expected):
    data = json.loads((ROOT / file).read_text())
    for expected_value in (expected, changed_expected):
        model = Model.model_validate(data)
        result = simulate(model, model.time_settings)
        assert result.values[output] == pytest.approx([expected_value] * len(result.time))
        for stock in model.stocks:
            assert result.values[stock.name] == pytest.approx([stock.initial_value] * len(result.time))
        for variable in data["variables"]:
            if variable["name"] in changes:
                variable["equation"] = changes[variable["name"]]
