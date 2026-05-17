from __future__ import annotations

import sys
import signal
from wiltron6647a import Wiltron6647A


def timeout_handler(signum, frame):
    print("TIMEOUT: Script exceeded 5 seconds. Hang detected!")
    sys.exit(1)


# Set 5-second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)


def log_io(command: str, response: str | None) -> None:
    if response is None:
        print(f"TX: {command}", flush=True)
    else:
        print(f"TX: {command}", flush=True)
        print(f"RX: {response}", flush=True)


def main() -> int:
    resource = "GPIB0::5::INSTR"
    
    try:
        print(f"[1] Creating Wiltron6647A instance...", flush=True)
        inst = Wiltron6647A(resource, logger=log_io, backend="@py")
        
        print(f"[2] Calling init()...", flush=True)
        inst.init()
        print(f"[3] Connected to {resource}", flush=True)
        
        print(f"[4] Querying IDN (OI command)...", flush=True)
        idn = inst.output_identify_instrument()
        print(f"[5] IDN: {idn}", flush=True)
        
        print(f"[6] Calling deinit()...", flush=True)
        inst.deinit()
        print(f"[7] Disconnected", flush=True)
        return 0
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
