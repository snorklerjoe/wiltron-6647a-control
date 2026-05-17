# wiltron-6647a-control

Simple Python library and PyQt softpanel for controlling a Wiltron 6647A over GPIB via `pyvisa`.

## Install

```bash
pip install -e .
```

## Library usage

```python
from wiltron6647a import Wiltron6647A

inst = Wiltron6647A("GPIB0::5::INSTR")
inst.init()

inst.rf_on()
inst.set_f0(10.0, "GH")
inst.set_delta_f(250, "MH")
idn = inst.output_identify_instrument()
print(idn)

inst.deinit()
```

## Softpanel GUI

```bash
python softpanel.py
```

The GUI is tabbed and includes:
- VISA connection and IEEE-488 bus actions
- Sweep, trigger, marker, RF, and leveling controls
- Step sweep and SRQ controls
- Output and miscellaneous controls
- Command browser for every command listed in the programming summary
- A bottom command log that records all TX/RX activity
