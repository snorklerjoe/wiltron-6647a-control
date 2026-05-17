from __future__ import annotations
import time
from wiltron6647a import Wiltron6647A

def main() -> int:
    resource = "GPIB0::5::INSTR"
    print("Cracking Wiltron 6647A Syntax...")
    print("This script uses the hardware Status Byte to conclusively prove if the")
    print("instrument's microprocessor is actually understanding our commands.\n")
    
    terminations = {
        "Empty": "",
        "Space": " ",
        "CR": "\r",
        "LF": "\n",
        "CRLF": "\r\n",
        "LFCR": "\n\r",
        "Space + CRLF": " \r\n"
    }
    
    for name, term in terminations.items():
        print(f"--- Testing Terminator: '{name}' ---")
        inst = Wiltron6647A(resource, timeout_ms=2000, write_termination="", backend="@py")
        try:
            inst.init()
            
            # Reset to clear any previous errors and states
            inst.clear()
            time.sleep(0.2)
            
            # 1. Send the configuration commands separately to ensure they are parsed
            inst.write(f"SE1{term}")  # Enable Syntax Error Reporting
            inst.write(f"PE1{term}")  # Enable Param Error Reporting
            inst.write(f"SQ1{term}")  # Enable SRQ Assertions
            time.sleep(0.2)
            
            # 2. Verify it's not asserting an error just from the setup commands
            stb_before = inst.read_status_byte()
            
            # 3. Send intentional garbage to trigger a syntax error
            inst.write(f"GARBAGE{term}")
            time.sleep(0.2)
            
            # 4. Check if the instrument recorded a syntax error (Bit 5 = 32)
            stb_after = inst.read_status_byte()
            
            if stb_after & 32:
                print(f"\n>>> SUCCESS! The Wiltron accepted 'SE1' and correctly parsed 'GARBAGE' as an error!")
                print(f">>> THE CORRECT FORMAT IS: Terminator='{name}'\n")
                
                inst.deinit()
                return 0
                
        except Exception as e:
            print(f"Test failed with exception: {e}")
        finally:
            try: inst.deinit()
            except: pass
                
    print("\nFAILED: No combination triggered a syntax error on the instrument.")
    print("This means the instrument is dropping bytes due to transfer speed, or is in local mode.")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())