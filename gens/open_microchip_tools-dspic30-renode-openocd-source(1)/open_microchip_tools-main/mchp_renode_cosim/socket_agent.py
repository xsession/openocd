from __future__ import annotations

import argparse
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from .protocol import ActionType, ProtocolMessage


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    buf = bytearray(size)
    view = memoryview(buf)
    read = 0
    while read < size:
        n = sock.recv_into(view[read:])
        if n == 0:
            raise ConnectionError("socket closed")
        read += n
    return bytes(buf)


@dataclass
class StubCPUState:
    halted: bool = False
    single_step: bool = False
    registers: Dict[int, int] = field(default_factory=dict)


@dataclass
class FirmwareCPUState(StubCPUState):
    """CPU state backed by `mchp_simulator.firmware_simulator.FirmwareSimulator` (optional)."""

    pc_reg: int = 0
    simulator: object | None = None

    def get_pc(self) -> int:
        if self.simulator is None:
            return int(self.registers.get(self.pc_reg, 0))

        try:
            processor = getattr(self.simulator, "processor", None)
            if processor is None:
                return 0
            return int(processor.getPC())
        except Exception:
            return 0

    def set_pc(self, value: int) -> None:
        if self.simulator is None:
            self.registers[self.pc_reg] = int(value) & 0xFFFFFFFFFFFFFFFF
            return

        try:
            processor = getattr(self.simulator, "processor", None)
            if processor is None:
                return
            processor.setPC(int(value))
        except Exception:
            return

    def step_one(self) -> bool:
        """Returns True if execution may continue, False if it halted (e.g. breakpoint)."""

        if self.simulator is None:
            self.set_pc(self.get_pc() + 1)
            return True

        processor = getattr(self.simulator, "processor", None)
        if processor is None:
            return True
        return bool(processor.singleStep())


class CoSimSocketAgent:
    """Minimal socket-based co-simulation agent.

    Renode side:
      - listens on two TCP ports (main + async)
    Agent side:
      - connects to both ports
      - receives requests on main
      - sends responses/notifications on async (except handshake, which is on main)
    """

    def __init__(
        self,
        *,
        host: str,
        main_port: int,
        async_port: int,
        state: Optional[StubCPUState] = None,
        max_steps_per_tick: int = 1000000,
    ):
        self.host = host
        self.main_port = int(main_port)
        self.async_port = int(async_port)
        self.state = state or StubCPUState()
        self.max_steps_per_tick = max(1, int(max_steps_per_tick))

        self._main: Optional[socket.socket] = None
        self._async: Optional[socket.socket] = None

    def connect(self, timeout_s: float = 10.0) -> None:
        deadline = time.time() + timeout_s
        self._main = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._async = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # simple retry loop (Renode might still be bringing up listeners)
        while True:
            try:
                self._main.connect((self.host, self.main_port))
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(0.1)

        while True:
            try:
                self._async.connect((self.host, self.async_port))
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(0.1)

        self._main.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._async.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self._handshake()

    def _handshake(self) -> None:
        assert self._main is not None
        raw = _recv_exact(self._main, ProtocolMessage._STRUCT.size)
        msg = ProtocolMessage.from_bytes(raw)
        if msg.action != ActionType.Handshake:
            raise RuntimeError(f"Expected Handshake on main socket, got {msg.action.name}")
        self._main.sendall(ProtocolMessage(ActionType.Handshake, 0, 0, ProtocolMessage.NoPeripheralIndex).to_bytes())

    def serve_forever(self) -> None:
        assert self._main is not None
        assert self._async is not None

        while True:
            raw = _recv_exact(self._main, ProtocolMessage._STRUCT.size)
            req = ProtocolMessage.from_bytes(raw)
            if req.action == ActionType.Disconnect:
                return
            self._handle_request(req)

    def _respond_async(self, action: ActionType, address: int, data: int, peripheral_index: int) -> None:
        assert self._async is not None
        self._async.sendall(ProtocolMessage(action, address, data, peripheral_index).to_bytes())

    def _handle_request(self, req: ProtocolMessage) -> None:
        a = req.action

        if a == ActionType.TickClock:
            # In Renode's CoSimulatedCPU, TickClock response Data is interpreted as
            # instructions executed this round.
            if getattr(self.state, "halted", False) or getattr(self.state, "single_step", False):
                executed = 0
            else:
                budget = max(0, int(req.data))
                budget = min(budget, self.max_steps_per_tick)
                executed = 0
                while executed < budget and not getattr(self.state, "halted", False):
                    cont = True
                    if hasattr(self.state, "step_one"):
                        cont = bool(getattr(self.state, "step_one")())
                    executed += 1
                    if not cont:
                        self.state.halted = True

            self._respond_async(ActionType.TickClock, req.address, executed, req.peripheral_index)
            return

        if a == ActionType.Step:
            # Execute at most one instruction.
            cont = True
            if hasattr(self.state, "step_one"):
                cont = bool(getattr(self.state, "step_one")())
            if getattr(self.state, "single_step", False):
                self.state.halted = True
            else:
                self.state.halted = not cont
            self._respond_async(ActionType.Step, req.address, 1 if cont else 0, req.peripheral_index)
            return

        if a == ActionType.IsHalted:
            self._respond_async(ActionType.IsHalted, req.address, 1 if self.state.halted else 0, req.peripheral_index)
            return

        if a == ActionType.SingleStepMode:
            self.state.single_step = bool(req.data)
            # If entering single step mode, consider CPU halted until `Step` arrives.
            if self.state.single_step:
                self.state.halted = True
            self._respond_async(ActionType.SingleStepMode, req.address, req.data, req.peripheral_index)
            return

        if a == ActionType.RegisterGet:
            reg = int(req.address)
            if hasattr(self.state, "pc_reg") and reg == int(getattr(self.state, "pc_reg")) and hasattr(self.state, "get_pc"):
                value = int(getattr(self.state, "get_pc")())
            else:
                value = self.state.registers.get(reg, 0)
            self._respond_async(ActionType.RegisterGet, req.address, value, req.peripheral_index)
            return

        if a == ActionType.RegisterSet:
            reg = int(req.address)
            val = int(req.data) & 0xFFFFFFFFFFFFFFFF
            if hasattr(self.state, "pc_reg") and reg == int(getattr(self.state, "pc_reg")) and hasattr(self.state, "set_pc"):
                getattr(self.state, "set_pc")(val)
            else:
                self.state.registers[reg] = val
            # Ack.
            self._respond_async(ActionType.RegisterSet, 0, 0, req.peripheral_index)
            return

        if a == ActionType.ResetPeripheral:
            self.state.registers.clear()
            self.state.halted = False
            self.state.single_step = False
            if hasattr(self.state, "set_pc"):
                getattr(self.state, "set_pc")(0)
            self._respond_async(ActionType.ResetPeripheral, req.address, req.data, req.peripheral_index)
            return

        # Default: indicate we don't understand the request.
        self._respond_async(ActionType.Error, req.address, req.data, req.peripheral_index)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Renode CoSimulationPlugin socket agent (stub)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--main-port", type=int, required=True)
    p.add_argument("--async-port", type=int, required=True)
    p.add_argument("--max-steps-per-tick", type=int, default=100000)

    p.add_argument("--device", help="Device name (e.g. dsPIC33EP512GM710, dsPIC30F5011)")
    p.add_argument("--firmware", help="Firmware path (.hex/.elf) to load into the local simulator")
    p.add_argument("--pc-reg", type=int, default=0, help="Register index used by Renode to represent PC")
    args = p.parse_args(argv)

    state: StubCPUState
    state = FirmwareCPUState(pc_reg=int(args.pc_reg))

    # Optional: back the agent with the local FirmwareSimulator.
    if args.device:
        try:
            from mchp_simulator.device_catalog import guess_device_spec
            from mchp_simulator.firmware_image import FirmwareImage
            from mchp_simulator.firmware_simulator import FirmwareSimulator

            spec = guess_device_spec(str(args.device))
            sim = FirmwareSimulator(spec)
            sim.Engage(None)
            if args.firmware:
                img = FirmwareImage.from_path(str(args.firmware))
                sim.load_firmware(img)
            state.simulator = sim
        except Exception:
            # Fall back to the stub state if simulator cannot be initialized.
            state.simulator = None

    agent = CoSimSocketAgent(
        host=args.host,
        main_port=args.main_port,
        async_port=args.async_port,
        state=state,
        max_steps_per_tick=args.max_steps_per_tick,
    )
    agent.connect()
    agent.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
