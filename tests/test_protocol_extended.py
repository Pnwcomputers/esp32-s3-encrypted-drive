import struct
from desktop.protocol import *

def test_fragmented_stream_recovers_from_crc_failure():
    decoder = FrameStreamDecoder()
    bad = bytearray(encode_frame(Frame(CMD_GET_STATUS, 1, b'x')))
    bad[-1] ^= 1
    good = Frame(CMD_UPLOAD_CHUNK, 2, b'x'*4116)
    raw = b'noise' + bad + encode_frame(good)
    frames = []
    for i in range(0, len(raw), 7):
        frames += decoder.feed(raw[i:i+7])
    assert frames == [good]

def test_full_chunk_framing():
    payload = encode_upload_chunk(b'1'*16, 0, b'x'*4096)
    frame = Frame(CMD_UPLOAD_CHUNK, 3, payload)
    assert decode_frame(encode_frame(frame)) == frame

def test_large_catalog_framing():
    rec = struct.pack('<H', 127) + b'x'*127 + struct.pack('<QQ', 1, 2) + b'1'*16
    data = b'\0' + struct.pack('<I', 256) + rec*256
    frame = Frame(CMD_LIST_FILES, 4, data)
    assert decode_frame(encode_frame(frame)) == frame
    assert len(parse_list_files_response(data)[1]) == 256

def test_bad_response_dimensions():
    try:
        parse_download_begin_response(b'\0'+b'1'*16+struct.pack('<QII', 100, 4096, 0))
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid download accepted')

def test_empty_and_exact_block_client_transfers():
    from pathlib import Path
    import tempfile
    from test_vault_client import MockVaultDevice, MockSerialPort
    from desktop.vault_client import VaultClient
    for n in (0, 4096, 8192):
        client = VaultClient(serial_instance=MockSerialPort(MockVaultDevice()))
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'input.bin'
            source.write_bytes(b'x'*n)
            file_id = client.upload_file(source)
            dest = Path(temp)/'output.bin'
            client.download_file(file_id, dest)
            assert dest.read_bytes() == source.read_bytes()
