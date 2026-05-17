"""Wiltron 6647A command wrapper."""

from __future__ import annotations

from typing import Callable, Literal, Optional

from pyvisa import constants as visa_constants

from .instrument import Instrument

FrequencyUnit = Literal["GH", "MH"]
TimeUnit = Literal["SEC", "MS"]
LevelUnit = Literal["DB", "DM"]


class Wiltron6647A(Instrument):
    """High-level command methods for the Wiltron 6647A sweep generator."""

    def __init__(
        self,
        resource_name: str,
        timeout_ms: int = 5000,
        write_termination: str = "\r\n",
        read_termination: str = "\n",
        logger: Optional[Callable[[str, Optional[str]], None]] = None,
        backend: str = "@py",
    ) -> None:
        super().__init__(
            resource_name=resource_name,
            timeout_ms=timeout_ms,
            write_termination=write_termination,
            read_termination=read_termination,
            logger=logger,
            backend=backend,
        )

    def reset(self) -> None:
        # RST is the device-native reset command from the programming guide.
        self.write("RST")

    @staticmethod
    def _ren_op(*names: str):
        enum_cls = visa_constants.RENLineOperation
        for name in names:
            if hasattr(enum_cls, name):
                return getattr(enum_cls, name)
            upper = name.upper()
            if hasattr(enum_cls, upper):
                return getattr(enum_cls, upper)
        raise AttributeError(f"REN operation not found for candidates: {names}")

    # ---------------------------------------------------------------------
    # Generic helpers
    # ---------------------------------------------------------------------
    def send(self, command: str) -> None:
        self.write(command)

    def send_query(self, command: str) -> str:
        return self.query(command)

    @staticmethod
    def _format_numeric(value: float | int) -> str:
        if isinstance(value, int):
            return str(value)
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text if text else "0"

    def _set_freq_param(self, prefix: str, value: float | int, unit: FrequencyUnit) -> None:
        self.write(f"{prefix}{self._format_numeric(value)}{unit}")

    def _set_time_param(self, prefix: str, value: float | int, unit: TimeUnit) -> None:
        self.write(f"{prefix}{self._format_numeric(value)}{unit}")

    def _set_level_param(self, prefix: str, value: float | int, unit: LevelUnit) -> None:
        self.write(f"{prefix}{self._format_numeric(value)}{unit}")

    # ---------------------------------------------------------------------
    # IEEE 488 bus messages (best-effort depending on VISA backend support)
    # ---------------------------------------------------------------------
    def device_clear_dc(self) -> None:
        self.clear()

    def device_clear_sdc(self) -> None:
        self.clear()

    def go_to_local_gtl(self) -> None:
        if self.resource is not None and hasattr(self.resource, "control_ren"):
            op = self._ren_op("deassert_gtl", "vi_gpib_ren_deassert_gtl")
            self.resource.control_ren(op)
            self._log("<GTL>", None)
            return
        self.write("GTL")

    def group_execute_trigger_get(self) -> None:
        self.assert_trigger()

    def interface_clear_ifc(self) -> None:
        # Some VISA backends expose IFC only at controller level; fallback to token write.
        try:
            if self.resource is not None and hasattr(self.resource, "send_ifc"):
                self.resource.send_ifc()
                self._log("<IFC>", None)
                return
        except Exception:
            pass
        self.write("IFC")

    def local_lockout_llo(self) -> None:
        if self.resource is not None and hasattr(self.resource, "control_ren"):
            op = self._ren_op("assert_address_llo", "vi_gpib_ren_assert_address_llo")
            self.resource.control_ren(op)
            self._log("<LLO>", None)
            return
        self.write("LLO")

    def remote_enable_rem(self) -> None:
        if self.resource is not None and hasattr(self.resource, "control_ren"):
            op = self._ren_op("assert_address", "vi_gpib_ren_assert_address")
            self.resource.control_ren(op)
            self._log("<REM>", None)
            return
        self.write("REM")

    def serial_poll_spe(self) -> int:
        return self.read_status_byte()

    def serial_poll_spd(self) -> int:
        return self.read_status_byte()

    def parallel_poll_ppc(self) -> None:
        self.write("PPC")

    def parallel_poll_ppe(self) -> None:
        self.write("PPE")

    def parallel_poll_ppu(self) -> None:
        self.write("PPU")

    def parallel_poll_ppd(self) -> None:
        self.write("PPD")

    # ---------------------------------------------------------------------
    # Front-panel-control related commands
    # ---------------------------------------------------------------------
    def set_f0(self, value: float | int, unit: FrequencyUnit = "GH") -> None:
        self._set_freq_param("F0", value, unit)

    def set_f1(self, value: float | int, unit: FrequencyUnit = "GH") -> None:
        self._set_freq_param("F1", value, unit)

    def set_f2(self, value: float | int, unit: FrequencyUnit = "GH") -> None:
        self._set_freq_param("F2", value, unit)

    def set_m1(self, value: float | int, unit: FrequencyUnit = "GH") -> None:
        self._set_freq_param("M1", value, unit)

    def set_m2(self, value: float | int, unit: FrequencyUnit = "GH") -> None:
        self._set_freq_param("M2", value, unit)

    def set_delta_f(self, value: float | int, unit: FrequencyUnit = "GH") -> None:
        self._set_freq_param("DLF", value, unit)

    def set_sweep_time(self, value: float | int, unit: TimeUnit = "MS") -> None:
        self._set_time_param("SWT", value, unit)

    def set_rf_level(self, value: float | int, unit: LevelUnit = "DM") -> None:
        self._set_level_param("LVL", value, unit)

    def gh(self) -> None:
        self.write("GH")

    def mh(self) -> None:
        self.write("MH")

    def sec(self) -> None:
        self.write("SEC")

    def ms(self) -> None:
        self.write("MS")

    def db(self) -> None:
        self.write("DB")

    def dm(self) -> None:
        self.write("DM")

    def shift(self) -> None:
        self.write("SH")

    def clear_entry(self) -> None:
        self.write("CLR")

    def full_sweep(self) -> None:
        self.write("FUL")

    def f1_f2_sweep(self) -> None:
        self.write("FF")

    def m1_m2_sweep(self) -> None:
        self.write("MM")

    def delta_f_f0_sweep(self) -> None:
        self.write("DF0")

    def delta_f_f1_sweep(self) -> None:
        self.write("DF1")

    def cw_f0(self) -> None:
        self.write("CF0")

    def cw_f1(self) -> None:
        self.write("CF1")

    def cw_f2(self) -> None:
        self.write("CF2")

    def cw_m1(self) -> None:
        self.write("CM1")

    def cw_m2(self) -> None:
        self.write("CM2")

    def freq_vernier_increase(self, correction_steps: int) -> None:
        self.write(f"FVS{abs(correction_steps):03d}E")

    def freq_vernier_decrease(self, correction_steps: int) -> None:
        self.write(f"FVS-{abs(correction_steps):03d}E")

    def freq_vernier_off(self) -> None:
        self.write("FV0")

    def auto_trigger(self) -> None:
        self.write("AUT")

    def line_trigger(self) -> None:
        self.write("LIN")

    def external_trigger(self) -> None:
        self.write("EXT")

    def trigger_single_sweep(self) -> None:
        self.write("TRS")

    def manual_sweep(self) -> None:
        self.write("MAN")

    def video_marker_on(self) -> None:
        self.write("VM1")

    def rf_marker_on(self) -> None:
        self.write("RM1")

    def intensity_marker_on(self) -> None:
        self.write("IM1")

    def markers_off(self) -> None:
        self.write("MKO")

    def internal_leveling(self) -> None:
        self.write("IL1")

    def detector_leveling(self) -> None:
        self.write("DL1")

    def power_meter_leveling(self) -> None:
        self.write("PL1")

    def leveling_off(self) -> None:
        self.write("LV0")

    def rf_off(self) -> None:
        self.write("RF0")

    def rf_on(self) -> None:
        self.write("RF1")

    def retrace_rf_off(self) -> None:
        self.write("RT0")

    def retrace_rf_on(self) -> None:
        self.write("RT1")

    def self_test(self) -> None:
        self.write("TST")

    def reset_command(self) -> None:
        self.write("RST")

    def fm_phase_lock_off(self) -> None:
        self.write("FM0")

    def fm_phase_lock_on(self) -> None:
        self.write("FM1")

    # ---------------------------------------------------------------------
    # Digital step sweep commands
    # ---------------------------------------------------------------------
    def step_sweep_mode(self) -> None:
        self.write("STP")

    def step_select(self, step_index: int) -> None:
        if step_index == 0:
            self.write("STSE")
            return
        self.write(f"STS{step_index}E")

    def increment_size(self, step_count: int) -> None:
        self.write(f"SIZ{int(step_count)}E")

    def next_step(self) -> None:
        self.write("N")

    # ---------------------------------------------------------------------
    # Group Execute Trigger mode commands
    # ---------------------------------------------------------------------
    def get_trigger_sweep_mode(self) -> None:
        self.write("GTS")

    def get_execute_up_mode(self) -> None:
        self.write("GTU")

    def get_execute_dn_mode(self) -> None:
        self.write("GTD")

    def get_execute_n_mode(self) -> None:
        self.write("GTN")

    # ---------------------------------------------------------------------
    # Service request commands
    # ---------------------------------------------------------------------
    def enable_srq(self) -> None:
        self.write("SQ1")

    def disable_srq(self) -> None:
        self.write("SQ0")

    def dwell_at_marker_on(self) -> None:
        self.write("DW1")

    def dwell_at_marker_off(self) -> None:
        self.write("DW0")

    def end_of_sweep_mode_on(self) -> None:
        self.write("ES1")

    def end_of_sweep_mode_off(self) -> None:
        self.write("ES0")

    def unleveled_condition_on(self) -> None:
        self.write("UL1")

    def unleveled_condition_off(self) -> None:
        self.write("UL0")

    def param_entry_error_on(self) -> None:
        self.write("PE1")

    def param_entry_error_off(self) -> None:
        self.write("PE0")

    def syntax_error_mode_on(self) -> None:
        self.write("SE1")

    def syntax_error_mode_off(self) -> None:
        self.write("SE0")

    # ---------------------------------------------------------------------
    # Output commands
    # ---------------------------------------------------------------------
    def output_identify_instrument(self) -> str:
        return self.query("OI")

    def output_delta_f(self) -> str:
        return self.query("ODF")

    def output_f0(self) -> str:
        return self.query("OF0")

    def output_f1(self) -> str:
        return self.query("OF1")

    def output_f2(self) -> str:
        return self.query("OF2")

    def output_low_end_freq(self) -> str:
        return self.query("OFL")

    def output_high_end_freq(self) -> str:
        return self.query("OFH")

    def output_m1(self) -> str:
        return self.query("OM1")

    def output_m2(self) -> str:
        return self.query("OM2")

    def output_power_level(self) -> str:
        return self.query("OLV")

    def output_status_byte(self) -> str:
        return self.query("OSB")

    def output_sweep_time(self) -> str:
        return self.query("OST")

    # ---------------------------------------------------------------------
    # Miscellaneous commands
    # ---------------------------------------------------------------------
    def continue_sweep(self) -> None:
        self.write("CNT")

    def displays_off(self) -> None:
        self.write("DS0")

    def displays_on(self) -> None:
        self.write("DS1")

    def decrement_parameter(self, active_parameter: Optional[str] = None) -> None:
        if active_parameter:
            self.write(f"{active_parameter} DN")
            return
        self.write("DN")

    def increment_parameter(self, active_parameter: Optional[str] = None) -> None:
        if active_parameter:
            self.write(f"{active_parameter} UP")
            return
        self.write("UP")

    def cw_filter_off(self) -> None:
        self.write("FL0")

    def cw_filter_on(self) -> None:
        self.write("FL1")

    def return_to_local(self) -> None:
        self.write("RL")

    def save_settings(self) -> str:
        return self.query("SAV")

    def recall_settings(self, saved_state_ascii: str) -> None:
        self.write(f"RCL{saved_state_ascii}")

    def horiz_output_cw_off(self) -> None:
        self.write("CS0")

    def horiz_output_cw_on(self) -> None:
        self.write("CS1")

    def reset_sweep(self) -> None:
        self.write("RSS")
