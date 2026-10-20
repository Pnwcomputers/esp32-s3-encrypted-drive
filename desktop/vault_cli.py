#!/usr/bin/env python3
"""Command-line interface for the ESP32-S3 Encrypted Hardware Vault.

Usage:
    python -m desktop.vault_cli ports
    python -m desktop.vault_cli status [--port PORT]
    python -m desktop.vault_cli ls [--port PORT]
    python -m desktop.vault_cli upload <filepath> [--port PORT]
    python -m desktop.vault_cli download <filename_or_id> [output_path] [--port PORT]
    python -m desktop.vault_cli delete <filename_or_id> [--port PORT]
    python -m desktop.vault_cli lock [--port PORT]
"""
from __future__ import annotations
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path

# Ensure repository root is on sys.path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from desktop.vault_client import VaultClient, VaultException, VaultLockedException

def format_size(bytes_num: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:3.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"

def print_progress(current: int, total: int, label: str) -> None:
    pct = (current / total) * 100 if total > 0 else 100
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else bar_len
    bar = '=' * filled + '-' * (bar_len - filled)
    sys.stdout.write(f"\r{label} [{bar}] {pct:5.1f}% ({current}/{total} chunks)")
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")

def cmd_ports(args) -> int:
    ports = VaultClient.list_serial_ports()
    if not ports:
        print("No serial ports detected.")
        return 0
    print(f"Detected {len(ports)} serial port(s):")
    for dev, desc, hwid in ports:
        print(f"  - {dev}: {desc} ({hwid})")
    auto = VaultClient.auto_detect_port()
    if auto:
        print(f"\nAuto-selected target port: {auto}")
    return 0

def cmd_status(client: VaultClient, args) -> int:
    print(f"Connecting to {client.port}...")
    status = client.get_status()
    lock_str = "UNLOCKED" if status.is_unlocked else "LOCKED"
    print("\n--- Vault Device Status ---")
    print(f"  State:            {lock_str}")
    print(f"  Firmware Version: {status.firmware_version >> 8}.{status.firmware_version & 0xFF}")
    print(f"  Total Storage:    {status.total_space_mb} MB")
    print(f"  Free Storage:     {status.free_space_mb} MB")
    print(f"  Used Storage:     {status.used_space_mb} MB")
    print(f"  Files in Vault:   {status.file_count}")
    return 0

def cmd_list(client: VaultClient, args) -> int:
    files = client.list_files()
    if not files:
        print("Vault is empty. No files stored.")
        return 0

    print(f"\nStored Vault Files ({len(files)} total):")
    print(f"{'Filename':<32} {'Size':<12} {'Modified':<20} {'File ID':<34}")
    print("-" * 100)
    for f in files:
        dt = datetime.fromtimestamp(f.modified).strftime("%Y-%m-%d %H:%M:%S") if f.modified else "N/A"
        print(f"{f.filename:<32} {format_size(f.size):<12} {dt:<20} {f.file_id_hex:<34}")
    return 0

def cmd_upload(client: VaultClient, args) -> int:
    path = Path(args.filepath)
    if not path.is_file():
        print(f"Error: Local file '{args.filepath}' does not exist.")
        return 1

    size = path.stat().st_size
    print(f"Uploading '{path.name}' ({format_size(size)}) to vault...")
    t0 = time.time()
    file_id = client.upload_file(path, progress_callback=print_progress)
    elapsed = max(0.001, time.time() - t0)
    rate = size / elapsed / 1024
    print(f"Upload complete in {elapsed:.2f}s ({rate:.1f} KB/s). Assigned File ID: {file_id.hex()}")
    return 0

def cmd_download(client: VaultClient, args) -> int:
    target = args.target
    dest = args.destination or "."
    print(f"Downloading '{target}' from vault...")
    t0 = time.time()
    saved_path = client.download_file(target, dest, progress_callback=print_progress)
    size = saved_path.stat().st_size
    elapsed = max(0.001, time.time() - t0)
    rate = size / elapsed / 1024
    print(f"Download complete: saved to '{saved_path}' in {elapsed:.2f}s ({rate:.1f} KB/s).")
    return 0

def cmd_delete(client: VaultClient, args) -> int:
    target = args.target
    confirm = args.yes
    if not confirm:
        res = input(f"Are you sure you want to permanently delete '{target}' from the vault? [y/N]: ")
        if res.strip().lower() not in ("y", "yes"):
            print("Deletion aborted.")
            return 0

    client.delete_file(target)
    print(f"Successfully deleted '{target}' from vault.")
    return 0

def cmd_lock(client: VaultClient, args) -> int:
    client.lock()
    print("Vault has been locked and session encryption keys were purged from RAM.")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="ESP32-S3 Encrypted Hardware Vault CLI")
    parser.add_argument("--port", "-p", default=None, help="Serial port (auto-detected if omitted)")
    parser.add_argument("--baud", "-b", type=int, default=115200, help="Baud rate (default: 115200)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ports
    subparsers.add_parser("ports", help="List available serial ports")

    # status
    subparsers.add_parser("status", help="Query vault operational and lock status")

    # list
    p_ls = subparsers.add_parser("ls", aliases=["list"], help="List encrypted files in vault")

    # upload
    p_up = subparsers.add_parser("upload", help="Upload a file into the vault")
    p_up.add_argument("filepath", help="Path to local file to upload")

    # download
    p_down = subparsers.add_parser("download", help="Download a file from the vault")
    p_down.add_argument("target", help="Filename or 32-character hex File ID")
    p_down.add_argument("destination", nargs="?", default=None, help="Destination directory or filename")

    # delete
    p_del = subparsers.add_parser("delete", help="Delete a file from the vault")
    p_del.add_argument("target", help="Filename or 32-character hex File ID")
    p_del.add_argument("-y", "--yes", action="store_true", help="Confirm deletion without prompting")

    # lock
    subparsers.add_parser("lock", help="Lock the vault immediately")

    args = parser.parse_args()

    if args.command == "ports":
        return cmd_ports(args)

    client = VaultClient(port=args.port, baudrate=args.baud)
    try:
        client.connect()
        if args.command in ("status",):
            return cmd_status(client, args)
        elif args.command in ("ls", "list"):
            return cmd_list(client, args)
        elif args.command == "upload":
            return cmd_upload(client, args)
        elif args.command == "download":
            return cmd_download(client, args)
        elif args.command == "delete":
            return cmd_delete(client, args)
        elif args.command == "lock":
            return cmd_lock(client, args)
    except VaultLockedException as e:
        print(f"\n[VAULT LOCKED]: {e}")
        print("Please authenticate via Wi-Fi AP (192.168.4.1) using your PIN to unlock before executing USB commands.")
        return 2
    except VaultException as e:
        print(f"\nVault Error: {e}")
        return 1
    except ValueError as e:
        # Malformed/garbled device response (e.g. bad UTF-8 or a length mismatch
        # from the parsers) — report cleanly instead of dumping a traceback.
        print(f"\nVault Error: malformed device response ({e})")
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 130
    finally:
        client.disconnect()

    return 0

if __name__ == "__main__":
    sys.exit(main())
