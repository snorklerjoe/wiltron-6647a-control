"""Base abstractions for VISA instruments."""

from __future__ import annotations

from typing import Any, Callable, Optional
import re
import time

import pyvisa


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

        self._init_pyvisa()

    def _init_pyvisa(self) -> None:
        """Initialize using pyvisa."""
        rm = pyvisa.ResourceManager(self.backend)
        res = rm.open_resource(self.resource_name)
        res.timeout = self.timeout_ms
        setattr(res, "write_termination", self.write_termination)
        setattr(res, "read_termination", self.read_termination)
        
        # Explicitly instruct PyVISA to assert EOI on the last byte
        setattr(res, "send_end", True)
        # Delay half a second between writing and reading in a query to allow the Wiltron to process!
        setattr(res, "query_delay", 0.5)

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
