"""Mock GPIB device for testing without real hardware."""

from __future__ import annotations
from typing import Any


class MockGpib:
    """Mock GPIB device that simulates a Wiltron 6647A"""

    def __init__(self, interface_or_board: Any, pad: int = -1) -> None:
        self.interface = f"{interface_or_board}:{pad}" if pad != -1 else str(interface_or_board)
        self.remote_enabled = True
        self.is_listener = False
        self.is_talker = False
        self.write_buffer = ""
        self.read_buffer = ""
        self.timeout = 1.0

    def interface_clear(self) -> None:
        """Clear device interface."""
        print(f"[MOCK] interface_clear()")
        
    def clear(self) -> None:
        """Clear device."""
        print(f"[MOCK] clear()")

    def remote_enable(self, enable: int) -> None:
        """Enable remote operation."""
        self.remote_enabled = bool(enable)
        print(f"[MOCK] remote_enable({enable}) -> {self.remote_enabled}")

    def listener(self, address: int) -> None:
        """Set as listener to specified address."""
        self.is_listener = True
        self.is_talker = False
        print(f"[MOCK] listener({address})")

    def talker(self, address: int) -> None:
        """Set as talker for specified address."""
        self.is_talker = True
        self.is_listener = False
        print(f"[MOCK] talker({address})")

    def write(self, data: str) -> None:
        """Write data to device."""
        self.write_buffer = data
        print(f"[MOCK] write({data!r})")
        
        # Simulate device response based on command
        if data.strip() in ("OI", "OI "):
            # Simulate the Wiltron 6647A response to OI (Identify) query
            self.read_buffer = "WILTRON 6647A\n"
            print(f"[MOCK] - Device ID query detected, will respond with: {self.read_buffer!r}")
        else:
            self.read_buffer = ""

    def read(self, size: int = 4096) -> bytes:
        """Read data from device."""
        data = self.read_buffer[:size]
        # Only return bytes once per read
        self.read_buffer = ""
        print(f"[MOCK] read({size}) -> {data!r}")
        return data.encode("utf-8") if data else b""

    def close(self) -> None:
        """Close device."""
        print(f"[MOCK] close()")


# Monkey-patch the gpib_ctypes.Gpib when imported without physical hardware
def patch_gpib_for_testing() -> None:
    """Patch gpib_ctypes to use mock device."""
    try:
        import gpib_ctypes.Gpib as gb_module
        original_Gpib = gb_module.Gpib
        
        def Gpib_constructor(interface_or_board: Any, pad: int = -1, *args: Any, **kwargs: Any) -> Any:
            print(f"[MOCK] Creating mock GPIB for: {interface_or_board}, pad: {pad}")
            return MockGpib(interface_or_board, pad)
        
        gb_module.Gpib = Gpib_constructor  # type: ignore
        print("[MOCK] gpib_ctypes.Gpib patched with MockGpib")
    except (ImportError, AttributeError):
        print("[MOCK] Could not patch gpib_ctypes - module not available or no real GPIB hardware")
