Simple protocol
===============

Expedition can exchange data over TCP, UDP or serial using its *simple protocol*. The
``Expedition.protocol`` module builds and checks those messages. It does no I/O, so it runs
on macOS and Linux as well as Windows. The package does not open sockets yet, so you send the
bytes with your own socket code.

.. code-block:: python

   from Expedition import protocol

   packet = protocol.gun_set(12.34)  # b"#G,12.34*62\r\n"
   sock.sendall(packet)

   reply = sock.recv(256)            # e.g. b"#ACK,62*xx\r\n"
   if not protocol.is_ack(reply, packet):
       raise RuntimeError("Expedition did not acknowledge the command")

Sentences
---------

A sentence is ``#<body>*XX`` followed by CR LF. ``XX`` is the XOR of every character from the
``#`` up to, but not including, the ``*``, written as two uppercase hex digits:

.. code-block:: python

   protocol.checksum("#G,12.34")  # "62"
   protocol.frame("G,12.34")      # b"#G,12.34*62\r\n"
   protocol.parse_sentence(b"#G,12.34*62\r\n").fields  # ("G", "12.34")

``parse_sentence`` raises ``ExpeditionProtocolError`` if the framing or checksum is wrong. That
exception is a ``ValueError``. The builders raise ``ValueError`` for bad arguments, before
anything is sent.

Commands
--------

Each builder returns the complete framed sentence as bytes.

.. list-table::
   :header-rows: 1

   * - Area
     - Builders
   * - Gun
     - ``gun_sync``, ``gun_set``, ``gun_kill``
   * - Line
     - ``line_ping``, ``line_set``
   * - Marks
     - ``mark_set``, ``mark_mob_at``, ``mark_mob_here``, ``mark_ping``, ``mark_ping_active``,
       ``mark_prev``, ``mark_next``, ``mark_query``, ``mark_query_next``, ``mark_query_all``,
       ``mark_at``
   * - Routes
     - ``course_count``, ``course_name``, ``course_set_active``, ``course_create``,
       ``course_create_wl``
   * - Events
     - ``event_comment``, ``event_phase_start``, ``event_phase_stop``,
       ``event_phase_cancel``, ``event_phase_comment``, ``event_phase_sails_up``
   * - Sails
     - ``sail_set``
   * - System
     - ``system_heartbeat``, ``system_reconnect``, ``system_get_channel_name``,
       ``system_get_user_channel_names``, ``system_set_channel_name``,
       ``system_set_boat_name``, ``system_licence``

Replies
-------

``is_ack(reply, sent)`` returns True when ``reply`` is ``#ACK,XX`` and ``XX`` is the checksum of
``sent``. ``parse_licence(reply)`` returns the site code from ``#S,LICENCE,code``.
``parse_stream(line)`` splits a ``#<boat>,var,value,...`` data sentence into its pairs. It keeps
the var and value fields as text. Mapping var IDs to ``Var`` and decoding time values need a
capture from a running Expedition, so they are not done yet.

Name and text limits
--------------------

Limits follow the manual where it states one. Otherwise they use the field widths that the
Expedition binary reads.

- Channel names: at most 27 characters. Short names: at most 9.
- Boat names: at most 31 characters.
- Mark, route, sail and phase names: at most 31 characters.
- Event comments: at most 63 characters.

Names are ASCII. They may not contain commas, ``#``, ``*`` or line breaks, except that event
comments may contain commas.

Expedition setup
----------------

Expedition only sends and accepts what its connection's filters allow. Configure the connection
in Expedition before you rely on replies:

- **Output (Tx) filter:** choose the data to send. ``Legacy times`` selects the pre-12.8 time
  format. ``System`` sends held wind and current. Sail names are only sent when the sails are
  included in the filter.
- **Input (Rx) filter:** choose the data to receive. ``Marks`` receives marks. ``Legacy times``
  expects the pre-12.8 time format.

Items that are not yet verified
-------------------------------

These come from the manual, and are not yet checked against a running Expedition:

- The units of the range in ``mark_at``.
- The meaning of the optional fields in ``course_create_wl``. Skipped middle fields are sent
  empty.
- Whether external and system channel data (``E,`` and ``X,``) include the leading ``#``. The
  parser currently expects it.
- The reply formats for ``system_get_channel_name`` and ``system_get_user_channel_names``.
