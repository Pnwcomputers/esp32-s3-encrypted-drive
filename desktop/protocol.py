"""Protocol constants and framing helpers for the planned USB CDC interface.

This is a framing prototype only, not a secure or complete transport implementation.
The firmware must independently validate every field and length.
"""
from __future__ import annotations
import struct
import zlib
from dataclasses import dataclass

MAGIC = b"VLT1"
PROTOCOL_VERSION = 1
MAX_PAYLOAD = 4096
# magic[4], version[u8], command[u8], request_id[u32], payload_len[u32]
HEADER = struct.Struct("<4sBBII")
CRC = struct.Struct("<I")

@dataclass(frozen=True)
class Frame:
    command: int
    request_id: int
    payload: bytes = b""

def encode_frame(frame: Frame) -> bytes:
    if not (0 <= frame.command <= 255):
        raise ValueError("command must fit u8")
    if not (0 <= frame.request_id <= 0xFFFFFFFF):
        raise ValueError("request_id must fit u32")
    if len(frame.payload) > MAX_PAYLOAD:
        raise ValueError("payload too large")
    header = HEADER.pack(MAGIC, PROTOCOL_VERSION, frame.command,
                         frame.request_id, len(frame.payload))
    body = header + frame.payload
    return body + CRC.pack(zlib.crc32(body) & 0xFFFFFFFF)

def decode_frame(data: bytes) -> Frame:
    if len(data) < HEADER.size + CRC.size:
        raise ValueError("frame too short")
    magic, version, command, request_id, payload_len = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise ValueError("bad magic")
    if version != PROTOCOL_VERSION:
        raise ValueError("unsupported protocol version")
    if payload_len > MAX_PAYLOAD:
        raise ValueError("payload too large")
    expected_len = HEADER.size + payload_len + CRC.size
    if len(data) != expected_len:
        raise ValueError("frame length mismatch")
    expected_crc, = CRC.unpack_from(data, expected_len - CRC.size)
    actual_crc = zlib.crc32(data[:-CRC.size]) & 0xFFFFFFFF
    if expected_crc != actual_crc:
        raise ValueError("CRC mismatch")
    payload = data[HEADER.size:HEADER.size + payload_len]
    return Frame(command=command, request_id=request_id, payload=payload)
