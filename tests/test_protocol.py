"""Tests for Expedition.protocol. These need no DLL and run on any platform."""

import pytest

from Expedition import protocol as p
from Expedition.errors import ExpeditionProtocolError


def _ack(command: bytes) -> bytes:
    """Build the ACK Expedition sends for ``command``."""
    cs = p.parse_sentence(command).checksum
    return p.frame(f"ACK,{cs}")


# Checksum and framing, using the worked examples in the manual.


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#G,12.34", "62"),
        ("#G,-1.0", "4A"),
    ],
)
def test_checksum_matches_manual_examples(text, expected):
    assert p.checksum(text) == expected


def test_frame_matches_manual_examples():
    assert p.frame("G,12.34") == b"#G,12.34*62\r\n"
    assert p.frame("G,-1.0") == b"#G,-1.0*4A\r\n"


def test_checksum_includes_leading_hash():
    # The '#' is part of the XOR, so dropping it changes the checksum.
    assert p.checksum("G,12.34") != p.checksum("#G,12.34")


@pytest.mark.parametrize("body", ["G,SYNC", "M,3,Anchorage,-33.5,151.2,P", "E,", "S,LICENCE"])
def test_parse_round_trips_framed_body(body):
    sentence = p.parse_sentence(p.frame(body))
    assert sentence.body == body
    assert sentence.checksum == p.checksum("#" + body)


def test_parse_accepts_lowercase_checksum():
    sentence = p.parse_sentence(b"#G,-1.0*4a\r\n")
    assert sentence.checksum == "4A"


def test_sentence_fields_and_name():
    sentence = p.parse_sentence(p.frame("M,3,Anchorage,-33.5,151.2,P"))
    assert sentence.name == "M"
    assert sentence.fields == ("M", "3", "Anchorage", "-33.5", "151.2", "P")


@pytest.mark.parametrize(
    ("line", "message"),
    [
        (b"#G,12.34*62", "CR LF"),  # missing line end
        (b"#G,12.34*62\n", "CR LF"),  # LF only
        (b"G,12.34*62\r\n", "start with '#'"),
        (b"#G,12.34\r\n", "end with"),
        (b"#G,12.34*6\r\n", "two hex digits"),
        (b"#G,12.34*620\r\n", "two hex digits"),
        (b"#G,12.34*ZZ\r\n", "two hex digits"),
        (b"#G,12.34*00\r\n", "checksum mismatch"),
        (b"#A*B*XX\r\n", "two hex digits"),
        (b"#*00\r\n", "empty"),
        ("#G,12.34*62\r\n".encode("utf-8").replace(b"G", "\u00e9".encode("utf-8")), "ASCII"),
    ],
)
def test_parse_rejects_malformed_sentences(line, message):
    with pytest.raises(ExpeditionProtocolError, match=message):
        p.parse_sentence(line)


def test_protocol_error_is_a_value_error():
    with pytest.raises(ValueError):
        p.parse_sentence(b"not a sentence")


def test_parse_rejects_str_input():
    with pytest.raises(ExpeditionProtocolError):
        p.parse_sentence("#G,12.34*62\r\n")


def test_frame_rejects_framing_characters_in_body():
    for body in ["G,1*2", "G,#1", "G,1\r\n", ""]:
        with pytest.raises(ValueError):
            p.frame(body)


# Gun and line


def test_gun_commands():
    assert p.gun_sync() == p.frame("G,SYNC")
    assert p.gun_kill() == p.frame("G,KILL")
    assert p.gun_set(12.34) == b"#G,12.34*62\r\n"
    assert p.gun_set(-1.0) == b"#G,-1.0*4A\r\n"


def test_gun_set_rejects_non_finite():
    with pytest.raises(ValueError):
        p.gun_set(float("nan"))
    with pytest.raises(ValueError):
        p.gun_set(True)


def test_line_commands():
    assert p.line_ping("P") == p.frame("L,P")
    assert p.line_ping("S") == p.frame("L,S")
    assert p.line_set("S", -33.5, 151.2) == p.frame("L,S,-33.5,151.2")


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: p.line_ping("X"), "end"),
        (lambda: p.line_set("P", 91, 0), "lat"),
        (lambda: p.line_set("P", 0, 181), "lon"),
    ],
)
def test_line_rejects_bad_arguments(call, message):
    with pytest.raises(ValueError, match=message):
        call()


# Marks


def test_mark_set_numbered_and_active():
    assert p.mark_set(3, "Anchorage", -33.5, 151.2, "P") == p.frame("M,3,Anchorage,-33.5,151.2,P")
    assert p.mark_set("ACTIVE", "Gate", 50.8, -1.4, "M") == p.frame("M,ACTIVE,Gate,50.8,-1.4,M")


@pytest.mark.parametrize("flag", ["X", "P", "S", "M"])
def test_mark_set_accepts_each_flag(flag):
    assert p.mark_set(0, "A", 0, 0, flag) == p.frame(f"M,0,A,0.0,0.0,{flag}")


def test_mark_name_limit_is_31_characters():
    assert p.mark_set(1, "x" * 31, 0, 0, "P")
    with pytest.raises(ValueError, match="31"):
        p.mark_set(1, "x" * 32, 0, 0, "P")


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: p.mark_set(-1, "A", 0, 0, "P"), "mark_id"),
        (lambda: p.mark_set("MOB", "A", 0, 0, "P"), "mark_id"),
        (lambda: p.mark_set(True, "A", 0, 0, "P"), "mark_id"),
        (lambda: p.mark_set(1, "", 0, 0, "P"), "name"),
        (lambda: p.mark_set(1, "a,b", 0, 0, "P"), "','"),
        (lambda: p.mark_set(1, "a\nb", 0, 0, "P"), "line breaks"),
        (lambda: p.mark_set(1, "caf\u00e9", 0, 0, "P"), "ASCII"),
        (lambda: p.mark_set(1, "A", 0, 0, "Q"), "flag"),
        (lambda: p.mark_set(1, "A", 0, 0, "p"), "flag"),
    ],
)
def test_mark_set_rejects_bad_arguments(call, message):
    with pytest.raises(ValueError, match=message):
        call()


def test_mob_and_query_commands():
    assert p.mark_mob_at(-33.5, 151.2) == p.frame("M,MOB,MOB,-33.5,151.2,X")
    assert p.mark_mob_here() == p.frame("M,MOB")
    assert p.mark_ping() == p.frame("M,PING")
    assert p.mark_ping_active() == p.frame("M,PINGACTIVE")
    assert p.mark_prev() == p.frame("M,PREV")
    assert p.mark_next() == p.frame("M,NEXT")
    assert p.mark_query() == p.frame("M,QUERY")
    assert p.mark_query_next() == p.frame("M,QUERYNEXT")
    assert p.mark_query_all() == p.frame("M,QUERYALL")


def test_mark_at_range_and_bearing():
    assert p.mark_at("N", 0.5, 90) == p.frame("M,AT,N,0.5,90.0")
    assert p.mark_at("A", 2, 360) == p.frame("M,AT,A,2.0,360.0")
    with pytest.raises(ValueError, match="bearing"):
        p.mark_at("N", 1, 361)
    with pytest.raises(ValueError, match="range_value"):
        p.mark_at("N", -1, 10)
    with pytest.raises(ValueError, match="target"):
        p.mark_at("X", 1, 10)


# Routes


def test_course_commands():
    assert p.course_count() == p.frame("C,GETCOURSENUM")
    assert p.course_name(2) == p.frame("C,GETCOURSENAME,2")
    assert p.course_set_active(1) == p.frame("C,SETCOURSE,1")
    assert p.course_create("Race 1") == p.frame("C,CREATECOURSE,Race 1")


def test_course_create_wl_all_fields():
    assert p.course_create_wl(90, 0.5, 0.5, 0.1, 0.2, 0.3, 3, "G", "S") == p.frame(
        "C,WL,90.0,0.5,0.5,0.1,0.2,0.3,3,G,S"
    )


def test_course_create_wl_trims_trailing_optional_fields():
    assert p.course_create_wl(90, 0.5, 0.5, 0.1) == p.frame("C,WL,90.0,0.5,0.5,0.1")
    assert p.course_create_wl(90, 0.5, 0.5, 0.1, laps=3) == p.frame("C,WL,90.0,0.5,0.5,0.1,,,3")


def test_course_create_wl_sends_empty_for_skipped_middle_fields():
    assert p.course_create_wl(90, 0.5, 0.5, 0.1, leeward="G") == p.frame(
        "C,WL,90.0,0.5,0.5,0.1,,,,G"
    )


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: p.course_create_wl(361, 0.5, 0.5, 0.1), "axis"),
        (lambda: p.course_create_wl(90, -1, 0.5, 0.1), "start_to_wm"),
        (lambda: p.course_create_wl(90, 0.5, 0.5, 0.1, leeward="X"), "leeward"),
        (lambda: p.course_create_wl(90, 0.5, 0.5, 0.1, marks_side="B"), "marks_side"),
        (lambda: p.course_create_wl(90, 0.5, 0.5, 0.1, laps=-1), "laps"),
        (lambda: p.course_create("x" * 32), "name"),
        (lambda: p.course_name(-1), "index"),
    ],
)
def test_course_rejects_bad_arguments(call, message):
    with pytest.raises(ValueError, match=message):
        call()


# Events


def test_event_commands():
    assert p.event_comment() == p.frame("E,")
    assert p.event_comment("Rounded mark") == p.frame("E,Rounded mark")
    assert p.event_comment("a, b") == p.frame("E,a, b")
    assert p.event_phase_start("Leg 1") == p.frame("E,PHASESTART,Leg 1")
    assert p.event_phase_stop("Leg 1") == p.frame("E,PHASESTOP,Leg 1")
    assert p.event_phase_cancel("Leg 1") == p.frame("E,PHASECANCEL,Leg 1")
    assert p.event_phase_comment("Leg 1", "Wind shift") == p.frame(
        "E,PHASECOMMENT,Leg 1,Wind shift"
    )


def test_event_phase_sails_up_allows_empty_sail_names():
    assert p.event_phase_sails_up("Main", 1, "J1", "", "S1", "ok") == p.frame(
        "E,PHASESAILSUP,Main,1,J1,,S1,ok"
    )


def test_event_comment_limit_is_63_characters():
    assert p.event_comment("c" * 63)
    with pytest.raises(ValueError, match="63"):
        p.event_comment("c" * 64)


def test_event_phase_comment_rejects_commas_in_comment():
    with pytest.raises(ValueError, match="','"):
        p.event_phase_comment("Leg 1", "a, b")


# Sails


def test_sail_set_targets():
    assert p.sail_set("A", "Genoa") == p.frame("S,A,Genoa")
    assert p.sail_set("E", "Spinnaker") == p.frame("S,E,Spinnaker")
    with pytest.raises(ValueError, match="target"):
        p.sail_set("Z", "Genoa")


# System


def test_system_commands():
    assert p.system_heartbeat() == p.frame("S,HEARTBEAT")
    assert p.system_reconnect() == p.frame("S,RECONNECT")
    assert p.system_get_channel_name(172) == p.frame("S,GETCHANNELNAME,172")
    assert p.system_get_user_channel_names() == p.frame("S,GETUSERCHANNELNAMES")
    assert p.system_licence() == p.frame("S,LICENCE")


def test_set_channel_name_matches_manual_example():
    assert p.system_set_channel_name(172, "My new name", "MyName") == p.frame(
        "S,SETCHANNELNAME,172,My new name,MyName"
    )


def test_channel_name_limits_follow_manual():
    # Manual: name less than 28 characters, short name less than 10.
    assert p.system_set_channel_name(172, "n" * 27, "s" * 9)
    with pytest.raises(ValueError, match="27"):
        p.system_set_channel_name(172, "n" * 28, "short")
    with pytest.raises(ValueError, match="9"):
        p.system_set_channel_name(172, "name", "s" * 10)


def test_channel_name_rejects_commas_and_bad_channel():
    with pytest.raises(ValueError, match="','"):
        p.system_set_channel_name(172, "a,b", "ab")
    with pytest.raises(ValueError, match="channel"):
        p.system_set_channel_name(65536, "a", "b")


def test_boat_name_limit_is_31_characters():
    assert p.system_set_boat_name(0, "b" * 31) == p.frame("S,SETBOATNAME,0," + "b" * 31)
    with pytest.raises(ValueError, match="31"):
        p.system_set_boat_name(0, "b" * 32)


# Replies


def test_is_ack_matches_the_command_checksum():
    command = p.course_set_active(1)
    assert p.is_ack(_ack(command), command) is True


def test_is_ack_rejects_other_commands_and_non_acks():
    command = p.course_set_active(1)
    other = p.gun_sync()
    assert p.is_ack(_ack(other), command) is False
    assert p.is_ack(p.frame("S,HEARTBEAT"), command) is False


def test_is_ack_accepts_lowercase_payload():
    command = p.course_set_active(1)
    cs = p.parse_sentence(command).checksum
    assert any(ch.isalpha() for ch in cs), "pick a command whose checksum has a letter"
    reply = p.frame(f"ACK,{cs.lower()}")
    assert p.is_ack(reply, command) is True


def test_is_ack_rejects_malformed_reply():
    with pytest.raises(ExpeditionProtocolError):
        p.is_ack(b"#ACK,62*00\r\n", p.gun_sync())


def test_parse_licence_returns_site_code():
    reply = p.frame("S,LICENCE,9ac6c16a")
    assert p.parse_licence(reply) == "9ac6c16a"


def test_parse_licence_rejects_other_replies():
    with pytest.raises(ExpeditionProtocolError):
        p.parse_licence(p.frame("S,HEARTBEAT"))
    with pytest.raises(ExpeditionProtocolError):
        p.parse_licence(p.frame("S,LICENCE,xyz"))


# Stream data (structure only: var and value meaning waits for a capture)


def test_parse_stream_pairs():
    stream = p.parse_stream(p.frame("3,12,1.5,13,2.0"))
    assert stream.boat == 3
    assert stream.pairs == (("12", "1.5"), ("13", "2.0"))


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("E,PHASESTART,Leg 1", "data sentence"),
        ("3,12", "pairs"),
        ("3", "pairs"),
        ("3,12,1.5,13", "pairs"),
        ("3,,1.5", "empty"),
    ],
)
def test_parse_stream_rejects_non_data_sentences(body, message):
    with pytest.raises(ExpeditionProtocolError, match=message):
        p.parse_stream(p.frame(body))
