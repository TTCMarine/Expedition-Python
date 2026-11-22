"""Pure-Python checks that run before ExpDLL.dll is loaded. No Expedition install needed."""

import struct
import tempfile
import warnings
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from Expedition import ExpeditionLoadError, ExpeditionVersionWarning, _loader


def make_pe(machine: int, *, truncate: bool = False, bad_magic: bool = False) -> bytes:
    """Build the smallest header that read_pe_machine accepts."""
    dos = bytearray(0x80)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, 0x80)
    pe = b"PE\x00\x00" + struct.pack("<H", machine) + b"\x00" * 18
    data = bytes(dos) + pe
    if bad_magic:
        data = data[:0x80] + b"NE\x00\x00" + data[0x84:]
    if truncate:
        data = data[:0x82]
    return data


class TempFolder(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name: str, data: bytes) -> str:
        path = self.folder / name
        path.write_bytes(data)
        return str(path)


class TestReadPeMachine(TempFolder):
    def test_amd64(self):
        path = self.write("ExpDLL.dll", make_pe(0x8664))
        self.assertEqual(_loader.read_pe_machine(path), 0x8664)

    def test_arm64(self):
        path = self.write("ExpDLL.dll", make_pe(0xAA64))
        self.assertEqual(_loader.read_pe_machine(path), 0xAA64)

    def test_x86_is_read_but_not_supported(self):
        path = self.write("ExpDLL.dll", make_pe(0x14C))
        self.assertEqual(_loader.read_pe_machine(path), 0x14C)
        self.assertIsNone(_loader.dll_architecture(0x14C))

    def test_truncated_file_is_rejected(self):
        path = self.write("ExpDLL.dll", make_pe(0x8664, truncate=True))
        with self.assertRaises(ExpeditionLoadError):
            _loader.read_pe_machine(path)

    def test_missing_mz_is_rejected(self):
        path = self.write("ExpDLL.dll", b"not a dll at all" * 10)
        with self.assertRaises(ExpeditionLoadError):
            _loader.read_pe_machine(path)

    def test_missing_pe_signature_is_rejected(self):
        path = self.write("ExpDLL.dll", make_pe(0x8664, bad_magic=True))
        with self.assertRaises(ExpeditionLoadError):
            _loader.read_pe_machine(path)

    def test_missing_file_is_load_error(self):
        with self.assertRaises(ExpeditionLoadError):
            _loader.read_pe_machine(str(self.folder / "absent.dll"))


class TestInterpreterArchitecture(TestCase):
    def test_64_bit_amd64(self):
        with (
            patch.object(_loader.platform, "machine", return_value="AMD64"),
            patch.object(_loader.struct, "calcsize", return_value=8),
        ):
            self.assertEqual(_loader.interpreter_architecture(), "AMD64")

    def test_64_bit_arm64(self):
        with (
            patch.object(_loader.platform, "machine", return_value="ARM64"),
            patch.object(_loader.struct, "calcsize", return_value=8),
        ):
            self.assertEqual(_loader.interpreter_architecture(), "ARM64")

    def test_32_bit(self):
        with patch.object(_loader.struct, "calcsize", return_value=4):
            self.assertEqual(_loader.interpreter_architecture(), "32-bit")


class TestArchitectureMismatch(TempFolder):
    def test_matching_pairs_are_accepted(self):
        for machine, arch in ((0x8664, "AMD64"), (0xAA64, "ARM64")):
            with self.subTest(arch=arch):
                path = self.write("ExpDLL.dll", make_pe(machine))
                self.assertEqual(_loader.check_dll_architecture(path, python_arch=arch), arch)

    def test_mismatched_pairs_are_rejected(self):
        cases = (
            (0xAA64, "AMD64"),  # ARM64 DLL, x64 Python
            (0x8664, "ARM64"),  # AMD64 DLL, native ARM64 Python
            (0x8664, "32-bit"),  # AMD64 DLL, 32-bit Python
            (0xAA64, "32-bit"),
        )
        for machine, python_arch in cases:
            with self.subTest(machine=hex(machine), python=python_arch):
                path = self.write("ExpDLL.dll", make_pe(machine))
                with self.assertRaises(ExpeditionLoadError) as caught:
                    _loader.check_dll_architecture(path, python_arch=python_arch)
                self.assertIn("this Python is " + python_arch, str(caught.exception))

    def test_arm64_dll_on_x64_python_points_at_build_options(self):
        path = self.write("ExpDLL.dll", make_pe(0xAA64))
        with self.assertRaises(ExpeditionLoadError) as caught:
            _loader.check_dll_architecture(path, python_arch="AMD64")
        message = str(caught.exception)
        self.assertIn("native ARM64 Python", message)
        self.assertIn("ExpeditionX64", message)

    def test_amd64_dll_on_arm64_python_mentions_emulation(self):
        path = self.write("ExpDLL.dll", make_pe(0x8664))
        with self.assertRaises(ExpeditionLoadError) as caught:
            _loader.check_dll_architecture(path, python_arch="ARM64")
        message = str(caught.exception)
        self.assertIn("emulation", message)
        self.assertIn("ExpeditionARM", message)

    def test_x86_dll_is_rejected_before_interpreter_check(self):
        path = self.write("ExpDLL.dll", make_pe(0x14C))
        with self.assertRaises(ExpeditionLoadError) as caught:
            _loader.check_dll_architecture(path, python_arch="AMD64")
        self.assertIn("32-bit builds are not", str(caught.exception))

    def test_interpreter_is_detected_when_not_given(self):
        path = self.write("ExpDLL.dll", make_pe(0x8664))
        with patch.object(_loader, "interpreter_architecture", return_value="AMD64"):
            self.assertEqual(_loader.check_dll_architecture(path), "AMD64")
        with patch.object(_loader, "interpreter_architecture", return_value="ARM64"):
            with self.assertRaises(ExpeditionLoadError):
                _loader.check_dll_architecture(path)


class TestCompanionLibrary(TempFolder):
    def test_arm64_companion_required(self):
        with self.assertRaises(ExpeditionLoadError) as caught:
            _loader.check_companion_library(str(self.folder), "ARM64")
        self.assertIn("libcrypto-3-arm64.dll", str(caught.exception))

    def test_amd64_companion_present(self):
        self.write("libcrypto-3-x64.dll", b"")
        _loader.check_companion_library(str(self.folder), "AMD64")

    def test_amd64_companion_missing_names_x64_file(self):
        with self.assertRaises(ExpeditionLoadError) as caught:
            _loader.check_companion_library(str(self.folder), "AMD64")
        self.assertIn("libcrypto-3-x64.dll", str(caught.exception))


class TestExeMismatchWarning(TempFolder):
    def test_warns_when_exe_architecture_differs(self):
        self.write("Expedition.exe", make_pe(0xAA64))
        with self.assertWarns(ExpeditionVersionWarning):
            _loader.warn_if_exe_mismatch(str(self.folder), "AMD64")

    def test_silent_when_exe_matches(self):
        self.write("Expedition.exe", make_pe(0x8664))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _loader.warn_if_exe_mismatch(str(self.folder), "AMD64")
        self.assertFalse(caught)

    def test_silent_when_exe_absent_or_unreadable(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _loader.warn_if_exe_mismatch(str(self.folder), "AMD64")
            self.write("Expedition.exe", b"junk")
            _loader.warn_if_exe_mismatch(str(self.folder), "AMD64")
        self.assertFalse(caught)


class TestPreflight(TempFolder):
    def test_arm64_build_with_companion_passes(self):
        dll = self.write("ExpDLL.dll", make_pe(0xAA64))
        self.write("libcrypto-3-arm64.dll", b"")
        with patch.object(_loader, "interpreter_architecture", return_value="ARM64"):
            self.assertEqual(_loader.preflight(dll), "ARM64")

    def test_amd64_build_without_companion_fails(self):
        dll = self.write("ExpDLL.dll", make_pe(0x8664))
        with patch.object(_loader, "interpreter_architecture", return_value="AMD64"):
            with self.assertRaises(ExpeditionLoadError):
                _loader.preflight(dll)

    def test_both_builds_are_separate_folders(self):
        arm = self.folder / "ExpeditionARM"
        x64 = self.folder / "ExpeditionX64"
        arm.mkdir()
        x64.mkdir()
        (arm / "ExpDLL.dll").write_bytes(make_pe(0xAA64))
        (x64 / "ExpDLL.dll").write_bytes(make_pe(0x8664))
        (x64 / "libcrypto-3-x64.dll").write_bytes(b"")
        with patch.object(_loader, "interpreter_architecture", return_value="AMD64"):
            self.assertEqual(_loader.preflight(str(x64 / "ExpDLL.dll")), "AMD64")
            with self.assertRaises(ExpeditionLoadError):
                _loader.preflight(str(arm / "ExpDLL.dll"))
