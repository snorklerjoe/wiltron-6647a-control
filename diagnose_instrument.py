from __future__ import annotations
import time
from wiltron6647a import Wiltron6647A

def print_stb(stb: int) -> None:
    print(f"Status Byte: 0x{stb:02X} ({stb})")
    print(f"  Bit 0 (1) : Dwell           : {bool(stb & 1)}")
    print(f"  Bit 1 (2) : End of Sweep    : {bool(stb & 2)}")
    print(f"  Bit 2 (4) : Unleveled       : {bool(stb & 4)}")
    print(f"  Bit 4 (16): Param Error     : {bool(stb & 16)}")
    print(f"  Bit 5 (32): Syntax Error    : {bool(stb & 32)}")
    print(f"  Bit 6 (64): SRQ Asserted    : {bool(stb & 64)}")

def test_command(inst: Wiltron6647A, cmd: str, name: str) -> None:
    print(f"\n--- Testing '{cmd}' ({name}) ---")
    inst.write(cmd)
    time.sleep(0.5)
    
    stb = inst.read_status_byte()
    print_stb(stb)
    
    if stb & 32:
        print(f"!!! The Wiltron rejected '{cmd}' as a SYNTAX ERROR !!!")
    elif stb & 16:
        print(f"!!! The Wiltron rejected '{cmd}' as a PARAMETER ERROR !!!")
    else:
        print(f"'{cmd}' was accepted! Wiltron output queue should be full. Attempting read...")
        try:
            if hasattr(inst.resource, "read"):
                data = inst.resource.read(40 if cmd == "OI" else 4096)
            else:
                data = inst.read()
            print(f"SUCCESS! Read data: {data!r}")
        except Exception as e:
            print(f"Read timed out or failed: {e}")
            
    # Clear error state for the next test
    inst.clear()
    time.sleep(0.2)

def main() -> int:
    resource = "GPIB0::5::INSTR"
    print(f"Connecting to {resource}...")
    
    # 1s timeout to fail fast if it hangs
    inst = Wiltron6647A(resource, timeout_ms=1000, write_termination="\r\n", backend="@py")
    try:
        inst.init()
        inst.clear()
        time.sleep(0.5)
        
        # Turn on SRQ reporting for Syntax Errors and Param Errors
        print("\nConfiguring instrument to report errors (SE1, PE1, SQ1)...")
        inst.write("SE1 PE1 SQ1")
        time.sleep(0.5)
        
        initial_stb = inst.read_status_byte()
        print("Initial Status:")
        print_stb(initial_stb)
            
        test_command(inst, "OI", "Identify Instrument")
        test_command(inst, "OSB", "Output Status Byte")
        test_command(inst, "OF0", "Output F0 Parameter")
        
        # Try a known bad command just to prove the syntax error reporting works!
        test_command(inst, "GARBAGE", "Intentional Bad Command")

        return 0
    except Exception as e:
        print(f"Diagnostic failed: {e}")
        return 1
    finally:
        try: inst.deinit()
        except: pass

if __name__ == "__main__":
    raise SystemExit(main())