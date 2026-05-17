from __future__ import annotations

import time
from typing import Any

import pyvisa

try:
    from gpib_ctypes.Gpib import Gpib
except Exception:  # pragma: no cover - optional fallback
    Gpib = None

BOARD = "gpib0"
PAD = 12
RESOURCE = f"GPIB::{PAD}::INSTR"
QUERY_COMMANDS = ("*IDN?", "IDN?")


def try_pyvisa(backend: str | None, command: str) -> str:
    rm = pyvisa.ResourceManager(backend) if backend else pyvisa.ResourceManager()
    try:
        res = rm.open_resource(RESOURCE)
        try:
            res_any: Any = res
            res.timeout = 5000
            res_any.write_termination = "\n"
            res_any.read_termination = "\n"
            res_any.clear()
            time.sleep(0.2)
            return res_any.query(command)
        finally:
            try:
                res.close()
            except Exception:
                pass
    finally:
        try:
            rm.close()
        except Exception:
            pass


def try_gpib_ctypes(command: str) -> str:
    if Gpib is None:
        raise RuntimeError("gpib_ctypes is not available")

    dev = Gpib(BOARD)
    try:
        dev.interface_clear()
        dev.remote_enable(1)
        dev.listener(PAD)
        time.sleep(0.5)
        dev.write(command)
        time.sleep(0.5)
        try:
            raw = dev.read(256)
            return raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        except Exception as exc:
            raise RuntimeError(f"GPIB read failed: {exc}")
    finally:
        try:
            dev.close()
        except Exception:
            pass


def main() -> int:
    print(f"Querying E4419B at {RESOURCE}")

    for command in QUERY_COMMANDS:
        backend = "@py"
        try:
            response = try_pyvisa(backend, command)
            label = backend or "default"
            print(f"PyVISA ({label}) {command} response:")
            print(response.strip())
            return 0
        except Exception as pyvisa_exc:
            label = backend or "default"
            print(f"PyVISA ({label}) {command} failed: {pyvisa_exc}")

        try:
            response = try_gpib_ctypes(command)
            print(f"gpib_ctypes {command} response:")
            print(response.strip())
            return 0
        except Exception as gpib_exc:
            print(f"gpib_ctypes {command} failed: {gpib_exc}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
