"""Enum generator and header comparison.

The parser tests always run. The header comparison skips unless the proprietary headers
have been synced into reference/expedition/ (see scripts/sync_expedition_headers.py).
"""

import sys
from pathlib import Path
from unittest import TestCase, skipIf

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_enums_against_headers  # noqa: E402
from _header_enums import (  # noqa: E402
    ENUM_SPECS,
    REFERENCE_DIR,
    EnumSpec,
    find_missing_headers,
    load_enums,
    parse_enum,
    preprocess,
    python_member_name,
)

import Expedition.enums as enums  # noqa: E402

HEADERS_MISSING = find_missing_headers(REFERENCE_DIR) is not None


class TestHeaderParser(TestCase):
    def test_comments_and_ifdef_blocks_are_removed(self):
        text = """
        // ExBogus = 99
        enum ExChannels : int {
            ExUtc = 0,  /* first */
        #ifdef EX_SAIL_AI
            ExSailAi = 1,
        #endif
            ExBsp,
        };
        """
        self.assertEqual(parse_enum(text, "ExChannels"), {"ExUtc": 0, "ExBsp": 1})

    def test_ifdef_branch_taken_when_macro_defined(self):
        text = "#ifdef FOO\nA = 1,\n#else\nA = 2,\n#endif\n"
        self.assertIn("A = 1", preprocess(text, defines={"FOO"}))
        self.assertIn("A = 2", preprocess(text, defines=set()))

    def test_alias_resolves_to_previous_value(self):
        text = "enum ExChannels : int { ExAlt0 = 5, ExAltMax = ExAlt0 };"
        self.assertEqual(parse_enum(text, "ExChannels"), {"ExAlt0": 5, "ExAltMax": 5})

    def test_implicit_values_follow_explicit_ones(self):
        text = "enum ExSysChannels : int { ExSysA = 4, ExSysB, ExSysC = 10, ExSysD };"
        self.assertEqual(
            parse_enum(text, "ExSysChannels"),
            {"ExSysA": 4, "ExSysB": 5, "ExSysC": 10, "ExSysD": 11},
        )

    def test_member_names_strip_prefixes(self):
        by_c_name = {spec.c_name: spec for spec in ENUM_SPECS}
        channels = by_c_name["ExChannels"]
        self.assertEqual(python_member_name(channels, "ExSysGpsTimeDelta"), "SysGpsTimeDelta")
        self.assertEqual(
            python_member_name(channels, "EXCANFastPacketErrors"), "CANFastPacketErrors"
        )
        booleans = by_c_name["ExSysBooleanChannels"]
        self.assertEqual(python_member_name(booleans, "ExSysBoolAutoPan"), "AutoPan")
        system = by_c_name["ExSysChannels"]
        self.assertEqual(python_member_name(system, "ExSysBoatLength"), "BoatLength")
        self.assertEqual(python_member_name(system, "ExNumSysChannels"), "NumSysChannels")

    def test_unknown_prefix_is_rejected(self):
        spec = EnumSpec("ExSysChannels", "SysVar", "sys_channels.h", "ExSys")
        with self.assertRaises(ValueError):
            python_member_name(spec, "Bogus")


class TestCommittedEnums(TestCase):
    """Values that Expedition depends on, checked without the headers."""

    def test_known_ids(self):
        self.assertEqual(int(enums.Var.NumChannels), 418)
        self.assertEqual(int(enums.Var.BowLat), 414)
        self.assertEqual(int(enums.Var.SysGpsTimeDelta), 256)
        self.assertEqual(int(enums.SysVar.CalTwa), 57)
        self.assertEqual(int(enums.SysVar.NumSysChannels), 76)
        self.assertEqual(int(enums.SysBooleanVar.AutoPan), 0)

    def test_boolean_and_int_enums_are_int_enums(self):
        self.assertTrue(issubclass(enums.SysBooleanVar, int))
        self.assertTrue(issubclass(enums.SysIntVar, int))
        self.assertFalse(hasattr(enums.SysBooleanVar, "lAutoPan"))

    def test_bow_and_stern_positions_removed_from_sys_var(self):
        for name in ("BowLat", "BowLon", "SternLat", "SternLon"):
            self.assertFalse(hasattr(enums.SysVar, name), name)


@skipIf(HEADERS_MISSING, "Expedition headers not synced into reference/expedition/")
class TestEnumsMatchHeaders(TestCase):
    def test_generated_enums_match_headers(self):
        expected = load_enums(REFERENCE_DIR)
        self.assertEqual(check_enums_against_headers.compare(expected, enums), [])

    def test_generator_output_matches_committed_file(self):
        from generate_enums_from_headers import render

        expected = load_enums(REFERENCE_DIR)
        generated = render(expected, "reference/expedition (gitignored)")
        committed = (REPO_ROOT / "Expedition" / "enums.py").read_text(encoding="utf-8")
        self.assertEqual(generated, committed)
