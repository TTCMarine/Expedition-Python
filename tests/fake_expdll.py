"""Fake ExpDLL for the unit tests. It needs no Expedition install and runs on any platform.

The fakes model the parts of the DLL the wrapper relies on:

- channel storage for ``SetExpVar`` / ``GetExpVar``, and ``SetExpVar2`` / ``GetExpVar2`` on
  the 1.2 fake;
- writes to ``Var.Utc`` are ignored;
- writes are ignored while Expedition is not running (``running=False``);
- boat 0 GPS channels are ignored unless ``gps_from_dll=True``;
- alternating channels (``Alt0``..``Alt9``) resolve through ``alt_map``.
"""

import ctypes
from unittest.mock import patch

from Expedition import ExpeditionDLL, ExVal, ValType, Var, _loader
from Expedition.dll_wrapper import GPS_BOAT0_CHANNELS

FAKE_CHANNELS = 418
FAKE_BOATS = 100
FAKE_INVALID = 32767.0

__all__ = [
    "FAKE_BOATS",
    "FAKE_CHANNELS",
    "FAKE_INVALID",
    "FakeCFunction",
    "FakeLegacyExpDLL",
    "FakeV12ExpDLL",
    "make_expedition",
]


class FakeCFunction:
    def __init__(self, impl=None, return_value=None):
        self.impl = impl
        self.return_value = return_value
        self.argtypes = None
        self.restype = None
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        if self.impl is not None:
            return self.impl(*args)
        return self.return_value


def _to_int(value):
    return int(value.value) if hasattr(value, "value") else int(value)


class _FakeExpDLLBase:
    """Models the parts of ExpDLL that the wrapper relies on.

    Constructor arguments:

    - ``running``: when False, writes are ignored and reads of ``Utc`` return the invalid
      sentinel.
    - ``gps_from_dll``: when True, writes to boat 0 GPS channels are kept.
    - ``alt_map``: maps an alternating channel ID to the channel it currently resolves to.
    """

    def __init__(self, *, running=True, gps_from_dll=False, alt_map=None):
        self.vars = {}
        self.ex_vals = {}
        self.var_precision = {}
        self.boat_names = {}
        self.boat_colours = {}
        self.ais_dangerous = True
        self.ais_name = "AIS TARGET"
        self.running = running
        self.gps_from_dll = gps_from_dll
        self.utc = 45000.5
        self.alt_map = dict(alt_map or {})

        self.GetExpVarNum = FakeCFunction(return_value=FAKE_CHANNELS)
        self.GetExpVarName = FakeCFunction(impl=self._get_exp_var_name)
        self.SetExpUserVarName = FakeCFunction()
        self.SetExpVar = FakeCFunction(impl=self._set_exp_var)
        self.GetExpVar = FakeCFunction(impl=self._get_exp_var)
        self.GetSysVar = FakeCFunction(impl=self._get_sys_var)
        self.GetSysBool = FakeCFunction(impl=self._get_sys_bool)
        self.GetBoatNum = FakeCFunction(return_value=FAKE_BOATS)
        self.SetMOB = FakeCFunction()

    def _get_exp_var_name(self, var_id, name_buf):
        var_name = "User0" if _to_int(var_id) == int(Var.User0) else "Bsp"
        name_buf.value = var_name.encode("utf-8")

    def _is_dropped(self, var_id, boat_id):
        if var_id == int(Var.Utc) or not self.running:
            return True
        return boat_id == 0 and not self.gps_from_dll and var_id in GPS_BOAT0_CHANNELS

    def _set_exp_var(self, var_id, value, boat):
        key = (_to_int(var_id), _to_int(boat))
        if self._is_dropped(*key):
            return
        self.vars[key] = float(value.value)

    def _lookup(self, var, boat_id):
        """Return ``(value, resolved_id)`` for a double read, or None if there is no value."""
        if var == int(Var.Utc) and boat_id == 0:
            return (self.utc if self.running else FAKE_INVALID), var
        resolved = self.alt_map.get(var, var)
        key = (resolved, boat_id)
        if key not in self.vars:
            return None
        return self.vars[key], resolved

    def _get_exp_var(self, var_id, value_out, boat, id_alt_out):
        found = self._lookup(_to_int(var_id), _to_int(boat))
        if found is None:
            return False
        value_out._obj.value, id_alt_out._obj.value = found
        return True

    def _get_sys_var(self, var_id, value_out):
        value_out._obj.value = 12.5
        return True

    def _get_sys_bool(self, var_id, value_out):
        value_out._obj.value = True
        return True


class FakeLegacyExpDLL(_FakeExpDLLBase):
    def __init__(self, **settings):
        super().__init__(**settings)
        self.SetVarPrecision = FakeCFunction(impl=self._set_var_precision)
        self.GetVarPrecision = FakeCFunction(impl=self._get_var_precision)
        self.SetExpVars = FakeCFunction(impl=self._set_exp_vars)
        self.GetExpVars = FakeCFunction(impl=self._get_exp_vars)
        self.SetBoatName = FakeCFunction(impl=self._set_boat_name)
        self.GetBoatColour = FakeCFunction(impl=self._get_boat_colour)
        self.SetBoatColour = FakeCFunction(impl=self._set_boat_colour)
        self.GetVariation = FakeCFunction(impl=self._get_variation)
        self.GetAisDangerousCPA = FakeCFunction(impl=self._get_ais_dangerous_cpa)
        self.PingMark = FakeCFunction()
        self.CreateActiveRoute = FakeCFunction()
        self.AddMarkToActiveRoute = FakeCFunction()

    def _set_var_precision(self, var_id, precision):
        self.var_precision[_to_int(var_id)] = _to_int(precision)

    def _get_var_precision(self, var_id, precision_out):
        precision_out._obj.value = self.var_precision.get(_to_int(var_id), 0)

    def _set_exp_vars(self, var_ids, values, n_vals, boat):
        count = _to_int(n_vals)
        boat_id = _to_int(boat)
        for index in range(count):
            self._set_exp_var(
                ctypes.c_uint16(var_ids[index]), ctypes.c_double(values[index]), boat_id
            )

    def _get_exp_vars(self, var_ids, values_out, n_vals, boat):
        count = _to_int(n_vals)
        boat_id = _to_int(boat)
        for index in range(count):
            key = (int(var_ids[index]), boat_id)
            if key not in self.vars:
                return False
            values_out[index] = self.vars[key]
        return True

    def _set_boat_name(self, boat, name):
        self.boat_names[_to_int(boat)] = name.decode("utf-8")

    def _set_boat_colour(self, boat, r, g, b):
        self.boat_colours[_to_int(boat)] = (_to_int(r), _to_int(g), _to_int(b))

    def _get_boat_colour(self, boat, r_out, g_out, b_out):
        r, g, b = self.boat_colours.get(_to_int(boat), (0, 0, 0))
        r_out._obj.value = r
        g_out._obj.value = g
        b_out._obj.value = b

    def _get_variation(self, utc, lat, lon, variation_out):
        variation_out._obj.value = 2.75
        return True

    def _get_ais_dangerous_cpa(self, dangerous_out, name_buf, name_len):
        dangerous_out._obj.value = self.ais_dangerous
        name_buf.value = self.ais_name


class FakeV12ExpDLL(_FakeExpDLLBase):
    def __init__(self, **settings):
        super().__init__(**settings)
        self.SetExpVar2 = FakeCFunction(impl=self._set_exp_var2)
        self.GetExpVar2 = FakeCFunction(impl=self._get_exp_var2)

    def _set_exp_var2(self, var_id, value, boat):
        key = (_to_int(var_id), _to_int(boat))
        ex_val = ExVal.from_struct(value)
        if self._is_dropped(*key):
            return
        self.ex_vals[key] = ex_val
        if ex_val.type is ValType.Double:
            self.vars[key] = ex_val.as_double()

    def _get_exp_var2(self, var_id, value_out, boat, id_alt_out):
        var = _to_int(var_id)
        boat_id = _to_int(boat)
        key = (var, boat_id)
        if key in self.ex_vals:
            stored = self.ex_vals[key].to_struct()
            resolved = var
        else:
            found = self._lookup(var, boat_id)
            if found is None:
                return False
            # Values written through SetExpVar are doubles on the 1.2 DLL too.
            stored = ExVal.from_double(found[0]).to_struct()
            resolved = found[1]
        dest = value_out._obj
        dest.type = stored.type
        dest.u = stored.u
        id_alt_out._obj.value = resolved
        return True


def make_expedition(fake_dll, strict=False):
    """Create an ExpeditionDLL that loads ``fake_dll`` instead of a real ExpDLL.dll."""
    windll = type("FakeWindll", (), {"LoadLibrary": lambda _, __: fake_dll})()
    with (
        patch("os.path.exists", return_value=True),
        patch.object(ctypes, "windll", windll, create=True),
        patch.object(_loader, "preflight", return_value="AMD64"),
    ):
        return ExpeditionDLL("C:/fake", strict=strict)
