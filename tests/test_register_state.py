from app.states.register_state import RegisterState


def test_trial_days_default_when_env_missing(monkeypatch):
    monkeypatch.delenv("TRIAL_DAYS", raising=False)
    state = RegisterState()
    assert state._trial_days() == 15


def test_trial_days_uses_env_value(monkeypatch):
    monkeypatch.setenv("TRIAL_DAYS", "21")
    state = RegisterState()
    assert state._trial_days() == 21


def test_trial_days_clamps_invalid_values(monkeypatch):
    state = RegisterState()

    monkeypatch.setenv("TRIAL_DAYS", "0")
    assert state._trial_days() == 1

    monkeypatch.setenv("TRIAL_DAYS", "999")
    assert state._trial_days() == 365

    monkeypatch.setenv("TRIAL_DAYS", "abc")
    assert state._trial_days() == 15
