"""Partition B provenance and independent mathematical checks.

Source-concept references do not certify calibration. In particular a completed
Euler pendulum run still has unacceptable energy drift, recorded in the ledger.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

import pytest

from app.core.integration import evaluate
from app.core.model import Model, TimeSettings
from app.core.simulator import simulate

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'operations/corpus-reconciliation-v17-b.json'


def load(stem):
    paths = list((ROOT / 'models').rglob(stem + '.json'))
    assert len(paths) == 1
    return Model.model_validate_json(paths[0].read_text())


def initial(model):
    return evaluate(model, {s.name: s.initial_value for s in model.stocks},
                    model.time_settings.start, model.time_settings.dt, {}, {}, initial=True)


def reconstruct_original(current, row):
    original = copy.deepcopy(current)
    for change in reversed(row['changed_fields']):
        parts = change['field'].strip('/').split('/')
        target = original
        for part in parts[:-1]:
            target = target[int(part)] if isinstance(target, list) else target[part]
        key = int(parts[-1]) if isinstance(target, list) else parts[-1]
        assert target[key] == change['after']
        target[key] = change['before']
    return original


def test_partition_b_receipt_complete_and_preserves_model_structure():
    ledger = json.loads(LEDGER.read_text())
    baseline = json.loads((ROOT / 'operations/library-full-v160.json').read_text())
    assigned = sorted((r for r in baseline['models'] if r['status'] == 'failed'),
                      key=lambda r:r['file'])[1::3]
    assert [r['file'] for r in ledger['models']] == [r['file'] for r in assigned]
    assert len(assigned) == 45
    for row, old in zip(ledger['models'], assigned):
        current = json.loads((ROOT / row['file']).read_text())
        original = reconstruct_original(current, row)
        assert row['original_sha256'] == old['sha256']
        assert row['current_sha256'] == hashlib.sha256((ROOT / row['file']).read_bytes()).hexdigest()
        assert row['diagnosis'] and row['source_scope'] and row['validation_status']
        assert row['current_run']['status'] in ('passed', 'failed')
        assert current['id'] == original['id']
        assert current['time_settings'] == original['time_settings']
        assert current['connectors'] == original['connectors']
        for kind in ('stocks', 'flows', 'variables'):
            assert len(current[kind]) == len(original[kind])
            for before, after in zip(original[kind], current[kind]):
                for field in ('id', 'position', 'from_stock', 'to_stock', 'initial_value', 'units'):
                    assert after.get(field) == before.get(field)
                assert after['name'] == row['notation_translation'].get(before['name'], before['name'])


def test_aging_chain_source_equations_and_population_accounting():
    model = load('aging-chain-population-cohorts-edu')
    run = simulate(model)
    # Exact source has nine initial cohorts10, births0, mortality.05/year.
    # All birthdays are internal transfers and cancel from the total balance.
    assert [s.initial_value for s in model.stocks] == [10] * 9
    assert run.values['10th Birthday'][0] == 1
    assert run.values['Decade 1 Loss'][0] == .5
    total = [sum(run.values[s.name][i] for s in model.stocks) for i in range(len(run.time))]
    for i, value in enumerate(total):
        assert value == pytest.approx(90 * (1 - .05 * model.time_settings.dt) ** i, rel=2e-12)
    assert min(min(run.values[s.name]) for s in model.stocks) >= 0


def test_dengue_reconstructed_normalizer_conserves_both_populations():
    model = load('dengue-vector-borne-disease-model-epi')
    assert '(Sh + Ih + Rh)' in model.description
    assert 'mathematical reconstruction' in model.description
    assert 'fidelity remains unverified' in model.description
    assert 'Nh without a declared variable' not in model.description
    run = simulate(model)
    for i in range(len(run.time)):
        assert sum(run.values[n][i] for n in ('Sh', 'Ih', 'Rh')) == pytest.approx(10000, abs=2e-9)
        # Existing mosquito recruitment2500 and mortality.05 give50000 equilibrium.
        assert run.values['Sv'][i] + run.values['Iv'][i] == pytest.approx(50000, abs=2e-8)
    assert min(min(run.values[s.name]) for s in model.stocks) >= 0


def test_case_sensitive_science_symbols_are_translated_without_merging():
    cell = load('cell-cycle-regulation-phy')
    v = initial(cell)
    assert v['Parameter lowercase k3'] == 1
    assert v['Parameter uppercase K3'] == .5
    assert v['CDK_Activation'] == pytest.approx(.05 / .55)
    assert v['CDK_Inactivation'] == pytest.approx(.05 * .3 / .55)
    allee = load('predator-prey-allee-effect-eco')
    v = initial(allee)
    assert v['Attack coefficient (lowercase a)'] == .02
    assert v['Allee scale (uppercase A)'] == 20
    assert v['Allee Factor'] == pytest.approx(100 / 120)


def test_bounded_confidence_averages_are_convex_and_symmetric():
    model = load('bounded-confidence-opinion-soc')
    v = initial(model)
    assert [v[n] for n in ('Weighted Avg 1', 'Weighted Avg 2', 'Weighted Avg 3')] == pytest.approx([-.15, 0, .15])
    run = simulate(model)
    for left, center, right in zip(run.values['Moderate Left Opinion'], run.values['Centrist Opinion'], run.values['Moderate Right Opinion']):
        assert -.3 <= left <= center <= right <= .3
        assert left == pytest.approx(-right, abs=1e-14)
        assert center == pytest.approx(0, abs=1e-14)


def energy(run):
    # E = .5*m*l^2*omega^2 + m*g*l*(1-cos(theta)); source m=l=10.
    return [.5 * 1000 * w*w + 980 * (1-math.cos(a))
            for a,w in zip(run.values['Angular Position'], run.values['Angular Velocity'])]


def test_original_pendulum_grid_runs_and_exposes_euler_energy_error():
    model = load('simple-pendulum-phy')
    assert model.time_settings.dt == .0078125
    run = simulate(model)
    assert len(run.time) == 12801 and run.time[-1] == 100
    coarse = energy(run)
    # This is an explicit diagnostic regression, not an accuracy acceptance test.
    assert coarse[-1] / coarse[0] - 1 == pytest.approx(.836735652232, rel=1e-9)
    # The same equations solved with RK4 conserve the independent physical invariant.
    refined = simulate(model, TimeSettings(start=0, end=100, dt=.03125, integration_method='rk4'))
    accurate = energy(refined)
    assert max(abs(e / accurate[0] - 1) for e in accurate) < 2e-7


def test_missing_originals_remain_explicit_failures():
    for stem, error in [('arctic-sea-ice-decline-model-cli', 'feedback_amplification'),
                        ('measles-vaccination-coverage-model-epi', 'beta'),
                        ('tuberculosis-transmission-model-epi', 'Unknown variable: N')]:
        with pytest.raises(Exception, match=error):
            simulate(load(stem))


def test_unresolved_boundary_failure_has_independent_first_step_evidence():
    model = load('workforce-overtime-morale-man')
    v = initial(model)
    assert v['Work_Completion'] == 2400
    assert 200 + .5 * (200 - v['Work_Completion']) == -900
    # No silent resource-floor correction was introduced in a definition.
    assert next(f for f in model.flows if f.name == 'Work_Completion').equation == 'Workforce * Productivity * Hours_Worked'
