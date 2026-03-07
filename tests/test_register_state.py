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


def test_register_state_inherits_hard_redirect_helper():
    state = RegisterState()

    script = state._hard_redirect_script("/dashboard")

    assert "window.location.replace" in script
    assert '"/dashboard"' in script


def test_runtime_bootstrap_script_waits_before_clicking():
    from app.app import _runtime_bootstrap_script

    script = _runtime_bootstrap_script()

    assert 'data-runtime-loaded' in script
    assert "setTimeout(trigger, 0)" not in script
    assert "setTimeout(trigger, 900)" in script
