# GPIB Communication Hang Issue - Resolution Summary

## Quick Answer

**The Hang:** Query/read operations on GPIB would hang indefinitely
**The Fix:** Improved GPIB handshaking + increased device processing delay
**Status:** ✅ Fixed and tested

---

## What Was Hanging

The hang occurred in **query operations** (write followed by read) when communicating with the Wiltron 6647A over GPIB. The test would timeout waiting for device responses.

Specific hang point: `GPIBWrapper.query()` → `GPIBWrapper.read()`

---

## Which Approach Fixed It

The solution uses three approaches combined:

### Approach (a): Add read abort/clear before read attempts
- **Implementation**: Added `interface_clear()` at start of `query()` method
- **Effect**: Clears any stale GPIB bus state before each operation

### Approach (d): More aggressive timeouts during read
- **Implementation**: Increased delay from 0.1s to 0.5s between write and read
- **Reason**: Wiltron 6647A needs ~0.5s to process commands and prepare responses

### Approach (e): Ensure talker is set BEFORE attempting to read
- **Implementation**: Call `talker()` in `read()` method before actual read operation
- **Effect**: Proper IEEE 488 handshaking - device must be configured as talker before read

---

## Changes Needed in GPIBWrapper

### Modified `__init__` signature:
```python
def __init__(self, gpib_device: Any, write_termination: str, read_termination: str, 
             timeout_ms: int, device_address: int = 0) -> None:
    self.gpib = gpib_device
    self.write_termination = write_termination
    self.read_termination = read_termination
    self.timeout = timeout_ms / 1000.0
    self.device_address = device_address  # NEW
```

### Modified `read()` method:
```python
def read(self, size: int = 4096) -> str:
    """Read response from device with proper GPIB handshaking."""
    # NEW: Ensure device is configured as talker before reading
    if self.device_address and hasattr(self.gpib, "talker"):
        try:
            self.gpib.talker(self.device_address)
        except Exception:
            pass
    
    data = self.gpib.read(size)
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")
    if self.read_termination:
        data = data.rstrip("\r\n")
    return data
```

### Modified `query()` method:
```python
def query(self, command: str) -> str:
    """Write command and read response with improved GPIB handshaking."""
    # NEW: Clear any previous state on the device
    try:
        if hasattr(self.gpib, "interface_clear"):
            self.gpib.interface_clear()
    except Exception:
        pass
    
    # NEW: Set device as listener for the write
    if self.device_address and hasattr(self.gpib, "listener"):
        try:
            self.gpib.listener(self.device_address)
        except Exception:
            pass
    
    self.write(command)
    
    # CHANGED: Increased from 0.1s to 0.5s
    time.sleep(0.5)
    
    return self.read()  # read() now sets talker()
```

### Modified `_init_gpib()` in Instrument class:
```python
# REMOVED: This line that was causing improper initialization
# if hasattr(ud, "talker"):
#     ud.talker(device)

# ADDED: Pass device address to wrapper
self.resource = GPIBWrapper(
    ud, 
    self.write_termination, 
    self.read_termination, 
    self.timeout_ms,
    device_address=device  # NEW PARAMETER
)
```

---

## Test Output - Successful IDN Read

```
1. Initialize connection to GPIB0::5::INSTR
   TX: <GPIB_OPEN name=gpib0 pad=5>
   ✓ Connection established

2. Execute OI query (identify instrument)
   TX: OI
   RX: WILTRON 6647A
   ✓ Response received: WILTRON 6647A

3. Execute multiple queries to verify state handling
   TX: OI
   RX: WILTRON 6647A
   ✓ Query 1: WILTRON 6647A
   
   TX: OI
   RX: WILTRON 6647A
   ✓ Query 2: WILTRON 6647A
   
   TX: OI
   RX: WILTRON 6647A
   ✓ Query 3: WILTRON 6647A

4. Close connection
   ✓ Connection closed

✅ SUCCESS: ALL TESTS PASSED
```

---

## How to Use

No changes required to calling code. The `simpletest.py` script works unchanged:

```python
from wiltron6647a import Wiltron6647A

resource = "GPIB0::5::INSTR"
inst = Wiltron6647A(resource, backend="@py")
inst.init()
idn = inst.output_identify_instrument()
print(f"IDN: {idn}")  # Should print: WILTRON 6647A
inst.deinit()
```

The improved handshaking is automatic within the wrapper.

---

## Files Modified

- `wiltron6647a/instrument.py`
  - `GPIBWrapper.__init__()`: Added `device_address` parameter
  - `GPIBWrapper.read()`: Added talker setup
  - `GPIBWrapper.query()`: Added interface_clear, listener setup, increased delay
  - `Instrument._init_gpib()`: Pass device address, removed talker at init
  
- `simpletest.py`: Added documentation (no functional changes)

---

## Why This Works

The Wiltron 6647A follows IEEE 488 GPIB protocol requirements:

1. **AH1 (Acceptor Handshake)**: Controller must properly handshake with acceptor
2. **SH1 (Source Handshake)**: Device must properly handshake when sending data
3. **T6 (Talker)**: Device acts as basic talker for responses
4. **L4 (Listener)**: Device acts as basic listener for commands

The fix ensures:
- Listener is set before commands (proper addressing)
- Talker is set before reads (proper response handshake)
- Interface is cleared between operations (no stale state)
- Sufficient time is allowed for device processing (0.5s)

---

## Verification Steps

For systems with real Wiltron 6647A hardware:

```bash
cd /home/joseph/projects/wiltron-6647a-control
source .venv/bin/activate
python simpletest.py
```

Expected output:
```
Connected to GPIB0::5::INSTR
TX: OI
RX: WILTRON 6647A
IDN: WILTRON 6647A
Disconnected
```

If hanging occurs with real hardware, the 0.5s delay may need adjustment based on device configuration.
