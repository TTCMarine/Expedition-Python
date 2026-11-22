"""Exact-value tests for WinRT tick conversion. No DLL needed."""

import calendar
from datetime import datetime, timedelta, timezone
from unittest import TestCase

from Expedition.exval import (
    datetime_to_winrt_ticks,
    timedelta_to_winrt_ticks,
    winrt_ticks_to_datetime,
    winrt_ticks_to_timedelta,
)

# Seconds between 1601-01-01 and 1970-01-01 (the Unix epoch).
UNIX_TO_WINRT_SECONDS = 11_644_473_600
TICKS_PER_SECOND = 10_000_000


def independent_ticks(dt_utc: datetime) -> int:
    """Expected ticks for an aware UTC datetime, computed without the module under test."""
    unix_seconds = calendar.timegm(dt_utc.utctimetuple())
    return (unix_seconds + UNIX_TO_WINRT_SECONDS) * TICKS_PER_SECOND + dt_utc.microsecond * 10


class TestDatetimeToTicks(TestCase):
    def test_epoch_values(self):
        self.assertEqual(datetime_to_winrt_ticks(datetime(1601, 1, 1, tzinfo=timezone.utc)), 0)
        self.assertEqual(
            datetime_to_winrt_ticks(datetime(1970, 1, 1, tzinfo=timezone.utc)),
            116_444_736_000_000_000,
        )

    def test_microsecond_value_is_exact(self):
        # The float version returned ...784 here; the exact value is ...780.
        dt = datetime(2026, 11, 22, 13, 31, 12, 345678, tzinfo=timezone.utc)
        self.assertEqual(datetime_to_winrt_ticks(dt), 134_398_278_723_456_780)
        self.assertEqual(datetime_to_winrt_ticks(dt), independent_ticks(dt))

    def test_matches_independent_calculation_over_range(self):
        samples = [
            datetime(1700, 3, 1, 0, 0, 0, 1, tzinfo=timezone.utc),
            datetime(1999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
            datetime(2038, 1, 19, 3, 14, 7, 123456, tzinfo=timezone.utc),
            datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
        ]
        for dt in samples:
            with self.subTest(dt=dt.isoformat()):
                self.assertEqual(datetime_to_winrt_ticks(dt), independent_ticks(dt))

    def test_naive_datetime_is_treated_as_utc(self):
        naive = datetime(2026, 11, 22, 13, 31, 12, 345678)
        aware = naive.replace(tzinfo=timezone.utc)
        self.assertEqual(datetime_to_winrt_ticks(naive), datetime_to_winrt_ticks(aware))

    def test_non_utc_offset_is_converted(self):
        plus_one = datetime(2026, 11, 22, 14, 31, 12, 345678, tzinfo=timezone(timedelta(hours=1)))
        utc = datetime(2026, 11, 22, 13, 31, 12, 345678, tzinfo=timezone.utc)
        self.assertEqual(datetime_to_winrt_ticks(plus_one), datetime_to_winrt_ticks(utc))

    def test_pre_epoch_datetime_gives_negative_ticks(self):
        dt = datetime(1600, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        self.assertEqual(datetime_to_winrt_ticks(dt), -TICKS_PER_SECOND)

    def test_round_trip_is_exact_at_microseconds(self):
        dt = datetime(2026, 11, 22, 13, 31, 12, 345678, tzinfo=timezone.utc)
        self.assertEqual(winrt_ticks_to_datetime(datetime_to_winrt_ticks(dt)), dt)


class TestTicksToDatetime(TestCase):
    def test_sub_microsecond_ticks_truncate_towards_negative_infinity(self):
        base = datetime_to_winrt_ticks(datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(
            winrt_ticks_to_datetime(base + 9), datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(
            winrt_ticks_to_datetime(base + 10),
            datetime(2026, 1, 1, 0, 0, 0, 1, tzinfo=timezone.utc),
        )

    def test_result_is_timezone_aware_utc(self):
        dt = winrt_ticks_to_datetime(0)
        self.assertEqual(dt, datetime(1601, 1, 1, tzinfo=timezone.utc))
        self.assertIsNotNone(dt.tzinfo)


class TestTimedeltaTicks(TestCase):
    def test_whole_and_fractional_spans(self):
        self.assertEqual(timedelta_to_winrt_ticks(timedelta(seconds=1)), TICKS_PER_SECOND)
        self.assertEqual(timedelta_to_winrt_ticks(timedelta(microseconds=1)), 10)
        self.assertEqual(
            timedelta_to_winrt_ticks(timedelta(hours=1, microseconds=345678)),
            3600 * TICKS_PER_SECOND + 3_456_780,
        )

    def test_negative_span(self):
        self.assertEqual(timedelta_to_winrt_ticks(timedelta(seconds=-1)), -TICKS_PER_SECOND)
        self.assertEqual(timedelta_to_winrt_ticks(timedelta(microseconds=-1)), -10)

    def test_span_round_trip_is_exact(self):
        for td in (
            timedelta(0),
            timedelta(microseconds=1),
            timedelta(seconds=-2, microseconds=500),
            timedelta(days=3650, hours=5, microseconds=123456),
        ):
            with self.subTest(td=td):
                self.assertEqual(winrt_ticks_to_timedelta(timedelta_to_winrt_ticks(td)), td)

    def test_sub_microsecond_ticks_truncate_towards_negative_infinity(self):
        self.assertEqual(winrt_ticks_to_timedelta(19), timedelta(microseconds=1))
        self.assertEqual(winrt_ticks_to_timedelta(-1), timedelta(microseconds=-1))
