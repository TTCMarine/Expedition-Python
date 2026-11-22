"""Expedition simple protocol: framing, checksums, typed commands and replies.

This module does no I/O, so it runs on any platform. Sockets belong in a separate transport.

A sentence is ``#<body>*XX`` followed by CR LF. ``XX`` is the XOR of every character from the
``#`` up to, but not including, the ``*``, written as two uppercase hex digits. Expedition
acknowledges a command with ``#ACK,XX``, where ``XX`` is the checksum of the command.

Builders return complete framed sentences as bytes. They raise ``ValueError`` for bad
arguments, as the DLL wrapper does. ``parse_sentence`` and the other parsers raise
``ExpeditionProtocolError``, which is also a ``ValueError``.

Length limits follow the manual where it states one. Otherwise they use the field width that
the Expedition binary reads for the same kind of field: 31 for names and 63 for comments.
"""

import math
import numbers
import operator
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from .errors import ExpeditionProtocolError

__all__ = [
    "BOAT_NAME_MAX",
    "CHANNEL_NAME_MAX",
    "CHANNEL_SHORT_NAME_MAX",
    "COMMENT_MAX",
    "LINE_END",
    "NAME_MAX",
    "Sentence",
    "StreamSentence",
    "checksum",
    "course_count",
    "course_create",
    "course_create_wl",
    "course_name",
    "course_set_active",
    "event_comment",
    "event_phase_cancel",
    "event_phase_comment",
    "event_phase_sails_up",
    "event_phase_start",
    "event_phase_stop",
    "frame",
    "gun_kill",
    "gun_set",
    "gun_sync",
    "is_ack",
    "line_ping",
    "line_set",
    "mark_at",
    "mark_mob_at",
    "mark_mob_here",
    "mark_next",
    "mark_ping",
    "mark_ping_active",
    "mark_prev",
    "mark_query",
    "mark_query_all",
    "mark_query_next",
    "mark_set",
    "parse_licence",
    "parse_sentence",
    "parse_stream",
    "sail_set",
    "system_get_channel_name",
    "system_get_user_channel_names",
    "system_heartbeat",
    "system_licence",
    "system_reconnect",
    "system_set_boat_name",
    "system_set_channel_name",
]

LINE_END = b"\r\n"

# Limits. The manual states the first three; the others come from the binary's field widths.
NAME_MAX = 31
CHANNEL_NAME_MAX = 27  # manual: "less than 28 characters"
CHANNEL_SHORT_NAME_MAX = 9  # manual: "short name less than 10"
BOAT_NAME_MAX = 31  # manual: "less than 32 characters"
COMMENT_MAX = 63

_UINT16_MAX = 65535
_MARK_FLAGS = ("X", "P", "S", "M")
_LINE_ENDS = ("P", "S")
_SAIL_TARGETS = ("A", "M", "N", "E")
_LEEWARD_MODES = ("L", "C", "G")
_MARK_SIDES = ("P", "S")
_CHECKSUM_RE = re.compile(r"[0-9A-Fa-f]{2}")
_HEX_RE = re.compile(r"[0-9A-Fa-f]+")


@dataclass(frozen=True)
class Sentence:
    """A parsed sentence. ``body`` is the text between ``#`` and ``*``."""

    body: str
    checksum: str  # two uppercase hex digits

    @property
    def fields(self) -> Tuple[str, ...]:
        """The comma-separated fields of ``body``."""
        return tuple(self.body.split(","))

    @property
    def name(self) -> str:
        """The first field, for example ``"G"``, ``"M"``, ``"ACK"`` or a boat id."""
        return self.fields[0]


@dataclass(frozen=True)
class StreamSentence:
    """A ``#<boat>,var,value,...`` data sentence.

    The var and value fields are kept as text. Mapping var IDs to ``Var`` members and
    decoding time values depend on a capture from a running Expedition, so they are not
    done here yet.
    """

    boat: int
    pairs: Tuple[Tuple[str, str], ...]


def checksum(text: str) -> str:
    """Return the checksum of ``text``, which runs from the ``#`` up to the ``*``.

    Example: ``checksum("#G,12.34") == "62"``.
    """
    data = _ascii_bytes(text, "checksum text")
    value = 0
    for byte in data:
        value ^= byte
    return f"{value:02X}"


def frame(body: str) -> bytes:
    """Frame ``body`` (the text after ``#``) as a complete sentence.

    Example: ``frame("G,12.34") == b"#G,12.34*62\\r\\n"``.
    """
    if not isinstance(body, str) or not body:
        raise ValueError("body must be a non-empty string")
    _check_ascii(body, "body")
    if any(ch in body for ch in "#*\r\n"):
        raise ValueError("body must not contain '#', '*' or line breaks")
    text = "#" + body
    return f"{text}*{checksum(text)}".encode("ascii") + LINE_END


def parse_sentence(line: bytes) -> Sentence:
    """Parse one complete sentence, checking framing and checksum.

    Lowercase hex in the checksum is accepted. Expedition sends uppercase.
    """
    try:
        text = bytes(line).decode("ascii")
    except (TypeError, UnicodeDecodeError) as exc:
        raise ExpeditionProtocolError("a sentence must be ASCII bytes") from exc
    if not text.endswith("\r\n"):
        raise ExpeditionProtocolError("a sentence must end with CR LF")
    text = text[:-2]
    if not text.startswith("#"):
        raise ExpeditionProtocolError("a sentence must start with '#'")
    star = text.rfind("*")
    if star < 0:
        raise ExpeditionProtocolError("a sentence must end with '*XX'")
    received = text[star + 1 :]
    if not _CHECKSUM_RE.fullmatch(received):
        raise ExpeditionProtocolError(f"checksum must be two hex digits, got {received!r}")
    content = text[1:star]
    if not content or any(ch in content for ch in "#*\r\n"):
        raise ExpeditionProtocolError("sentence body is empty or contains framing characters")
    expected = checksum(text[:star])
    if expected != received.upper():
        raise ExpeditionProtocolError(
            f"checksum mismatch: sentence has {received.upper()}, expected {expected}"
        )
    return Sentence(body=content, checksum=expected)


def is_ack(reply: bytes, sent: bytes) -> bool:
    """Return True if ``reply`` is ``#ACK,XX`` where ``XX`` is the checksum of ``sent``.

    Raises ExpeditionProtocolError if either argument is not a valid sentence.
    """
    command = parse_sentence(sent)
    response = parse_sentence(reply)
    fields = response.fields
    return len(fields) == 2 and fields[0] == "ACK" and fields[1].upper() == command.checksum


def parse_licence(line: bytes) -> str:
    """Return the site code from a ``#S,LICENCE,code`` reply, as the hex text received."""
    sentence = parse_sentence(line)
    fields = sentence.fields
    if len(fields) != 3 or fields[:2] != ("S", "LICENCE") or not _HEX_RE.fullmatch(fields[2]):
        raise ExpeditionProtocolError(f"not a licence reply: {sentence.body!r}")
    return fields[2]


def parse_stream(line: bytes) -> StreamSentence:
    """Parse a ``#<boat>,var,value,...`` data sentence into its var and value pairs."""
    sentence = parse_sentence(line)
    fields = sentence.fields
    if not fields[0].isdigit():
        raise ExpeditionProtocolError(f"not a data sentence: {sentence.body!r}")
    rest = fields[1:]
    if not rest or len(rest) % 2:
        raise ExpeditionProtocolError("a data sentence needs var,value pairs")
    if any(not field for field in rest):
        raise ExpeditionProtocolError("a data sentence has an empty var or value")
    return StreamSentence(boat=int(fields[0]), pairs=tuple(zip(rest[0::2], rest[1::2])))


# Gun


def gun_sync() -> bytes:
    """Synchronise the start countdown timer."""
    return frame("G,SYNC")


def gun_set(minutes: float) -> bytes:
    """Set the start countdown to ``minutes``. The manual's example uses a negative value."""
    return frame(f"G,{_fmt(_real(minutes, 'minutes'))}")


def gun_kill() -> bytes:
    """Kill the start countdown timer."""
    return frame("G,KILL")


# Line


def line_ping(end: str) -> bytes:
    """Ping the ``"P"`` (port) or ``"S"`` (starboard) end of the line."""
    return frame(f"L,{_choice(end, 'end', _LINE_ENDS)}")


def line_set(end: str, lat: float, lon: float) -> bytes:
    """Set the ``"P"`` or ``"S"`` end of the line to a position."""
    end = _choice(end, "end", _LINE_ENDS)
    return frame(f"L,{end},{_latitude(lat)},{_longitude(lon)}")


# Marks


def mark_set(mark_id, name: str, lat: float, lon: float, flag: str) -> bytes:
    """Create or update a mark.

    ``mark_id`` is a non-negative mark number, or ``"ACTIVE"`` for the active mark. An
    existing numbered mark is updated; any other id creates a new mark. ``flag`` is ``"X"``
    (MOB), ``"P"`` (leave to port), ``"S"`` (leave to starboard) or ``"M"`` (sail direct).
    """
    if isinstance(mark_id, str):
        ident = _choice(mark_id, "mark_id", ("ACTIVE",))
    else:
        ident = str(_index(mark_id, "mark_id"))
    name = _text(name, "name", NAME_MAX)
    flag = _choice(flag, "flag", _MARK_FLAGS)
    return frame(f"M,{ident},{name},{_latitude(lat)},{_longitude(lon)},{flag}")


def mark_mob_at(lat: float, lon: float) -> bytes:
    """Set a MOB mark at a position. Expedition reports the active mark afterwards."""
    return frame(f"M,MOB,MOB,{_latitude(lat)},{_longitude(lon)},X")


def mark_mob_here() -> bytes:
    """Set Expedition's MOB at the current position. Expedition replies with the active mark."""
    return frame("M,MOB")


def mark_ping() -> bytes:
    """Ping a mark at the current location (bow or GPS)."""
    return frame("M,PING")


def mark_ping_active() -> bytes:
    """Set the active mark to the current position."""
    return frame("M,PINGACTIVE")


def mark_prev() -> bytes:
    """Make the previous mark in the active route active. Expedition replies with it."""
    return frame("M,PREV")


def mark_next() -> bytes:
    """Make the next mark in the active route active. Expedition replies with it."""
    return frame("M,NEXT")


def mark_query() -> bytes:
    """Query the active mark. Expedition replies with its details."""
    return frame("M,QUERY")


def mark_query_next() -> bytes:
    """Query the next mark."""
    return frame("M,QUERYNEXT")


def mark_query_all() -> bytes:
    """Query all marks of the active route."""
    return frame("M,QUERYALL")


def mark_at(target: str, range_value: float, bearing: float) -> bytes:
    """Place a mark at a range and bearing.

    ``target`` is ``"N"`` to create a new active mark and route, or ``"A"`` to add a mark
    after the active mark. The manual does not state the units of ``range_value``.
    """
    target = _choice(target, "target", ("N", "A"))
    rng = _real(range_value, "range_value", low=0)
    brg = _real(bearing, "bearing", low=0, high=360)
    return frame(f"M,AT,{target},{_fmt(rng)},{_fmt(brg)}")


# Routes (courses)


def course_count() -> bytes:
    """Ask for the number of routes. Expedition replies with ``#C,COURSENUM,n``."""
    return frame("C,GETCOURSENUM")


def course_name(index: int) -> bytes:
    """Ask for the name of route ``index``. Expedition replies with ``#C,COURSENAME,n,s``."""
    return frame(f"C,GETCOURSENAME,{_index(index, 'index')}")


def course_set_active(index: int) -> bytes:
    """Make route ``index`` the active route."""
    return frame(f"C,SETCOURSE,{_index(index, 'index')}")


def course_create(name: str) -> bytes:
    """Create an empty route called ``name`` and make it active."""
    return frame(f"C,CREATECOURSE,{_text(name, 'name', NAME_MAX)}")


def course_create_wl(
    axis: float,
    start_to_wm: float,
    start_to_lm: float,
    gate_width: float,
    finish_width: Optional[float] = None,
    wi: Optional[float] = None,
    laps: Optional[int] = None,
    leeward: Optional[str] = None,
    marks_side: Optional[str] = None,
) -> bytes:
    """Create a windward/leeward course from the start line.

    ``axis`` is in degrees magnetic. ``leeward`` is ``"L"`` (leeward mark above the boat, or
    gate centred on the line), ``"C"`` (leeward mark above the committee boat) or ``"G"``
    (gate centred above the line). ``marks_side`` is ``"P"`` or ``"S"``; Expedition uses
    port if it is omitted.

    The manual lists ``finish_width``, ``wi``, ``laps``, ``leeward`` and ``marks_side`` as
    optional. Positional fields cannot be skipped, so an omitted field in the middle is sent
    empty, and trailing omitted fields are dropped. Empty fields are not checked against a
    capture yet.
    """
    required = [
        _fmt(_real(axis, "axis", low=0, high=360)),
        _fmt(_real(start_to_wm, "start_to_wm", low=0)),
        _fmt(_real(start_to_lm, "start_to_lm", low=0)),
        _fmt(_real(gate_width, "gate_width", low=0)),
    ]
    optional: list = [
        None if finish_width is None else _fmt(_real(finish_width, "finish_width", low=0)),
        None if wi is None else _fmt(_real(wi, "wi", low=0)),
        None if laps is None else str(_index(laps, "laps")),
        None if leeward is None else _choice(leeward, "leeward", _LEEWARD_MODES),
        None if marks_side is None else _choice(marks_side, "marks_side", _MARK_SIDES),
    ]
    while optional and optional[-1] is None:
        optional.pop()
    fields = required + ["" if value is None else value for value in optional]
    return frame("C,WL," + ",".join(fields))


# Events


def event_comment(comment: str = "") -> bytes:
    """Create an event with a comment. An empty comment creates an event with no text."""
    if comment:
        comment = _text(comment, "comment", COMMENT_MAX, allow_commas=True)
    return frame(f"E,{comment}")


def event_phase_start(name: str) -> bytes:
    """Start a Sailing Performance style phase."""
    return frame(f"E,PHASESTART,{_text(name, 'name', NAME_MAX)}")


def event_phase_stop(name: str) -> bytes:
    """Stop a phase."""
    return frame(f"E,PHASESTOP,{_text(name, 'name', NAME_MAX)}")


def event_phase_cancel(name: str) -> bytes:
    """Cancel a phase."""
    return frame(f"E,PHASECANCEL,{_text(name, 'name', NAME_MAX)}")


def event_phase_comment(name: str, comment: str) -> bytes:
    """Add a comment to a phase. The comment may not contain commas, since they separate fields."""
    name = _text(name, "name", NAME_MAX)
    comment = _text(comment, "comment", COMMENT_MAX)
    return frame(f"E,PHASECOMMENT,{name},{comment}")


def event_phase_sails_up(
    mainsail: str,
    num_reefs: int,
    headsail: str,
    staysail: str,
    spinnaker: str,
    comments: str = "",
) -> bytes:
    """Record the sails set for a phase. Sail names may be empty; commas are not allowed."""
    fields = [
        _text(mainsail, "mainsail", NAME_MAX, allow_empty=True),
        str(_index(num_reefs, "num_reefs")),
        _text(headsail, "headsail", NAME_MAX, allow_empty=True),
        _text(staysail, "staysail", NAME_MAX, allow_empty=True),
        _text(spinnaker, "spinnaker", NAME_MAX, allow_empty=True),
        _text(comments, "comments", COMMENT_MAX, allow_empty=True),
    ]
    return frame("E,PHASESAILSUP," + ",".join(fields))


# Sails


def sail_set(target: str, name: str) -> bytes:
    """Set a sail name. ``target`` is ``"A"`` (current), ``"M"`` (to mark), ``"N"`` (next
    leg) or ``"E"`` (set by events). The sail name is only sent when the Tx filter includes
    sails. The manual gives no length limit for sail names, so ``NAME_MAX`` is used.
    """
    target = _choice(target, "target", _SAIL_TARGETS)
    return frame(f"S,{target},{_text(name, 'name', NAME_MAX)}")


# System


def system_heartbeat() -> bytes:
    """Send a heartbeat."""
    return frame("S,HEARTBEAT")


def system_reconnect() -> bytes:
    """Tell the receiving computer to reconnect all network connections."""
    return frame("S,RECONNECT")


def system_get_channel_name(channel: int) -> bytes:
    """Ask for a channel's name. Expedition replies with ``#S,CHANNELNAME,channel,name,short``."""
    return frame(f"S,GETCHANNELNAME,{_index(channel, 'channel', _UINT16_MAX)}")


def system_get_user_channel_names() -> bytes:
    """Ask for the names of the user channels."""
    return frame("S,GETUSERCHANNELNAMES")


def system_set_channel_name(channel: int, name: str, short_name: str) -> bytes:
    """Rename a channel. The manual's example renames User0, which is channel 172.

    Names must be shorter than the manual's limits: ``name`` at most 27 characters and
    ``short_name`` at most 9.
    """
    channel = _index(channel, "channel", _UINT16_MAX)
    name = _text(name, "name", CHANNEL_NAME_MAX, allow_commas=False)
    short_name = _text(short_name, "short_name", CHANNEL_SHORT_NAME_MAX)
    return frame(f"S,SETCHANNELNAME,{channel},{name},{short_name}")


def system_set_boat_name(boat: int, name: str) -> bytes:
    """Rename boat ``boat`` (0 to n). The name must be shorter than 32 characters."""
    return frame(
        f"S,SETBOATNAME,{_index(boat, 'boat', _UINT16_MAX)},"
        f"{_text(name, 'name', BOAT_NAME_MAX)}"
    )


def system_licence() -> bytes:
    """Ask for Expedition's site code. Expedition replies with ``#S,LICENCE,code``."""
    return frame("S,LICENCE")


# Validation helpers


def _ascii_bytes(text: str, label: str) -> bytes:
    if not isinstance(text, str):
        raise ValueError(f"{label} must be a string")
    _check_ascii(text, label)
    return text.encode("ascii")


def _check_ascii(text: str, label: str) -> None:
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError(f"{label} must be ASCII") from None


def _text(
    value,
    label: str,
    max_len: int,
    *,
    allow_empty: bool = False,
    allow_commas: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if not value and not allow_empty:
        raise ValueError(f"{label} must not be empty")
    _check_ascii(value, label)
    forbidden = "#*\r\n" if allow_commas else ",#*\r\n"
    if any(ch in value for ch in forbidden):
        listed = "'#', '*' or line breaks" if allow_commas else "',', '#', '*' or line breaks"
        raise ValueError(f"{label} must not contain {listed}")
    if len(value) > max_len:
        raise ValueError(f"{label} must be {max_len} characters or fewer, got {len(value)}")
    return value


def _choice(value, label: str, options: Tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in options:
        raise ValueError(f"{label} must be one of {', '.join(options)}, got {value!r}")
    return value


def _index(value, label: str, maximum: Optional[int] = None) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer, not bool")
    try:
        number = operator.index(value)
    except TypeError:
        raise ValueError(f"{label} must be an integer, got {value!r}") from None
    if number < 0 or (maximum is not None and number > maximum):
        upper = "" if maximum is None else f" and {maximum}"
        raise ValueError(f"{label} must be between 0{upper}, got {number}")
    return number


def _real(value, label: str, low: Optional[float] = None, high: Optional[float] = None) -> float:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"{label} must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite, got {number}")
    if (low is not None and number < low) or (high is not None and number > high):
        raise ValueError(f"{label} is out of range, got {number}")
    return number


def _latitude(value) -> str:
    return _fmt(_real(value, "lat", low=-90, high=90))


def _longitude(value) -> str:
    return _fmt(_real(value, "lon", low=-180, high=180))


def _fmt(value: float) -> str:
    """Format a number without exponent notation, trimmed, keeping one decimal place.

    Examples: ``12.34 -> "12.34"``, ``-1.0 -> "-1.0"``, ``45 -> "45.0"``.
    """
    text = f"{value:.6f}".rstrip("0")
    return text + "0" if text.endswith(".") else text
