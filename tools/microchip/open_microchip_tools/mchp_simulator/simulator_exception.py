from __future__ import annotations

from enum import Enum


class SimulatorException(RuntimeError):
    class FailType(Enum):
        NO_FAIL = "NO_FAIL"
        INIT_FAIL = "INIT_FAIL"
        E0101_SIM_FAILED_TO_DISASSEMBLE_INSTRUCTION = "E0101_SIM_FAILED_TO_DISASSEMBLE_INSTRUCTION"
        E0102_SIM_INVALID_INSTRUCTION = "E0102_SIM_INVALID_INSTRUCTION"
        E0103_SIM_FAILED_TO_PARSE_SCL = "E0103_SIM_FAILED_TO_PARSE_SCL"
        E0104_SIM_NO_VALUE_AVAILABLE = "E0104_SIM_NO_VALUE_AVAILABLE"
        E0105_SIM_FAILED_TO_INIT_PERIPHERAL = "E0105_SIM_FAILED_TO_INIT_PERIPHERAL"
        E0106_SIM_ATTEMPT_TO_SET_PIN = "E0106_SIM_ATTEMPT_TO_SET_PIN"
        E0107_SIM_SFR_UPDATE_EXCEPTION = "E0107_SIM_SFR_UPDATE_EXCEPTION"
        E0108_SIM_FAILED_OPERATION = "E0108_SIM_FAILED_OPERATION"
        E0109_SIM_FAILED_TO_CLOSE_FILE = "E0109_SIM_FAILED_TO_CLOSE_FILE"
        E0110_SIM_FAILED_TO_EXECUTE_INSTRUCTION = "E0110_SIM_FAILED_TO_EXECUTE_INSTRUCTION"
        E0111_SIM_UNEXPECTED_INSTRUCTION = "E0111_SIM_UNEXPECTED_INSTRUCTION"
        E0112_SIM_NO_PINS_IN_PIC_FILE = "E0112_SIM_NO_PINS_IN_PIC_FILE"

        def getMessage(self) -> str:
            # Java uses NbBundle; here we keep stable, debuggable strings.
            return self.value

    def __init__(self, fail_type: "SimulatorException.FailType", chain_msg: str = ""):
        msg = fail_type.getMessage()
        if chain_msg:
            msg = f"{msg} {chain_msg}"
        super().__init__(msg)
        self.type = fail_type

    def getType(self) -> "SimulatorException.FailType":
        return self.type


__all__ = ["SimulatorException"]
