import struct

from aigp.io.vision_rx import HEADER_FORMAT, ChunkAssembler, VisionRX


def make_packet(frame_id: int, chunk_id: int, total: int, full: bytes,
                payload: bytes, ts: int = 12345) -> bytes:
    header = struct.pack(HEADER_FORMAT, frame_id, chunk_id, total,
                         len(full), len(payload), ts)
    return header + payload


def split(frame_id: int, data: bytes, chunk_size: int, ts: int = 12345):
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    return [make_packet(frame_id, i, len(chunks), data, c, ts)
            for i, c in enumerate(chunks)]


def test_single_chunk_frame():
    asm = ChunkAssembler()
    data = b"jpegdata"
    result = asm.feed(make_packet(1, 0, 1, data, data))
    assert result == (1, 12345, data)


def test_multi_chunk_in_order():
    asm = ChunkAssembler()
    data = bytes(range(256)) * 20
    packets = split(7, data, 1000)
    assert len(packets) > 3
    for p in packets[:-1]:
        assert asm.feed(p) is None
    frame_id, ts, jpeg = asm.feed(packets[-1])
    assert frame_id == 7 and jpeg == data


def test_multi_chunk_reordered():
    asm = ChunkAssembler()
    data = b"x" * 5000
    packets = split(3, data, 1400)
    reordered = [packets[2], packets[0], packets[3], packets[1]]
    results = [asm.feed(p) for p in reordered]
    assert results[:-1] == [None, None, None]
    assert results[-1] == (3, 12345, data)


def test_interleaved_frames():
    asm = ChunkAssembler()
    d1, d2 = b"a" * 3000, b"b" * 3000
    p1, p2 = split(1, d1, 2000), split(2, d2, 2000)
    assert asm.feed(p1[0]) is None
    assert asm.feed(p2[0]) is None
    assert asm.feed(p2[1]) == (2, 12345, d2)
    assert asm.feed(p1[1]) == (1, 12345, d1)


def test_lost_chunk_gc():
    asm = ChunkAssembler(stale_after_s=1.0)
    data = b"z" * 5000
    packets = split(9, data, 1400)
    asm.feed(packets[0], now=0.0)
    asm.feed(packets[1], now=0.1)
    assert asm.pending == 1
    # A later frame arrives long after; the stale partial is collected.
    asm.feed(make_packet(10, 0, 1, b"ok", b"ok"), now=5.0)
    assert asm.pending == 0


def test_runt_packet_ignored():
    asm = ChunkAssembler()
    assert asm.feed(b"short") is None
    assert asm.pending == 0


def test_rebroadcast_dedupe():
    """The real sim re-sends each exposure ~8-9x (measured ~280 msg/s vs
    ~30 unique/s). Duplicates must be dropped BEFORE decode so the
    estimator sees each exposure once and a frozen stream stops feeding
    the frame watchdog."""
    rx = VisionRX.__new__(VisionRX)          # logic only, no socket/bus
    rx._last_frame_id = None
    assert rx._is_new_exposure(1500)
    assert not rx._is_new_exposure(1500)     # rebroadcast
    assert rx._is_new_exposure(1501)
    assert not rx._is_new_exposure(1500)     # late rebroadcast of older id
    assert not rx._is_new_exposure(1501)
    assert rx._is_new_exposure(1502)
    # Large backward jump = the sim restarted numbering (new race): accept.
    assert rx._is_new_exposure(3)
    assert rx._is_new_exposure(4)
