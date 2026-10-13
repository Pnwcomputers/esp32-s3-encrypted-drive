from desktop.protocol import Frame, encode_frame, decode_frame

def test_round_trip():
    original = Frame(command=0x10, request_id=123, payload=b"hello")
    assert decode_frame(encode_frame(original)) == original

def test_reject_crc_corruption():
    raw = bytearray(encode_frame(Frame(command=1, request_id=1, payload=b"x")))
    raw[-1] ^= 0x01
    try:
        decode_frame(bytes(raw))
    except ValueError as exc:
        assert "CRC" in str(exc)
    else:
        raise AssertionError("corrupted frame accepted")

def test_reject_oversized_payload():
    try:
        encode_frame(Frame(command=1, request_id=1, payload=b"x" * 4097))
    except ValueError as exc:
        assert "large" in str(exc)
    else:
        raise AssertionError("oversized payload accepted")
