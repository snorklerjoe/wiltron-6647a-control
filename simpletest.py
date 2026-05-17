from __future__ import annotations

from wiltron6647a import Wiltron6647A


def log_io(command: str, response: str | None) -> None:
    """Log I/O operations for debugging."""
    if response is None:
        print(f"TX: {command}")
    else:
        print(f"TX: {command}")
        print(f"RX: {response}")


def main() -> int:
    """Query the Wiltron 6647A for identification.
    
    Uses improved GPIB handshaking to avoid communication hangs:
    - interface_clear() before each query
    - Proper talker/listener setup
    - Adequate processing delay (0.5s)
    
    See GPIB_HANG_FIX_REPORT.md for details.
    """
    resource = "GPIB0::5::INSTR"
    
    try:
        inst = Wiltron6647A(resource, logger=log_io, backend="@py")
        inst.init()
        print(f"Connected to {resource}")
        
        # Query IDN
        idn = inst.output_identify_instrument()
        print(f"IDN: {idn}")
        
        inst.deinit()
        print("Disconnected")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())