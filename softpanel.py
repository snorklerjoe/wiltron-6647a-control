"""PyQt softpanel for Wiltron 6647A control."""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Optional

import pyvisa
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from wiltron6647a import Wiltron6647A


COMMAND_DESCRIPTIONS = {
    "DC": "Device clear",
    "SDC": "Selected device clear",
    "GTL": "Go to local",
    "GET": "Group execute trigger",
    "IFC": "Interface clear",
    "LLO": "Local lockout",
    "REM": "Remote enable",
    "SPE": "Serial poll enable",
    "SPD": "Serial poll disable",
    "PPC": "Parallel poll configure",
    "PPE": "Parallel poll enable",
    "PPU": "Parallel poll unconfigure",
    "PPD": "Parallel poll disable",
    "F0": "Set F0 with GH/MH terminator",
    "F1": "Set F1 with GH/MH terminator",
    "F2": "Set F2 with GH/MH terminator",
    "M1": "Set M1 with GH/MH terminator",
    "M2": "Set M2 with GH/MH terminator",
    "DLF": "Set delta-F with GH/MH terminator",
    "SWT": "Set sweep time with SEC/MS",
    "LVL": "Set RF level with DB/DM",
    "GH": "GHz terminator",
    "MH": "MHz terminator",
    "SEC": "Seconds terminator",
    "MS": "Milliseconds terminator",
    "DB": "dB terminator",
    "DM": "dBm terminator",
    "SH": "Shift",
    "CLR": "Clear entry",
    "FUL": "Full sweep",
    "FF": "F1-F2 sweep",
    "MM": "M1-M2 sweep",
    "DF0": "delta-F around F0",
    "DF1": "delta-F around F1",
    "CF0": "CW F0",
    "CF1": "CW F1",
    "CF2": "CW F2",
    "CM1": "CW M1",
    "CM2": "CW M2",
    "FVS###E": "Frequency vernier increase",
    "FVS-###E": "Frequency vernier decrease",
    "FV0": "Frequency vernier off",
    "AUT": "Auto trigger",
    "LIN": "Line trigger",
    "EXT": "External trigger",
    "TRS": "Single sweep trigger",
    "MAN": "Manual sweep",
    "VM1": "Video marker on",
    "RM1": "RF marker on",
    "IM1": "Intensity marker on",
    "MKO": "Markers off",
    "IL1": "Internal leveling",
    "DL1": "Detector leveling",
    "PL1": "Power meter leveling",
    "LV0": "Leveling off",
    "RF0": "RF off",
    "RF1": "RF on",
    "RT0": "Retrace RF off",
    "RT1": "Retrace RF on",
    "TST": "Self test",
    "RST": "Reset",
    "FM0": "FM/phase-lock off",
    "FM1": "FM/phase-lock on",
    "STP": "Step sweep mode",
    "STS#E": "Step select",
    "SIZ#E": "Increment size",
    "N": "Next step",
    "GTS": "GET triggers sweep",
    "GTU": "GET executes UP",
    "GTD": "GET executes DN",
    "GTN": "GET executes N",
    "SQ1": "Enable SRQ",
    "SQ0": "Disable SRQ",
    "DW1": "Dwell at marker on",
    "DW0": "Dwell at marker off",
    "ES1": "End-of-sweep SRQ on",
    "ES0": "End-of-sweep SRQ off",
    "UL1": "Unleveled SRQ on",
    "UL0": "Unleveled SRQ off",
    "PE1": "Parameter-entry-error SRQ on",
    "PE0": "Parameter-entry-error SRQ off",
    "SE1": "Syntax-error SRQ on",
    "SE0": "Syntax-error SRQ off",
    "OI": "Identify instrument",
    "ODF": "Output delta-F",
    "OF0": "Output F0",
    "OF1": "Output F1",
    "OF2": "Output F2",
    "OFL": "Output low-end frequency",
    "OFH": "Output high-end frequency",
    "OM1": "Output M1",
    "OM2": "Output M2",
    "OLV": "Output level",
    "OSB": "Output status byte",
    "OST": "Output sweep time",
    "CNT": "Continue sweep",
    "DS0": "Displays off",
    "DS1": "Displays on",
    "DN": "Decrement parameter",
    "UP": "Increment parameter",
    "FL0": "CW filter off",
    "FL1": "CW filter on",
    "RL": "Return to local",
    "SAV": "Save settings",
    "RCL": "Recall settings",
    "CS0": "Horizontal output CW off",
    "CS1": "Horizontal output CW on",
    "RSS": "Reset sweep",
}


class SoftpanelWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Wiltron 6647A Softpanel")
        self.resize(1200, 820)

        self.instrument: Optional[Wiltron6647A] = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(5000)
        self.log_output.setPlaceholderText("Commands and responses appear here.")
        self.log_output.setMinimumHeight(180)
        root.addWidget(QLabel("Command / Response Log"))
        root.addWidget(self.log_output, stretch=0)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self._build_connection_tab()
        self._build_sweep_tab()
        self._build_step_srq_tab()
        self._build_output_misc_tab()
        self._build_command_browser_tab()

        self.refresh_resources()

    def _build_connection_tab(self) -> None:
        tab = QWidget()
        self.tabs.addTab(tab, "Connection")
        layout = QVBoxLayout(tab)

        conn_group = QGroupBox("VISA Connection")
        conn_layout = QGridLayout(conn_group)

        self.resource_combo = QComboBox()
        self.resource_combo.setEditable(True)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_resources)
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self.connect_instrument)
        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.clicked.connect(self.disconnect_instrument)

        conn_layout.addWidget(QLabel("Resource"), 0, 0)
        conn_layout.addWidget(self.resource_combo, 0, 1, 1, 3)
        conn_layout.addWidget(refresh_btn, 1, 0)
        conn_layout.addWidget(connect_btn, 1, 1)
        conn_layout.addWidget(disconnect_btn, 1, 2)

        layout.addWidget(conn_group)

        bus_group = QGroupBox("IEEE-488 Bus Actions")
        bus_layout = QGridLayout(bus_group)

        buttons = [
            ("DC", lambda: self._send_bus("DC")),
            ("SDC", lambda: self._send_bus("SDC")),
            ("GTL", lambda: self._send_bus("GTL")),
            ("GET", lambda: self._send_bus("GET")),
            ("IFC", lambda: self._send_bus("IFC")),
            ("LLO", lambda: self._send_bus("LLO")),
            ("REM", lambda: self._send_bus("REM")),
            ("SPE", lambda: self._send_bus("SPE")),
            ("SPD", lambda: self._send_bus("SPD")),
            ("PPC", lambda: self._send_bus("PPC")),
            ("PPE", lambda: self._send_bus("PPE")),
            ("PPU", lambda: self._send_bus("PPU")),
            ("PPD", lambda: self._send_bus("PPD")),
        ]
        for idx, (name, callback) in enumerate(buttons):
            b = QPushButton(name)
            b.clicked.connect(callback)
            bus_layout.addWidget(b, idx // 5, idx % 5)

        layout.addWidget(bus_group)

        util_row = QHBoxLayout()
        rst_btn = QPushButton("RST")
        rst_btn.clicked.connect(lambda: self._run(lambda i: i.reset_command()))
        id_btn = QPushButton("OI")
        id_btn.clicked.connect(lambda: self._run(lambda i: i.output_identify_instrument(), expect_response=True))
        util_row.addWidget(rst_btn)
        util_row.addWidget(id_btn)
        util_row.addStretch(1)
        layout.addLayout(util_row)

        layout.addStretch(1)

    def _build_sweep_tab(self) -> None:
        tab = QWidget()
        self.tabs.addTab(tab, "Sweep / RF")
        layout = QVBoxLayout(tab)

        param_group = QGroupBox("Frequency, Time, and Level")
        param_form = QFormLayout(param_group)

        self.f0_spin = self._make_freq_spin()
        self.f0_unit = self._make_unit_combo(["GH", "MH"])
        self.f1_spin = self._make_freq_spin()
        self.f1_unit = self._make_unit_combo(["GH", "MH"])
        self.f2_spin = self._make_freq_spin()
        self.f2_unit = self._make_unit_combo(["GH", "MH"])
        self.m1_spin = self._make_freq_spin()
        self.m1_unit = self._make_unit_combo(["GH", "MH"])
        self.m2_spin = self._make_freq_spin()
        self.m2_unit = self._make_unit_combo(["GH", "MH"])
        self.dlf_spin = self._make_freq_spin()
        self.dlf_unit = self._make_unit_combo(["GH", "MH"])

        self.swt_spin = self._make_time_spin()
        self.swt_unit = self._make_unit_combo(["MS", "SEC"])
        self.lvl_spin = self._make_level_spin()
        self.lvl_unit = self._make_unit_combo(["DM", "DB"])

        param_form.addRow("F0", self._param_row(self.f0_spin, self.f0_unit, lambda: self._run(lambda i: i.set_f0(self.f0_spin.value(), self.f0_unit.currentText()))))
        param_form.addRow("F1", self._param_row(self.f1_spin, self.f1_unit, lambda: self._run(lambda i: i.set_f1(self.f1_spin.value(), self.f1_unit.currentText()))))
        param_form.addRow("F2", self._param_row(self.f2_spin, self.f2_unit, lambda: self._run(lambda i: i.set_f2(self.f2_spin.value(), self.f2_unit.currentText()))))
        param_form.addRow("M1", self._param_row(self.m1_spin, self.m1_unit, lambda: self._run(lambda i: i.set_m1(self.m1_spin.value(), self.m1_unit.currentText()))))
        param_form.addRow("M2", self._param_row(self.m2_spin, self.m2_unit, lambda: self._run(lambda i: i.set_m2(self.m2_spin.value(), self.m2_unit.currentText()))))
        param_form.addRow("delta-F", self._param_row(self.dlf_spin, self.dlf_unit, lambda: self._run(lambda i: i.set_delta_f(self.dlf_spin.value(), self.dlf_unit.currentText()))))
        param_form.addRow("Sweep Time", self._param_row(self.swt_spin, self.swt_unit, lambda: self._run(lambda i: i.set_sweep_time(self.swt_spin.value(), self.swt_unit.currentText()))))
        param_form.addRow("RF Level", self._param_row(self.lvl_spin, self.lvl_unit, lambda: self._run(lambda i: i.set_rf_level(self.lvl_spin.value(), self.lvl_unit.currentText()))))

        layout.addWidget(param_group)

        modes_group = QGroupBox("Sweep Modes")
        modes_layout = QGridLayout(modes_group)
        sweep_mode_cmds = ["FUL", "FF", "MM", "DF0", "DF1", "CF0", "CF1", "CF2", "CM1", "CM2"]
        for idx, cmd in enumerate(sweep_mode_cmds):
            b = QPushButton(cmd)
            b.clicked.connect(lambda _=False, c=cmd: self._run(lambda i: i.send(c)))
            modes_layout.addWidget(b, idx // 5, idx % 5)
        layout.addWidget(modes_group)

        trigger_group = QGroupBox("Trigger and Markers")
        trigger_layout = QGridLayout(trigger_group)
        trigger_cmds = ["AUT", "LIN", "EXT", "TRS", "MAN", "VM1", "RM1", "IM1", "MKO"]
        for idx, cmd in enumerate(trigger_cmds):
            b = QPushButton(cmd)
            b.clicked.connect(lambda _=False, c=cmd: self._run(lambda i: i.send(c)))
            trigger_layout.addWidget(b, idx // 5, idx % 5)
        layout.addWidget(trigger_group)

        rf_group = QGroupBox("RF and Leveling")
        rf_layout = QGridLayout(rf_group)
        rf_cmds = ["IL1", "DL1", "PL1", "LV0", "RF0", "RF1", "RT0", "RT1", "FM0", "FM1", "TST"]
        for idx, cmd in enumerate(rf_cmds):
            b = QPushButton(cmd)
            b.clicked.connect(lambda _=False, c=cmd: self._run(lambda i: i.send(c)))
            rf_layout.addWidget(b, idx // 6, idx % 6)
        layout.addWidget(rf_group)
        layout.addStretch(1)

    def _build_step_srq_tab(self) -> None:
        tab = QWidget()
        self.tabs.addTab(tab, "Step / SRQ")
        layout = QVBoxLayout(tab)

        step_group = QGroupBox("Digital Step Sweep")
        step_layout = QGridLayout(step_group)

        self.step_select_spin = QSpinBox()
        self.step_select_spin.setRange(0, 4095)
        self.step_size_spin = QSpinBox()
        self.step_size_spin.setRange(1, 9999)

        step_layout.addWidget(QLabel("Step Index (STS)"), 0, 0)
        step_layout.addWidget(self.step_select_spin, 0, 1)
        set_sts_btn = QPushButton("Apply STS")
        set_sts_btn.clicked.connect(lambda: self._run(lambda i: i.step_select(self.step_select_spin.value())))
        step_layout.addWidget(set_sts_btn, 0, 2)

        step_layout.addWidget(QLabel("Increment Size (SIZ)"), 1, 0)
        step_layout.addWidget(self.step_size_spin, 1, 1)
        set_siz_btn = QPushButton("Apply SIZ")
        set_siz_btn.clicked.connect(lambda: self._run(lambda i: i.increment_size(self.step_size_spin.value())))
        step_layout.addWidget(set_siz_btn, 1, 2)

        for idx, cmd in enumerate(["STP", "N", "UP", "DN"]):
            b = QPushButton(cmd)
            b.clicked.connect(lambda _=False, c=cmd: self._run(lambda i: i.send(c)))
            step_layout.addWidget(b, 2, idx)

        layout.addWidget(step_group)

        get_group = QGroupBox("GET Mode")
        get_layout = QGridLayout(get_group)
        for idx, cmd in enumerate(["GTS", "GTU", "GTD", "GTN"]):
            b = QPushButton(cmd)
            b.clicked.connect(lambda _=False, c=cmd: self._run(lambda i: i.send(c)))
            get_layout.addWidget(b, 0, idx)
        layout.addWidget(get_group)

        srq_group = QGroupBox("SRQ Modes")
        srq_layout = QGridLayout(srq_group)
        srq_cmds = ["SQ1", "SQ0", "DW1", "DW0", "ES1", "ES0", "UL1", "UL0", "PE1", "PE0", "SE1", "SE0", "CNT"]
        for idx, cmd in enumerate(srq_cmds):
            b = QPushButton(cmd)
            b.clicked.connect(lambda _=False, c=cmd: self._run(lambda i: i.send(c)))
            srq_layout.addWidget(b, idx // 5, idx % 5)
        layout.addWidget(srq_group)
        layout.addStretch(1)

    def _build_output_misc_tab(self) -> None:
        tab = QWidget()
        self.tabs.addTab(tab, "Output / Misc")
        layout = QVBoxLayout(tab)

        out_group = QGroupBox("Output Queries")
        out_layout = QGridLayout(out_group)
        output_cmds = ["OI", "ODF", "OF0", "OF1", "OF2", "OFL", "OFH", "OM1", "OM2", "OLV", "OSB", "OST", "SAV"]
        for idx, cmd in enumerate(output_cmds):
            b = QPushButton(cmd)
            b.clicked.connect(lambda _=False, c=cmd: self._run(lambda i: i.send_query(c), expect_response=True))
            out_layout.addWidget(b, idx // 5, idx % 5)
        layout.addWidget(out_group)

        misc_group = QGroupBox("Misc")
        misc_layout = QGridLayout(misc_group)
        misc_cmds = ["DS0", "DS1", "FL0", "FL1", "RL", "CS0", "CS1", "RSS", "CLR", "SH", "FV0"]
        for idx, cmd in enumerate(misc_cmds):
            b = QPushButton(cmd)
            b.clicked.connect(lambda _=False, c=cmd: self._run(lambda i: i.send(c)))
            misc_layout.addWidget(b, idx // 6, idx % 6)
        layout.addWidget(misc_group)

        recall_group = QGroupBox("Recall Settings")
        recall_layout = QHBoxLayout(recall_group)
        self.recall_input = QLineEdit()
        self.recall_input.setPlaceholderText("Paste ASCII state string returned by SAV")
        recall_btn = QPushButton("Send RCL")
        recall_btn.clicked.connect(self.send_recall)
        recall_layout.addWidget(self.recall_input)
        recall_layout.addWidget(recall_btn)
        layout.addWidget(recall_group)

        raw_group = QGroupBox("Raw Command")
        raw_layout = QHBoxLayout(raw_group)
        self.raw_command_input = QLineEdit()
        self.raw_command_input.setPlaceholderText("Enter raw command string, e.g. DF0 F02GH DLF10MH AUT")
        raw_send = QPushButton("Send")
        raw_send.clicked.connect(self.send_raw_command)
        raw_query = QPushButton("Query")
        raw_query.clicked.connect(self.query_raw_command)
        raw_layout.addWidget(self.raw_command_input)
        raw_layout.addWidget(raw_send)
        raw_layout.addWidget(raw_query)
        layout.addWidget(raw_group)
        layout.addStretch(1)

    def _build_command_browser_tab(self) -> None:
        tab = QWidget()
        self.tabs.addTab(tab, "Command Browser")
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Every command listed in the summary is available here. Select one and send/query."))
        self.command_list = QListWidget()
        for cmd, desc in COMMAND_DESCRIPTIONS.items():
            item = QListWidgetItem(f"{cmd} - {desc}")
            item.setData(Qt.ItemDataRole.UserRole, cmd)
            self.command_list.addItem(item)
        layout.addWidget(self.command_list, stretch=1)

        row = QHBoxLayout()
        send_btn = QPushButton("Send Selected")
        send_btn.clicked.connect(self.send_selected_command)
        query_btn = QPushButton("Query Selected")
        query_btn.clicked.connect(self.query_selected_command)
        row.addWidget(send_btn)
        row.addWidget(query_btn)
        row.addStretch(1)
        layout.addLayout(row)

    @staticmethod
    def _make_unit_combo(values: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(values)
        return combo

    @staticmethod
    def _make_freq_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(6)
        spin.setRange(0.0, 99.999999)
        spin.setValue(1.0)
        return spin

    @staticmethod
    def _make_time_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(3)
        spin.setRange(0.0, 99999.999)
        spin.setValue(100.0)
        return spin

    @staticmethod
    def _make_level_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setRange(-140.0, 40.0)
        spin.setValue(0.0)
        return spin

    @staticmethod
    def _param_row(spin: QDoubleSpinBox, unit_combo: QComboBox, callback) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("Set")
        btn.clicked.connect(callback)
        row.addWidget(spin)
        row.addWidget(unit_combo)
        row.addWidget(btn)
        row.addStretch(1)
        return widget

    def refresh_resources(self) -> None:
        try:
            rm = pyvisa.ResourceManager('@py')
            resources = list(rm.list_resources())
            rm.close()
        except Exception as exc:
            resources = []
            self._log_text(f"Resource scan failed: {exc}")

        current = self.resource_combo.currentText().strip()
        self.resource_combo.clear()
        self.resource_combo.addItems(resources)
        if current:
            self.resource_combo.setEditText(current)

    def connect_instrument(self) -> None:
        resource = self.resource_combo.currentText().strip()
        if not resource:
            QMessageBox.warning(self, "Missing Resource", "Enter or select a VISA resource name.")
            return

        self.disconnect_instrument()
        try:
            inst = Wiltron6647A(resource, logger=self._log_io, backend="@py")
            inst.init()
            self.instrument = inst
            self.status_bar.showMessage(f"Connected: {resource}")
            self._log_text(f"Connected to {resource}")
        except Exception as exc:
            self.instrument = None
            QMessageBox.critical(self, "Connection Failed", str(exc))

    def disconnect_instrument(self) -> None:
        if self.instrument is None:
            return

        try:
            self.instrument.deinit()
        finally:
            self._log_text("Disconnected")
            self.status_bar.showMessage("Disconnected")
            self.instrument = None

    def send_raw_command(self) -> None:
        cmd = self.raw_command_input.text().strip()
        if not cmd:
            return
        self._run(lambda i: i.send(cmd))

    def query_raw_command(self) -> None:
        cmd = self.raw_command_input.text().strip()
        if not cmd:
            return
        self._run(lambda i: i.send_query(cmd), expect_response=True)

    def send_recall(self) -> None:
        state = self.recall_input.text().strip()
        if not state:
            QMessageBox.warning(self, "Missing State", "Paste the SAV string first.")
            return
        self._run(lambda i: i.recall_settings(state))

    def send_selected_command(self) -> None:
        item = self.command_list.currentItem()
        if item is None:
            return
        token = str(item.data(Qt.ItemDataRole.UserRole))
        if "#" in token:
            QMessageBox.information(self, "Template Command", f"{token} is a template command. Use the specific controls or raw command field.")
            return
        self._send_bus(token)

    def query_selected_command(self) -> None:
        item = self.command_list.currentItem()
        if item is None:
            return
        token = str(item.data(Qt.ItemDataRole.UserRole))
        if "#" in token:
            QMessageBox.information(self, "Template Command", f"{token} is a template command. Use the specific controls or raw command field.")
            return

        if token in {"SPE", "SPD"}:
            self._send_bus(token)
            return

        self._run(lambda i: i.send_query(token), expect_response=True)

    def _send_bus(self, token: str) -> None:
        if token in {"DC", "SDC"}:
            self._run(lambda i: i.device_clear_dc())
            return
        if token == "GTL":
            self._run(lambda i: i.go_to_local_gtl())
            return
        if token == "GET":
            self._run(lambda i: i.group_execute_trigger_get())
            return
        if token == "IFC":
            self._run(lambda i: i.interface_clear_ifc())
            return
        if token == "LLO":
            self._run(lambda i: i.local_lockout_llo())
            return
        if token == "REM":
            self._run(lambda i: i.remote_enable_rem())
            return
        if token == "SPE":
            self._run(lambda i: i.serial_poll_spe(), expect_response=True)
            return
        if token == "SPD":
            self._run(lambda i: i.serial_poll_spd(), expect_response=True)
            return

        self._run(lambda i: i.send(token))

    def _run(self, action, expect_response: bool = False) -> None:
        if self.instrument is None:
            QMessageBox.warning(self, "Not Connected", "Connect to a VISA resource first.")
            return

        try:
            result = action(self.instrument)
            if expect_response and result is not None:
                self.status_bar.showMessage(f"Response: {result}", 6000)
        except Exception as exc:
            QMessageBox.critical(self, "Instrument Error", str(exc))
            self.status_bar.showMessage("Command failed", 4000)

    def _log_io(self, command: str, response: Optional[str]) -> None:
        if response is None:
            self._log_text(f"TX: {command}")
        else:
            self._log_text(f"TX: {command}")
            self._log_text(f"RX: {response}")

    def _log_text(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.appendPlainText(f"[{stamp}] {text}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.disconnect_instrument()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    window = SoftpanelWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
