import os
import io
import sys
import struct
import tempfile
from pathlib import Path

# Ensure repository root is on sys.path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from desktop.protocol import (
    Frame, encode_frame, decode_frame, FrameStreamDecoder,
    CMD_GET_STATUS, CMD_LIST_FILES, CMD_UPLOAD_BEGIN, CMD_UPLOAD_CHUNK,
    CMD_UPLOAD_COMMIT, CMD_DOWNLOAD_BEGIN, CMD_DOWNLOAD_CHUNK, CMD_DOWNLOAD_END,
    CMD_DELETE_FILE, CMD_LOCK,
    STATUS_OK, STATUS_ERR_LOCKED, STATUS_ERR_NOT_FOUND
)
from desktop.vault_client import (
    VaultClient, VaultLockedException, VaultNotFoundException
)

class MockVaultDevice:
    """In-memory simulation of the ESP32-S3 Vault firmware for client testing."""
    def __init__(self):
        self.is_unlocked = True
        self.files = {}  # file_id -> { "name": str, "data": bytes, "time": int }
        self.active_upload = None
        self.decoder = FrameStreamDecoder()
        self.tx_buffer = bytearray()

    def process_incoming(self, raw_bytes: bytes) -> bytes:
        frames = self.decoder.feed(raw_bytes)
        responses = bytearray()
        for f in frames:
            resp_payload = self._handle_frame(f)
            resp_frame = Frame(command=f.command, request_id=f.request_id, payload=resp_payload)
            responses.extend(encode_frame(resp_frame))
        return bytes(responses)

    def _handle_frame(self, frame: Frame) -> bytes:
        cmd = frame.command
        p = frame.payload

        if cmd == CMD_GET_STATUS:
            return struct.pack("<BBHIII", STATUS_OK, 1 if self.is_unlocked else 0, 0x0100, 64000, 58000, len(self.files))

        if not self.is_unlocked and cmd != CMD_LOCK:
            return bytes([STATUS_ERR_LOCKED])

        if cmd == CMD_LOCK:
            self.is_unlocked = False
            return bytes([STATUS_OK])

        if cmd == CMD_LIST_FILES:
            buf = bytearray([STATUS_OK])
            buf.extend(struct.pack("<I", len(self.files)))
            for fid, f in self.files.items():
                name_b = f["name"].encode("utf-8")
                buf.extend(struct.pack("<H", len(name_b)))
                buf.extend(name_b)
                buf.extend(struct.pack("<QQ", len(f["data"]), f["time"]))
                buf.extend(fid)
            return bytes(buf)

        if cmd == CMD_UPLOAD_BEGIN:
            name_len, = struct.unpack_from("<H", p, 0)
            name = p[2:2 + name_len].decode("utf-8")
            total_size, = struct.unpack_from("<Q", p, 2 + name_len)
            fid = os.urandom(16)
            self.active_upload = {"fid": fid, "name": name, "size": total_size, "chunks": {}}
            return bytes([STATUS_OK]) + fid + struct.pack("<I", 4096)

        if cmd == CMD_UPLOAD_CHUNK:
            fid = p[:16]
            chunk_idx, = struct.unpack_from("<I", p, 16)
            chunk_data = p[20:]
            self.active_upload["chunks"][chunk_idx] = chunk_data
            return bytes([STATUS_OK]) + struct.pack("<I", chunk_idx)

        if cmd == CMD_UPLOAD_COMMIT:
            fid = p[:16]
            # assemble chunks
            assembled = bytearray()
            for i in sorted(self.active_upload["chunks"].keys()):
                assembled.extend(self.active_upload["chunks"][i])
            self.files[fid] = {"name": self.active_upload["name"], "data": bytes(assembled), "time": 1700000000}
            self.active_upload = None
            return bytes([STATUS_OK])

        if cmd == CMD_DOWNLOAD_BEGIN:
            target_id = None
            if len(p) == 16 and p in self.files:
                target_id = p
            elif len(p) > 2:
                name_len, = struct.unpack_from("<H", p, 0)
                name = p[2:2 + name_len].decode("utf-8")
                for fid, f in self.files.items():
                    if f["name"] == name:
                        target_id = fid
                        break

            if not target_id:
                return bytes([STATUS_ERR_NOT_FOUND])

            data = self.files[target_id]["data"]
            total_size = len(data)
            chunk_size = 4096
            total_chunks = max(1, (total_size + chunk_size - 1) // chunk_size) if total_size > 0 else 1
            return bytes([STATUS_OK]) + target_id + struct.pack("<QII", total_size, chunk_size, total_chunks)

        if cmd == CMD_DOWNLOAD_CHUNK:
            fid = p[:16]
            chunk_idx, = struct.unpack_from("<I", p, 16)
            data = self.files[fid]["data"]
            chunk_size = 4096
            start = chunk_idx * chunk_size
            chunk = data[start:start + chunk_size]
            return bytes([STATUS_OK]) + struct.pack("<I", chunk_idx) + chunk

        if cmd == CMD_DOWNLOAD_END:
            return bytes([STATUS_OK])

        if cmd == CMD_DELETE_FILE:
            fid = p[:16]
            if fid in self.files:
                del self.files[fid]
                return bytes([STATUS_OK])
            return bytes([STATUS_ERR_NOT_FOUND])

        return bytes([STATUS_ERR_NOT_FOUND])

class MockSerialPort:
    def __init__(self, device: MockVaultDevice):
        self.device = device
        self.in_buffer = bytearray()
        self.is_open = True

    def write(self, data: bytes):
        resp = self.device.process_incoming(data)
        self.in_buffer.extend(resp)
        return len(data)

    def read(self, size: int = 512) -> bytes:
        chunk = bytes(self.in_buffer[:size])
        del self.in_buffer[:size]
        return chunk

    def reset_input_buffer(self):
        self.in_buffer.clear()

    def reset_output_buffer(self):
        pass

    def close(self):
        self.is_open = False

def test_mock_vault_client_lifecycle():
    device = MockVaultDevice()
    mock_serial = MockSerialPort(device)
    client = VaultClient(serial_instance=mock_serial)

    # 1. Query status
    st = client.get_status()
    assert st.is_unlocked is True
    assert st.file_count == 0

    # 2. Upload a multi-chunk file (10 KB = 3 chunks with 4KB chunk size)
    content = b"TOP_SECRET_DATA_" * 640  # 10240 bytes
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        progress_events = []
        def on_prog(cur, tot, name):
            progress_events.append((cur, tot, name))

        file_id = client.upload_file(tmp_path, progress_callback=on_prog)
        assert len(file_id) == 16
        assert len(progress_events) == 3

        # 3. List files
        files = client.list_files()
        assert len(files) == 1
        assert files[0].file_id == file_id
        assert files[0].size == len(content)

        # 4. Download file
        out_dest = tempfile.mktemp(suffix=".bin")
        client.download_file(file_id, out_dest)
        with open(out_dest, "rb") as f:
            downloaded = f.read()
        assert downloaded == content
        os.unlink(out_dest)

        # 5. Delete file
        client.delete_file(file_id)
        assert len(client.list_files()) == 0

        # 6. Lock device
        client.lock()
        assert client.get_status().is_unlocked is False

        # Attempting list_files when locked must raise VaultLockedException
        try:
            client.list_files()
        except VaultLockedException:
            pass
        else:
            raise AssertionError("Should have raised VaultLockedException")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

if __name__ == "__main__":
    test_mock_vault_client_lifecycle()
    print("Mock vault client tests passed successfully!")
