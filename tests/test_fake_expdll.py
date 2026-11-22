"""Checks that the shared fake DLL models what the wrapper relies on. Needs no DLL."""

import pytest

from Expedition import ExpeditionWriteWarning, ExVal, Var


def test_utc_writes_are_rejected_before_the_dll(make_fake_expedition):
    expedition, fake = make_fake_expedition()
    with pytest.raises(ValueError, match="Utc|between 1"):
        expedition.set_exp_var_value(Var.Utc, 1.0)
    assert fake.SetExpVar.calls == []


def test_writes_are_dropped_when_not_running(make_fake_expedition):
    expedition, fake = make_fake_expedition(running=False)
    expedition.set_exp_var_value(Var.Bsp, 7.5)
    assert (int(Var.Bsp), 0) not in fake.vars
    assert expedition.get_exp_var_value(Var.Bsp) is None


def test_boat0_gps_write_is_dropped_by_default(make_fake_expedition):
    expedition, fake = make_fake_expedition()
    with pytest.warns(ExpeditionWriteWarning):
        expedition.set_exp_var_value(Var.Lat, 50.8, boat=0)
    assert (int(Var.Lat), 0) not in fake.vars


def test_gps_from_dll_keeps_boat0_gps_writes(make_fake_expedition):
    expedition, fake = make_fake_expedition(gps_from_dll=True)
    # The wrapper warns about boat 0 GPS writes whatever the fake's GPS source is.
    with pytest.warns(ExpeditionWriteWarning):
        expedition.set_exp_var_value(Var.Lat, 50.8, boat=0)
    assert fake.vars[(int(Var.Lat), 0)] == pytest.approx(50.8)


def test_alt_map_resolves_alternating_channel(make_fake_expedition):
    expedition, _ = make_fake_expedition(alt_map={int(Var.Alt0): int(Var.Bsp)})
    expedition.set_exp_var_value(Var.Bsp, 7.5)
    reading = expedition.get_exp_var_ex(Var.Alt0)
    assert reading is not None
    assert reading.value == pytest.approx(7.5)
    assert reading.resolved_var == Var.Bsp


def test_v12_set_exp_var2_round_trips_double(make_fake_expedition):
    expedition, _ = make_fake_expedition("1.2")
    expedition.set_exp_var2(Var.Bsp, ExVal.from_double(3.25))
    stored = expedition.get_exp_var2(Var.Bsp)
    assert stored is not None
    assert stored.as_double() == pytest.approx(3.25)


def test_v12_reads_values_written_with_set_exp_var(make_fake_expedition):
    expedition, _ = make_fake_expedition("1.2")
    expedition.set_exp_var_value(Var.Bsp, 4.0)
    assert expedition.get_exp_var_value(Var.Bsp) == pytest.approx(4.0)


def test_unknown_api_name_is_rejected(make_fake_expedition):
    with pytest.raises(ValueError, match="api"):
        make_fake_expedition("3.0")
