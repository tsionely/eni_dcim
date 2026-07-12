from aigp.io.udp_tap import (
    STREAM_MAVLINK,
    STREAM_VISION,
    DatagramRecorder,
    read_recording,
)


def test_record_read_roundtrip(tmp_path):
    path = tmp_path / "rec.aigprec"
    rec = DatagramRecorder(path)
    rec.write(STREAM_MAVLINK, b"mav-1", mono_ns=100)
    rec.write(STREAM_VISION, b"vis-1", mono_ns=200)
    rec.write(STREAM_VISION, b"", mono_ns=300)   # empty datagram survives
    rec.close()

    records = list(read_recording(path))
    assert records == [
        (100, STREAM_MAVLINK, b"mav-1"),
        (200, STREAM_VISION, b"vis-1"),
        (300, STREAM_VISION, b""),
    ]


def test_sink_binding(tmp_path):
    rec = DatagramRecorder(tmp_path / "r.aigprec")
    sink = rec.sink_for(STREAM_VISION)
    sink(b"abc")
    rec.close()
    [(_, stream_id, data)] = list(read_recording(tmp_path / "r.aigprec"))
    assert stream_id == STREAM_VISION and data == b"abc"


def test_truncated_file_stops_cleanly(tmp_path):
    path = tmp_path / "rec.aigprec"
    rec = DatagramRecorder(path)
    rec.write(STREAM_MAVLINK, b"full-record", mono_ns=1)
    rec.close()
    data = path.read_bytes()
    path.write_bytes(data[:-4])   # cut mid-payload
    assert list(read_recording(path)) == []
