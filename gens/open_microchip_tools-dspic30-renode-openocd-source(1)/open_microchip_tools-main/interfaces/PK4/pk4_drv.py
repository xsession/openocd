from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from mchp_ri4.commands import Commands
from mchp_ri4.icd4_comms_usb import ICD4CommsUsb
from mchp_ri4.power_control import Ri4PowerController
from mchp_ri4.ri4_com import EndpointMap, Ri4Com, DEFAULT_ENDPOINTS


@dataclass(frozen=True)
class PK4UsbIds:
	vid: int
	pid: int


class PK4Driver:
	def __init__(self, ids: PK4UsbIds, *, endpoints: Optional[EndpointMap] = None):
		from mchp_ri4.transport import PyusbTransport

		self._transport = PyusbTransport(vid=ids.vid, pid=ids.pid)
		self._com = Ri4Com(self._transport, endpoints=endpoints or DEFAULT_ENDPOINTS)
		self._ctrl = ICD4CommsUsb(self._com)
		self._commands = Commands(self._ctrl)
		self._power = Ri4PowerController(self._commands)

	def get_status_value(self, key: str) -> str:
		return self._ctrl.get_status_value_from_key(key)

	def exec_raw_command(self, command_info: bytes, response_length: int, *, timeout_ms: int = -1) -> bytes:
		return self._ctrl.exec_command(command_info, response_length, timeout_ms=timeout_ms)

	def power_target(self, voltage_mv: int, **kwargs):
		return self._power.power_target(voltage_mv, **kwargs)

	def power_status(self):
		return self._power.get_power_status()

	def shutdown_power(self):
		return self._power.shutdown_power()

	def close(self) -> None:
		self._commands.close()

