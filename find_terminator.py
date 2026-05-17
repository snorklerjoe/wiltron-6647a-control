from __future__ import annotations
import time
from wiltron6647a import Wiltron6647A

def main() -> int:
    resource = "GPIB0::5::INSTR"
    
    # We will test all these syntax variations
    terminations = {
        "None (empty)": "",
        "Space": " ",
        "CR": "\r",
        "LF": "\n",
        "CRLF": "\r\n",
        "LFCR": "\n\r",
        "Space + LF": " \n",
        "Space + CR": " \r",
        "Space + CRLF": " \r\n"
    }
    
    print("Starting automated terminator search...")
    print("This will test multiple syntax combinations to see what the Wiltron accepts.\n")

    for name, term in terminations.items():
        print(f"=== Testing Termination: {name} ===")
        try:
            # Use a slightly shorter timeout (2s) to iterate quickly
            inst = Wiltron6647A(resource, timeout_ms=2000, write_termination=term, backend="@py")
            inst.init()
            
            # Send a Selected Device Clear (SDC) to flush previous syntax errors
            inst.clear()
            time.sleep(0.5)
            
            # Attempt the Identify command
            print(f"Sending 'OI' with {name} terminator...")
            response = inst.query("OI")
            print(f"SUCCESS! Received: {response!r}")
            
            inst.deinit()
            print(f"\n>>> THE CORRECT TERMINATOR IS: {name} <<<")
            return 0
            
        except Exception as e:
            print(f"Failed: {e}")
            try:
                inst.deinit()
            except:
                pass
        print("-" * 40)

if __name__ == "__main__":
    raise SystemExit(main())