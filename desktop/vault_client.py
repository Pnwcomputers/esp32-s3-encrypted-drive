"""High-level client for communicating with the ESP32-S3 Encrypted Hardware Vault.

Provides automatic serial port detection, request-response handling,
chunked uploading/downloading with progress tracking, file listing,
atomic file saves, deletion, and lock commands.
"""
from __future__ import annotations
import os
import time
import math
import tempfile
import threading
from typing import List, Optional, Callable, Tuple
from pathlib import Path

from desktop.protocol import (
    Frame, FrameStreamDecoder, encode_frame,
    CMD_GET_STATUS, CMD_LIST_FILES,
    CMD_UPLOAD_BEGIN, CMD_UPLOAD_CHUNK, CMD_UPLOAD_COMMIT,
    CMD_DOWNLOAD_BEGIN, CMD_DOWNLOAD_CHUNK, CMD_DOWNLOAD_END,
    CMD_DELETE_FILE, CMD_LOCK,
    STATUS_OK, STATUS_ERR_LOCKED, STATUS_ERR_NOT_FOUND, STATUS_ERR_AUTH_FAIL,
    STATUS_MESSAGES, VaultStatus, FileInfo,
    parse_status_response, parse_list_files_response,
    encode_upload_begin, parse_upload_begin_response,
    encode_upload_chunk, parse_upload_chunk_response,
    encode_download_begin, parse_download_begin_response,
    encode_download_chunk, parse_download_chunk_response
)

class VaultException(Exception):
    """Base exception for Vault client operations."""
    pass

class VaultLockedException(VaultException):
    """Raised when an operation fails because the vault is locked."""
    pass

class VaultNotFoundException(VaultException):
    """Raised when a requested file is not found in the vault."""
    pass

class VaultAuthException(VaultException):
    """Raised when cryptographic verification fails."""
    pass

class VaultClient:
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200, timeout: float = 3.0, serial_instance=None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = serial_instance
        self._decoder = FrameStreamDecoder()
        self._request_id_counter = 1
        self._command_lock = threading.Lock()

    @classmethod
    def list_serial_ports(cls) -> List[Tuple[str, str, str]]:
        """List available serial ports as (device, description, hwid)."""
        try:
            import serial.tools.list_ports
            return [(p.device, p.description, p.hwid) for p in serial.tools.list_ports.comports()]
        except ImportError:
            return []

    @classmethod
    def auto_detect_port(cls) -> Optional[str]:
        """Attempt to find ESP32-S3 TinyUSB CDC port."""
        ports = cls.list_serial_ports()
        matches = []
        for dev, desc, hwid in ports:
            # Espressif USB VID 0x303A or TinyUSB CDC markers
            if "303A" in hwid.upper() or "ESP32" in desc.upper() or "USB CDC" in desc.upper():
                matches.append(dev)
        return matches[0] if len(matches) == 1 else None

    def connect(self) -> None:
        if self.serial is not None and getattr(self.serial, "is_open", True):
            return

        if not self.port:
            detected = self.auto_detect_port()
            if not detected:
                raise VaultException("No serial port specified and no ESP32 device auto-detected.")
            self.port = detected

        try:
            import serial
            self.serial = serial.Serial(self.port, self.baudrate, timeout=0.1)
            time.sleep(0.05)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
        except ImportError:
            raise VaultException("pyserial is required for hardware serial communication. Run: pip install pyserial")
        except Exception as e:
            raise VaultException(f"Failed to open port {self.port}: {e}")

    def disconnect(self) -> None:
        if self.serial is not None:
            try:
                self.serial.close()
            except Exception:
                pass
            self.serial = None
        self._decoder = FrameStreamDecoder()

    def _next_request_id(self) -> int:
        req_id = self._request_id_counter
        self._request_id_counter = (self._request_id_counter + 1) & 0xFFFFFFFF
        return req_id

    def send_command(self, command: int, payload: bytes = b"") -> Frame:
        """Send command frame and wait for response matching command & request_id."""
        with self._command_lock:
            return self._send_command(command, payload)

    def _send_command(self, command: int, payload: bytes) -> Frame:
        if self.serial is None:
            self.connect()

        req_id = self._next_request_id()
        frame = Frame(command=command, request_id=req_id, payload=payload)
        encoded = encode_frame(frame)

        written = 0
        while written < len(encoded):
            count = self.serial.write(encoded[written:])
            if not isinstance(count, int) or count <= 0:
                raise VaultException('Serial write did not make progress')
            written += count
        if hasattr(self.serial, "flush"):
            self.serial.flush()

        start_time = time.monotonic()
        while time.monotonic() - start_time < self.timeout:
            chunk = self.serial.read(512)
            if chunk:
                frames = self._decoder.feed(chunk)
                for f in frames:
                    if f.command == command and f.request_id == req_id:
                        return f
            else:
                time.sleep(0.01)

        raise VaultException(f"Timed out waiting for response to command 0x{command:02X}")

    def _check_status(self, status: int, context: str = "") -> None:
        if status == STATUS_OK:
            return
        msg = STATUS_MESSAGES.get(status, f"Unknown error (code {status})")
        err_msg = f"{context}: {msg}" if context else msg
        if status == STATUS_ERR_LOCKED:
            raise VaultLockedException(err_msg)
        elif status == STATUS_ERR_NOT_FOUND:
            raise VaultNotFoundException(err_msg)
        elif status == STATUS_ERR_AUTH_FAIL:
            raise VaultAuthException(err_msg)
        else:
            raise VaultException(err_msg)

    def get_status(self) -> VaultStatus:
        """Query vault operational and lock status."""
        resp = self.send_command(CMD_GET_STATUS)
        if len(resp.payload) > 0 and resp.payload[0] != STATUS_OK:
            self._check_status(resp.payload[0], "Get status failed")
        status_info = parse_status_response(resp.payload)
        return status_info

    def list_files(self) -> List[FileInfo]:
        """Retrieve list of all encrypted files stored in the vault."""
        resp = self.send_command(CMD_LIST_FILES)
        if len(resp.payload) > 0 and resp.payload[0] != STATUS_OK:
            self._check_status(resp.payload[0], "List files failed")
        status, files = parse_list_files_response(resp.payload)
        self._check_status(status, "List files failed")
        return files

    def upload_file(self, local_path: str | Path,
                    progress_callback: Optional[Callable[[int, int, str], None]] = None) -> bytes:
        """Upload a local file to the vault with chunked encryption."""
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        file_size = path.stat().st_size
        filename = path.name

        # 1. Begin upload
        begin_payload = encode_upload_begin(filename, file_size)
        resp = self.send_command(CMD_UPLOAD_BEGIN, begin_payload)
        if len(resp.payload) > 0 and resp.payload[0] != STATUS_OK:
            self._check_status(resp.payload[0], "Upload begin failed")
        status, file_id, max_chunk = parse_upload_begin_response(resp.payload)
        self._check_status(status, "Upload begin failed")

        if max_chunk != 4096:
            raise VaultException('Device advertised unsupported chunk size')
        chunk_size = max_chunk
        total_chunks = max(1, math.ceil(file_size / chunk_size)) if file_size > 0 else 1

        # 2. Upload chunks
        with open(path, "rb") as f:
            chunk_idx = 0
            while True:
                data = f.read(chunk_size)
                if not data and chunk_idx > 0:
                    break

                chunk_payload = encode_upload_chunk(file_id, chunk_idx, data)
                chunk_resp = self.send_command(CMD_UPLOAD_CHUNK, chunk_payload)
                if len(chunk_resp.payload) > 0 and chunk_resp.payload[0] != STATUS_OK:
                    self._check_status(chunk_resp.payload[0], f"Upload chunk {chunk_idx} failed")
                c_status, ack_idx = parse_upload_chunk_response(chunk_resp.payload)
                self._check_status(c_status, f"Upload chunk {chunk_idx} failed")
                if ack_idx != chunk_idx:
                    raise VaultException('Upload chunk acknowledgement mismatch')

                chunk_idx += 1
                if progress_callback:
                    progress_callback(chunk_idx, total_chunks, filename)

                if len(data) < chunk_size:
                    break

        # 3. Commit upload
        commit_resp = self.send_command(CMD_UPLOAD_COMMIT, file_id)
        self._require_ok(commit_resp, 'Upload commit failed')

        return file_id

    def download_file(self, file_id_or_name: str | bytes, dest_path: str | Path,
                      progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Path:
        """Download and decrypt a file from the vault to a local destination."""
        if (isinstance(file_id_or_name, str) and len(file_id_or_name) == 32
                and all(c in '0123456789abcdefABCDEF' for c in file_id_or_name)):
            file_id_or_name = bytes.fromhex(file_id_or_name)
        dest = Path(dest_path)
        if dest.is_dir():
            if isinstance(file_id_or_name, str):
                from desktop.protocol import _name
                _name(file_id_or_name)
                if file_id_or_name in (".", "..") or any(c in file_id_or_name for c in "/\\"):
                    raise VaultException("Unsafe destination filename")
                dest = dest / file_id_or_name
            else:
                dest = dest / f"vault_{file_id_or_name.hex()[:8]}.bin"

        dest.parent.mkdir(parents=True, exist_ok=True)

        # 1. Begin download
        if isinstance(file_id_or_name, str):
            matches = [f for f in self.list_files() if f.filename == file_id_or_name]
            if not matches:
                raise VaultNotFoundException('File not found')
            file_id_or_name = matches[0].file_id
        begin_payload = encode_download_begin(file_id_or_name)
        resp = self.send_command(CMD_DOWNLOAD_BEGIN, begin_payload)
        if len(resp.payload) > 0 and resp.payload[0] != STATUS_OK:
            self._check_status(resp.payload[0], "Download begin failed")
        status, file_id, total_size, chunk_size, total_chunks = parse_download_begin_response(resp.payload)
        self._check_status(status, "Download begin failed")

        # 2. Fetch chunks
        fd, temporary = tempfile.mkstemp(prefix='.vault-', suffix='.part', dir=dest.parent)
        tmp_dest = Path(temporary)
        received = 0
        try:
            with os.fdopen(fd, "wb") as f:
                for chunk_idx in range(total_chunks):
                    req_payload = encode_download_chunk(file_id, chunk_idx)
                    chunk_resp = self.send_command(CMD_DOWNLOAD_CHUNK, req_payload)
                    if len(chunk_resp.payload) > 0 and chunk_resp.payload[0] != STATUS_OK:
                        self._check_status(chunk_resp.payload[0], f"Download chunk {chunk_idx} failed")
                    c_status, ack_idx, chunk_data = parse_download_chunk_response(chunk_resp.payload)
                    self._check_status(c_status, f"Download chunk {chunk_idx} failed")
                    expected = min(chunk_size, total_size - received)
                    if ack_idx != chunk_idx or len(chunk_data) != expected:
                        raise VaultException('Download chunk index or length mismatch')
                    received += len(chunk_data)

                    if chunk_data:
                        f.write(chunk_data)

                    if progress_callback:
                        progress_callback(chunk_idx + 1, total_chunks, dest.name)

                f.flush()
                os.fsync(f.fileno())
            if received != total_size:
                raise VaultException('Download size mismatch')
            # 3. End download session
            end_resp = self.send_command(CMD_DOWNLOAD_END, file_id)
            self._require_ok(end_resp, 'Download end failed')

            # Atomic commit on host
            os.replace(tmp_dest, dest)
            return dest
        except Exception:
            try:
                self.send_command(CMD_DOWNLOAD_END, file_id)
            except Exception:
                pass
            if tmp_dest.exists():
                tmp_dest.unlink()
            raise

    def delete_file(self, file_id_or_name: str | bytes) -> None:
        """Delete an encrypted file from the vault."""
        target_id: bytes
        if isinstance(file_id_or_name, str):
            # Check if hex string of 32 chars
            if len(file_id_or_name) == 32 and all(c in "0123456789abcdefABCDEF" for c in file_id_or_name):
                target_id = bytes.fromhex(file_id_or_name)
            else:
                # Find by filename in file list
                files = self.list_files()
                match = [f for f in files if f.filename == file_id_or_name]
                if not match:
                    raise VaultNotFoundException(f"File '{file_id_or_name}' not found in vault")
                target_id = match[0].file_id
        else:
            target_id = file_id_or_name

        resp = self.send_command(CMD_DELETE_FILE, target_id)
        self._require_ok(resp, 'Delete file failed')

    def lock(self) -> None:
        """Immediately lock the vault and clear session keys."""
        resp = self.send_command(CMD_LOCK)
        self._require_ok(resp, 'Lock command failed')

    def _require_ok(self, response: Frame, context: str) -> None:
        if len(response.payload) != 1:
            raise VaultException(f'{context}: malformed acknowledgement')
        self._check_status(response.payload[0], context)
