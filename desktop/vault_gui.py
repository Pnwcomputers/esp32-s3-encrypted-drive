#!/usr/bin/env python3
"""Graphical user interface for the ESP32-S3 Encrypted Hardware Vault.

Built with PySide6. Provides file browsing, drag-and-drop uploading,
downloading, deletion, storage visualization, and device locking.
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
from datetime import datetime

# Ensure repository root is on sys.path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from PySide6.QtCore import Qt, QThread, Signal, Slot
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
        QHeaderView, QProgressBar, QFileDialog, QMessageBox, QStatusBar,
        QFrame, QSplitter
    )
    from PySide6.QtGui import QFont, QIcon, QColor
    HAS_PYSIDE = True
except ImportError:
    HAS_PYSIDE = False

from desktop.vault_client import VaultClient, VaultException, VaultLockedException, FileInfo, VaultStatus

def format_size(bytes_num: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:3.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"

if HAS_PYSIDE:
    class TransferWorker(QThread):
        progress = Signal(int, int, str)
        finished = Signal(bool, str)

        def __init__(self, client: VaultClient, op_type: str, local_path: str, target: str):
            super().__init__()
            self.client = client
            self.op_type = op_type
            self.local_path = local_path
            self.target = target

        def run(self):
            try:
                if self.op_type == "upload":
                    self.client.upload_file(
                        self.local_path,
                        progress_callback=lambda cur, tot, name: self.progress.emit(cur, tot, name)
                    )
                    self.finished.emit(True, f"Uploaded {Path(self.local_path).name} successfully")
                elif self.op_type == "download":
                    saved = self.client.download_file(
                        self.target,
                        self.local_path,
                        progress_callback=lambda cur, tot, name: self.progress.emit(cur, tot, name)
                    )
                    self.finished.emit(True, f"Downloaded to {saved.name}")
            except Exception as e:
                self.finished.emit(False, str(e))

    class VaultMainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.client: VaultClient | None = None
            self.worker: TransferWorker | None = None
            self.setWindowTitle("ESP32-S3 Encrypted Hardware Vault")
            self.resize(900, 600)
            self._init_ui()
            self._refresh_ports()

        def _init_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            main_layout = QVBoxLayout(central)
            main_layout.setSpacing(12)
            main_layout.setContentsMargins(16, 16, 16, 16)

            # Top toolbar (Connection & Device Status)
            top_panel = QFrame()
            top_panel.setStyleSheet("background: #1e1e2e; border-radius: 8px; padding: 10px;")
            top_layout = QHBoxLayout(top_panel)
            top_layout.setContentsMargins(8, 8, 8, 8)

            lbl_port = QLabel("Device Port:")
            lbl_port.setStyleSheet("font-weight: bold; color: #cdd6f4;")
            self.combo_ports = QComboBox()
            self.combo_ports.setMinimumWidth(200)

            btn_refresh_ports = QPushButton("↻")
            btn_refresh_ports.setToolTip("Refresh COM ports")
            btn_refresh_ports.clicked.connect(self._refresh_ports)

            self.btn_connect = QPushButton("Connect")
            self.btn_connect.setStyleSheet("background: #89b4fa; color: #11111b; font-weight: bold; padding: 6px 14px;")
            self.btn_connect.clicked.connect(self._toggle_connection)

            top_layout.addWidget(lbl_port)
            top_layout.addWidget(self.combo_ports)
            top_layout.addWidget(btn_refresh_ports)
            top_layout.addWidget(self.btn_connect)
            top_layout.addSpacing(20)

            self.lbl_status_badge = QLabel("DISCONNECTED")
            self.lbl_status_badge.setStyleSheet("background: #45475a; color: #cdd6f4; font-weight: bold; padding: 4px 10px; border-radius: 6px;")
            top_layout.addWidget(self.lbl_status_badge)

            top_layout.addStretch()

            self.btn_lock = QPushButton("🔒 Lock Vault")
            self.btn_lock.setStyleSheet("background: #f38ba8; color: #11111b; font-weight: bold; padding: 6px 14px;")
            self.btn_lock.setEnabled(False)
            self.btn_lock.clicked.connect(self._lock_device)
            top_layout.addWidget(self.btn_lock)

            main_layout.addWidget(top_panel)

            # Storage capacity gauge
            storage_frame = QFrame()
            storage_frame.setStyleSheet("background: #181825; border-radius: 8px; padding: 8px;")
            storage_layout = QHBoxLayout(storage_frame)
            self.lbl_storage_info = QLabel("Storage: Not connected")
            self.lbl_storage_info.setStyleSheet("color: #a6adc8;")
            self.storage_bar = QProgressBar()
            self.storage_bar.setRange(0, 100)
            self.storage_bar.setValue(0)
            self.storage_bar.setTextVisible(True)
            self.storage_bar.setStyleSheet("QProgressBar { background: #313244; border-radius: 4px; text-align: center; } QProgressBar::chunk { background: #a6e3a1; border-radius: 4px; }")
            storage_layout.addWidget(self.lbl_storage_info)
            storage_layout.addWidget(self.storage_bar)
            main_layout.addWidget(storage_frame)

            # Action bar
            action_layout = QHBoxLayout()
            self.btn_upload = QPushButton("Upload File...")
            self.btn_upload.setStyleSheet("background: #a6e3a1; color: #11111b; font-weight: bold; padding: 8px 16px;")
            self.btn_upload.setEnabled(False)
            self.btn_upload.clicked.connect(self._upload_file_dialog)

            self.btn_download = QPushButton("Download Selected")
            self.btn_download.setStyleSheet("background: #89dceb; color: #11111b; font-weight: bold; padding: 8px 16px;")
            self.btn_download.setEnabled(False)
            self.btn_download.clicked.connect(self._download_selected)

            self.btn_delete = QPushButton("Delete Selected")
            self.btn_delete.setStyleSheet("background: #eba0ac; color: #11111b; font-weight: bold; padding: 8px 16px;")
            self.btn_delete.setEnabled(False)
            self.btn_delete.clicked.connect(self._delete_selected)

            self.btn_refresh_files = QPushButton("Refresh List")
            self.btn_refresh_files.setEnabled(False)
            self.btn_refresh_files.clicked.connect(self._refresh_file_list)

            action_layout.addWidget(self.btn_upload)
            action_layout.addWidget(self.btn_download)
            action_layout.addWidget(self.btn_delete)
            action_layout.addStretch()
            action_layout.addWidget(self.btn_refresh_files)
            main_layout.addLayout(action_layout)

            # Files table
            self.table = QTableWidget()
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Filename", "Size", "Date Modified", "Encrypted File ID"])
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self.table.setSelectionBehavior(QTableWidget.SelectRows)
            self.table.setSelectionMode(QTableWidget.SingleSelection)
            self.table.setStyleSheet("QTableWidget { background: #11111b; color: #cdd6f4; gridline-color: #313244; } QHeaderView::section { background: #181825; color: #cdd6f4; padding: 6px; }")
            main_layout.addWidget(self.table)

            # Transfer progress
            self.transfer_bar = QProgressBar()
            self.transfer_bar.setVisible(False)
            main_layout.addWidget(self.transfer_bar)

            # Status bar
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
            self.status_bar.showMessage("Ready. Select device port and click Connect.")

        def _refresh_ports(self):
            self.combo_ports.clear()
            ports = VaultClient.list_serial_ports()
            for dev, desc, hwid in ports:
                self.combo_ports.addItem(f"{dev} - {desc}", dev)
            auto = VaultClient.auto_detect_port()
            if auto:
                idx = self.combo_ports.findData(auto)
                if idx >= 0:
                    self.combo_ports.setCurrentIndex(idx)

        def _toggle_connection(self):
            if self.client is None:
                port = self.combo_ports.currentData()
                if not port:
                    QMessageBox.warning(self, "No Port", "Please select or connect a valid USB CDC serial port.")
                    return
                try:
                    self.client = VaultClient(port=port)
                    self.client.connect()
                    status = self.client.get_status()

                    self.btn_connect.setText("Disconnect")
                    self.btn_connect.setStyleSheet("background: #f38ba8; color: #11111b; font-weight: bold; padding: 6px 14px;")

                    if status.is_unlocked:
                        self.lbl_status_badge.setText("VAULT UNLOCKED")
                        self.lbl_status_badge.setStyleSheet("background: #a6e3a1; color: #11111b; font-weight: bold; padding: 4px 10px; border-radius: 6px;")
                        self.btn_lock.setEnabled(True)
                        self.btn_upload.setEnabled(True)
                        self.btn_download.setEnabled(True)
                        self.btn_delete.setEnabled(True)
                        self.btn_refresh_files.setEnabled(True)
                        self._update_storage_ui(status)
                        self._refresh_file_list()
                    else:
                        self.lbl_status_badge.setText("LOCKED")
                        self.lbl_status_badge.setStyleSheet("background: #fab387; color: #11111b; font-weight: bold; padding: 4px 10px; border-radius: 6px;")
                        QMessageBox.information(
                            self, "Vault Locked",
                            "Device is connected but locked.\n\nPlease connect to the Wi-Fi AP ('MyEarPods') and submit your PIN on http://192.168.4.1 to unlock."
                        )
                except Exception as e:
                    if self.client:
                        self.client.disconnect()
                    self.client = None
                    QMessageBox.critical(self, "Connection Error", f"Failed to connect to device:\n{e}")
            else:
                self._disconnect_client()

        def closeEvent(self, event):
            if self.worker and self.worker.isRunning():
                QMessageBox.information(self, "Transfer active", "Wait for the current transfer to finish before closing.")
                event.ignore()
                return
            self._disconnect_client()
            event.accept()

        def _disconnect_client(self):
            if self.client:
                self.client.disconnect()
                self.client = None
            self.btn_connect.setText("Connect")
            self.btn_connect.setStyleSheet("background: #89b4fa; color: #11111b; font-weight: bold; padding: 6px 14px;")
            self.lbl_status_badge.setText("DISCONNECTED")
            self.lbl_status_badge.setStyleSheet("background: #45475a; color: #cdd6f4; font-weight: bold; padding: 4px 10px; border-radius: 6px;")
            self.btn_lock.setEnabled(False)
            self.btn_upload.setEnabled(False)
            self.btn_download.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_refresh_files.setEnabled(False)
            self.table.setRowCount(0)
            self.lbl_storage_info.setText("Storage: Not connected")
            self.storage_bar.setValue(0)
            self.status_bar.showMessage("Disconnected.")

        def _update_storage_ui(self, status: VaultStatus):
            used = status.used_space_mb
            total = status.total_space_mb
            pct = int((used / total) * 100) if total > 0 else 0
            self.lbl_storage_info.setText(f"Storage: {used} MB used / {total} MB total ({status.free_space_mb} MB free)")
            self.storage_bar.setValue(pct)

        def _refresh_file_list(self):
            if not self.client:
                return
            try:
                files = self.client.list_files()
                self.table.setRowCount(len(files))
                for row, f in enumerate(files):
                    dt_str = datetime.fromtimestamp(f.modified).strftime("%Y-%m-%d %H:%M:%S") if f.modified else "N/A"
                    self.table.setItem(row, 0, QTableWidgetItem(f.filename))
                    self.table.setItem(row, 1, QTableWidgetItem(format_size(f.size)))
                    self.table.setItem(row, 2, QTableWidgetItem(dt_str))
                    item_id = QTableWidgetItem(f.file_id_hex)
                    item_id.setData(Qt.UserRole, f.file_id)
                    self.table.setItem(row, 3, item_id)
                self.status_bar.showMessage(f"Loaded {len(files)} files from vault.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to list vault files:\n{e}")

        def _upload_file_dialog(self):
            if not self.client:
                return
            filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Encrypt & Store in Vault")
            if not filepath:
                return

            self._set_transfer_mode(True, f"Uploading {Path(filepath).name}...")
            self.worker = TransferWorker(self.client, "upload", filepath, "")
            self.worker.progress.connect(self._on_transfer_progress)
            self.worker.finished.connect(self._on_transfer_finished)
            self.worker.start()

        def _download_selected(self):
            if not self.client:
                return
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.warning(self, "Selection Required", "Please select a file to download.")
                return

            filename = self.table.item(row, 0).text()
            file_id = self.table.item(row, 3).data(Qt.UserRole)

            dest_path, _ = QFileDialog.getSaveFileName(self, "Save Decrypted File", filename)
            if not dest_path:
                return

            self._set_transfer_mode(True, f"Downloading {filename}...")
            self.worker = TransferWorker(self.client, "download", dest_path, file_id)
            self.worker.progress.connect(self._on_transfer_progress)
            self.worker.finished.connect(self._on_transfer_finished)
            self.worker.start()

        def _delete_selected(self):
            if not self.client:
                return
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.warning(self, "Selection Required", "Please select a file to delete.")
                return

            filename = self.table.item(row, 0).text()
            file_id = self.table.item(row, 3).data(Qt.UserRole)

            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to permanently delete '{filename}' from the vault?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            try:
                self.client.delete_file(file_id)
                self.status_bar.showMessage(f"Deleted '{filename}' successfully.")
                self._refresh_file_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file:\n{e}")

        def _lock_device(self):
            if not self.client:
                return
            try:
                self.client.lock()
                QMessageBox.information(self, "Vault Locked", "Device memory purged and vault locked.")
                self._disconnect_client()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to lock vault:\n{e}")

        def _set_transfer_mode(self, in_progress: bool, message: str = ""):
            self.btn_connect.setEnabled(not in_progress)
            self.btn_refresh_files.setEnabled(not in_progress)
            self.btn_upload.setEnabled(not in_progress)
            self.btn_download.setEnabled(not in_progress)
            self.btn_delete.setEnabled(not in_progress)
            self.btn_lock.setEnabled(not in_progress)
            self.transfer_bar.setVisible(in_progress)
            self.transfer_bar.setValue(0)
            if in_progress:
                self.status_bar.showMessage(message)

        @Slot(int, int, str)
        def _on_transfer_progress(self, current: int, total: int, name: str):
            pct = int((current / total) * 100) if total > 0 else 0
            self.transfer_bar.setValue(pct)
            self.status_bar.showMessage(f"Transferring {name}: {current}/{total} chunks ({pct}%)")

        @Slot(bool, str)
        def _on_transfer_finished(self, success: bool, message: str):
            self._set_transfer_mode(False)
            if success:
                self.status_bar.showMessage(message)
                self._refresh_file_list()
                try:
                    st = self.client.get_status()
                    self._update_storage_ui(st)
                except Exception:
                    pass
            else:
                QMessageBox.critical(self, "Transfer Error", f"Transfer failed:\n{message}")

def run_gui():
    if not HAS_PYSIDE:
        print("PySide6 is not installed. To run the graphical interface, install it with:")
        print("    pip install PySide6 pyserial")
        print("You can still use the command-line interface:")
        print("    python -m desktop.vault_cli --help")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = VaultMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_gui()
