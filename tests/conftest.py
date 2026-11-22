"""Shared pytest fixtures. The fakes live in ``fake_expdll.py`` so tests can import them too."""

import pytest
from fake_expdll import FakeLegacyExpDLL, FakeV12ExpDLL, make_expedition


@pytest.fixture
def fake_legacy_dll():
    """A fake legacy ExpDLL (has GetVariation, no GetExpVar2)."""
    return FakeLegacyExpDLL()


@pytest.fixture
def fake_v12_dll():
    """A fake ExpDLL 1.2 (has GetExpVar2 and SetExpVar2, no GetVariation)."""
    return FakeV12ExpDLL()


@pytest.fixture
def make_fake_expedition():
    """Factory returning ``(expedition, fake_dll)`` for a chosen API version.

    Keyword arguments other than ``api`` and ``strict`` go to the fake DLL's constructor,
    for example ``make_fake_expedition("1.2", running=False, gps_from_dll=True)``.
    """

    def factory(api="legacy", *, strict=False, **settings):
        if api == "1.2":
            fake = FakeV12ExpDLL(**settings)
        elif api == "legacy":
            fake = FakeLegacyExpDLL(**settings)
        else:
            raise ValueError(f"api must be 'legacy' or '1.2', got {api!r}")
        return make_expedition(fake, strict=strict), fake

    return factory
