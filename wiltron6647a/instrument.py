"""Base abstractions for VISA instruments."""

from __future__ import annotations

from typing import Any, Callable, Optional
import re
import time

import pyvisa

try:
    from gpib_ctypes.Gpib import Gpib as _Gpib
except ImportError:
    _Gpib = None

Gpib = _Gpib


class GPIBWrapper:
    """
    Simple pyvisa-like wrapper for raw linux-gpib devices via gpib_ctypes.
    This implementation uses a BOARD-level descriptor for manual addressing
    and byte-pacing to support vintage instruments that are sensitive to timing.
    """

    def __init__(self, gpib_device: Any, write_termination: str, read_termination: str, timeout_ms: int, device_address: int = 0, board_device: Any = None) -> None:
        self.gpib = gpib_device  # This is expected to be a board descriptor
        self.write_termination = write_termination
        self.read_termination = read_termination
        self.timeout = timeout_ms / 1000.0
        self.device_address = device_address
        # board_device is ignored as self.gpib is the board device.

    def _send_cmd_bytes(self, cmd_bytes: bytes) -> None:
        if hasattr(self.gpib, "command"):
            self.gpib.command(cmd_bytes)

    def write(self, command: str) -> None:
        """Write command with manual addressing and byte-pacing."""
        command = command.rstrip()
        if self.write_termination and not command.endswith(self.write_termination):
            command += self.write_termination

        # Address board 0 as Talker (MTA 0 = 0x40) and device as Listener (MLA = 0x20 + addr)
        self._send_cmd_bytes(bytes([0x40, 0x20 + self.device_address]))

        # Send string bytes. ibwrt will automatically pace and assert EOI on the last byte.
        self.gpib.write(command.encode('ascii'))

        # Un-address the device (UNL = 0x3F) and the board (UNT = 0x5F)
        self._send_cmd_bytes(bytes([0x3F, 0x5F]))

    def read(self, size: int = 4096) -> str:
        """Read response with manual addressing."""
        # Address device to talk (MTA = 0x40 + addr) and board 0 to listen (MLA 0 = 0x20)
        self._send_cmd_bytes(bytes([0x40 + self.device_address, 0x20]))

        data = self.gpib.read(size)

        # Un-address the board (UNL = 0x3F) and the talker (UNT = 0x5F)
        self._send_cmd_bytes(bytes([0x3F, 0x5F]))

        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        if self.read_termination:
            data = data.rstrip("\r\n")
        return data

    def query(self, command: str) -> str:
        """Write command and read response."""
        self.write(command)
        time.sleep(0.5)  # Wait for instrument to process
        return self.read()

    def close(self) -> None:
        """Close GPIB device."""
        try:
            # Go to local before closing (GTL is command byte 0x01)
            self._send_cmd_bytes(bytes([0x01]))
            self.gpib.close()
        except Exception:
            pass

    def clear(self) -> None:
        """Clear device using SDC (Selected Device Clear)."""
        # Address the device to listen
        self._send_cmd_bytes(bytes([0x20 + self.device_address]))
        # Send SDC command byte (0x04)
        self._send_cmd_bytes(bytes([0x04]))
        # Un-address the device
        self._send_cmd_bytes(bytes([0x3F]))

    def assert_trigger(self) -> None:
        """Trigger device using GET (Group Execute Trigger)."""
        # GET is command byte 0x08
        self._send_cmd_bytes(bytes([0x08]))

    def read_stb(self) -> int:
        """Read status byte using serial poll."""
        try:
            # SPE (Serial Poll Enable = 0x18)
            # Address device as Talker (0x40 + addr) and board 0 as Listener (0x20)
            self._send_cmd_bytes(bytes([0x18, 0x40 + self.device_address, 0x20]))
            
            # Read exactly 1 byte
            stb_bytes = self.gpib.read(1)
            
            # SPD (Serial Poll Disable = 0x19)
            # Un-address board (UNL = 0x3F) and Talker (UNT = 0x5F)
            self._send_cmd_bytes(bytes([0x19, 0x3F, 0x5F]))
            
            if stb_bytes:
                return int(stb_bytes[0])
        except Exception:
            pass
        return 0


class Instrument:
    """Reusable base class for pyvisa-controlled instruments."""

    def __init__(
        self,
        resource_name: str,
        timeout_ms: int = 5000,
        write_termination: str = "",
        read_termination: str = "",
        logger: Optional[Callable[[str, Optional[str]], None]] = None,
        backend: str = "@py",
    ) -> None:
        self.resource_name = resource_name
        self.timeout_ms = timeout_ms
        self.write_termination = write_termination
        self.read_termination = read_termination
        self.logger = logger
        self.backend = backend
        self.rm: Optional[pyvisa.ResourceManager] = None
        self.resource: Optional[Any] = None

    def init(self) -> None:
        """Open and configure the VISA resource."""
        if self.resource is not None:
            return

        # Detect GPIB resource and use raw linux-gpib if pyvisa-py backend
        if "GPIB" in self.resource_name and self.backend == "@py":
            if Gpib is None:
                raise RuntimeError("gpib_ctypes required for GPIB with @py backend. Install: pip install gpib-ctypes")
            self._init_gpib()
        else:
            self._init_pyvisa()

    def _init_gpib(self) -> None:
        """Initialize raw linux-gpib device using a board-level descriptor for manual control."""
        # Parse VISA-style GPIB resource: GPIB{board}::{address}::INSTR
        match = re.match(r"GPIB(\d+)::(\d+)", self.resource_name, re.IGNORECASE)
        if not match:
            raise ValueError(f"Invalid GPIB resource format: {self.resource_name}")

        board = int(match.group(1))
        device = int(match.group(2))

        try:
            # Use a BOARD-level descriptor for manual addressing and timing control.
            ud = Gpib(board)

            # Send Interface Clear (IFC) to reset the bus and become controller-in-charge.
            if hasattr(ud, "interface_clear"):
                ud.interface_clear()
                time.sleep(0.1)  # Wait for devices to settle after IFC

            # Assert Remote Enable (REN) to allow remote control.
            if hasattr(ud, "remote_enable"):
                ud.remote_enable(1)

            # Configure End-Of-String (EOS) and End-Or-Identify (EOI) mode
            try:
                try:
                    import gpib
                except ImportError:
                    from gpib_ctypes import gpib  # type: ignore
                if hasattr(ud, "id"):
                    try:
                        gpib.ibeot(ud.id, 1)  # Always assert EOI on last byte
                    except AttributeError:
                        pass
                    if self.read_termination:
                        eos_mode = 0x1400 | ord(self.read_termination[-1])
                        try:
                            gpib.ibeos(ud.id, eos_mode)
                        except AttributeError:
                            pass
            except Exception as e:
                self._log(f"<GPIB_CONFIG_ERROR {e}>", None)

            # Set timeout on the raw GPIB device to prevent hanging on writes/reads
            # gpib_ctypes expects an integer enum for timeout, not a float in seconds.
            if hasattr(ud, "timeout"):
                t = self.timeout_ms
                if t <= 0: t_val = 0        # TNONE
                elif t <= 1: t_val = 5      # T1ms
                elif t <= 3: t_val = 6      # T3ms
                elif t <= 10: t_val = 7     # T10ms
                elif t <= 30: t_val = 8     # T30ms
                elif t <= 100: t_val = 9    # T100ms
                elif t <= 300: t_val = 10   # T300ms
                elif t <= 1000: t_val = 11  # T1s
                elif t <= 3000: t_val = 12  # T3s
                elif t <= 10000: t_val = 13 # T10s (5000ms will round up to 10s)
                elif t <= 30000: t_val = 14 # T30s
                elif t <= 100000: t_val = 15  # T100s
                elif t <= 300000: t_val = 16  # T300s
                else: t_val = 17            # T1000s
                ud.timeout = t_val
            self.resource = GPIBWrapper(ud, self.write_termination, self.read_termination, self.timeout_ms, device_address=device)
            self._log(f"<GPIB_OPEN board={board} pad={device} (MANUAL ADDR)>", None)
        except Exception as e:
            raise RuntimeError(
                f"Failed to open GPIB board {board} for address {device}: {e}"
            )

    def _init_pyvisa(self) -> None:
        """Initialize using pyvisa."""
        rm = pyvisa.ResourceManager(self.backend)
        res = rm.open_resource(self.resource_name)
        res.timeout = self.timeout_ms
        setattr(res, "write_termination", self.write_termination)
        setattr(res, "read_termination", self.read_termination)
        # Explicitly instruct PyVISA to assert EOI on the last byte
        setattr(res, "send_end", True)

        self.rm = rm
        self.resource = res

    def reset(self) -> None:
        """Reset the instrument state. Subclasses can override."""
        self.write("*RST")

    def deinit(self) -> None:
        """Close the instrument and VISA resource manager."""
        if self.resource is not None:
            try:
                self.resource.close()
            except Exception:
                pass
            self.resource = None

        if self.rm is not None:
            try:
                self.rm.close()
            except Exception:
                pass
            self.rm = None

    def write(self, command: str) -> None:
        """Send a command string to the instrument."""
        command = command.rstrip()
        res = self._resource()
        res.write(command)
        self._log(command, None)

    def read(self) -> str:
        """Read a response from the instrument."""
        res = self._resource()
        return str(res.read())

    def query(self, command: str) -> str:
        """Send command and read response in one round trip."""
        command = command.rstrip()
        res = self._resource()
        response = str(res.query(command))
        self._log(command, response)
        return response

    def clear(self) -> None:
        """Issue VISA clear on the connected resource."""
        res = self._resource()
        res.clear()
        self._log("<VISA_CLEAR>", None)

    def assert_trigger(self) -> None:
        """Issue a VISA trigger if supported by the backend."""
        res = self._resource()
        res.assert_trigger()
        self._log("<VISA_TRIGGER>", None)

    def read_status_byte(self) -> int:
        """Read serial poll status byte if supported."""
        res = self._resource()
        value = int(res.read_stb())
        self._log("<READ_STB>", str(value))
        return value

    def _resource(self) -> Any:
        self._require_connected()
        assert self.resource is not None
        return self.resource

    def _require_connected(self) -> None:
        if self.resource is None:
            raise RuntimeError("Instrument is not initialized. Call init() first.")

    def _log(self, command: str, response: Optional[str]) -> None:
        if self.logger:
            self.logger(command, response)
