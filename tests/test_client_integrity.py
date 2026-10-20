"""Fault injection for local downloads and serial writes; no hardware required."""
import struct
import tempfile
from pathlib import Path
from unittest.mock import patch

from desktop.protocol import *
from desktop.vault_client import VaultClient, VaultException
from test_vault_client import MockSerialPort, MockVaultDevice


def test_partial_serial_writes():
    class PartialPort(MockSerialPort):
        def write(self, data):
            return super().write(data[:3])
    client = VaultClient(serial_instance=PartialPort(MockVaultDevice()))
    assert client.get_status().is_unlocked


def test_stalled_serial_write_fails():
    port = MockSerialPort(MockVaultDevice())
    port.write = lambda data: 0
    try:
        VaultClient(serial_instance=port).get_status()
    except VaultException:
        pass
    else:
        raise AssertionError('stalled write accepted')


def test_ambiguous_and_unrelated_ports_are_not_selected():
    with patch.object(VaultClient, 'list_serial_ports', return_value=[('COM1', 'Other device', 'OTHER')]):
        assert VaultClient.auto_detect_port() is None
    with patch.object(VaultClient, 'list_serial_ports', return_value=[('COM1', 'ESP32', ''), ('COM2', 'ESP32', '')]):
        assert VaultClient.auto_detect_port() is None


def test_failed_download_preserves_destination_and_existing_part_file():
    class CorruptDevice(MockVaultDevice):
        def _handle_frame(self, frame):
            payload = super()._handle_frame(frame)
            if frame.command == CMD_DOWNLOAD_CHUNK:
                return payload[:-1]
            return payload
    client = VaultClient(serial_instance=MockSerialPort(CorruptDevice()))
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp)/'source.bin'
        source.write_bytes(b'secret' * 1000)
        file_id = client.upload_file(source)
        dest = Path(temp)/'out.bin'
        dest.write_bytes(b'original')
        part = Path(temp)/'out.bin.part'
        part.write_bytes(b'belongs to user')
        try:
            client.download_file(file_id, dest)
        except VaultException:
            pass
        else:
            raise AssertionError('short chunk accepted')
        assert dest.read_bytes() == b'original'
        assert part.read_bytes() == b'belongs to user'
        assert not list(Path(temp).glob('.vault-*.part'))


def test_empty_commit_response_is_not_success():
    class MissingAck(MockVaultDevice):
        def _handle_frame(self, frame):
            payload = super()._handle_frame(frame)
            return b'' if frame.command == CMD_UPLOAD_COMMIT else payload
    client = VaultClient(serial_instance=MockSerialPort(MissingAck()))
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp)/'source.bin'
        source.write_bytes(b'data')
        try:
            client.upload_file(source)
        except VaultException:
            pass
        else:
            raise AssertionError('missing commit acknowledgement accepted')


def test_path_names_rejected():
    for name in ('../secret', '..', 'a\\b', 'a\x00b', 'a\nb'):
        try:
            encode_upload_begin(name, 1)
        except ValueError:
            pass
        else:
            raise AssertionError('unsafe filename accepted')


def test_fourteen_byte_filename_download():
    client = VaultClient(serial_instance=MockSerialPort(MockVaultDevice()))
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp)/'1234567890.txt'
        source.write_bytes(b'round trip')
        client.upload_file(source)
        dest = Path(temp)/'output.txt'
        client.download_file(source.name, dest)
        assert dest.read_bytes() == source.read_bytes()


def test_hex_id_download():
    client = VaultClient(serial_instance=MockSerialPort(MockVaultDevice()))
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp)/'source.txt'
        source.write_bytes(b'hex ID round trip')
        file_id = client.upload_file(source)
        dest = Path(temp)/'output.txt'
        client.download_file(file_id.hex(), dest)
        assert dest.read_bytes() == source.read_bytes()
