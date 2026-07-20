from __future__ import annotations

import argparse
import json
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

from .power_cli import _discover_pid, _open_driver
from .repo_assets import iter_repo_firmware_packages, load_manifest, resolve_repo_firmware_path, vendor_root


FIRMWARE_STATUS_KEYS = (
    "MajorFirmwareVersion",
    "MinorFirmwareVersion",
    "MajorFirmwareVersionOnDisk",
    "MinorFirmwareVersionOnDisk",
    "HardwareRevision",
    "Commands in progress",
)

GET_FIRMWARE_INFO_COMMAND = bytes((0xE1,))
FIRMWARE_INFO_RESPONSE_LENGTH = 512
FIRMWARE_TYPE_BOOT = 0xBF
FIRMWARE_TYPE_APP = 0xAF
CONFIG_AREA_SUPPORT_MAGIC = 1265202276
BOOT_UPDATE_SUPPORT_MAGIC = 1179402836
ENTER_UPGRADE_MODE_COMMAND = bytes((0xE0,))
ERASE_FLASH_COMMAND = 0xE2
WRITE_FLASH_COMMAND = 0xE3
GET_CRCS_COMMAND = bytes((0xE5,))
JUMP_TO_APP_COMMAND = bytes((0xE6,))
SOFTWARE_RESET_COMMAND = bytes((0xE7,))
WRITE_BFM_COMMAND = 0xE4
APP_FLASH_TYPE = 0xFA
BOOT_FLASH_TYPE = 0xFB
PK4_BOOT_PID = 0x9017
PK4_PFM_START = 0x40C000
PK4_PFM_SIZE = 0x1F4000
PK4_PFM_ROW_SIZE = 512
PK4_BFM_START = 0x400000
PK4_BFM_SIZE = 0xC000
PK4_BFM_PAGE_SIZE = 0x2000
PK4_BOOT_FILE_NAME = "boot.hex"
PK4_APP_FILE_NAME = "app.hex"


@dataclass(frozen=True)
class NativeFirmwareInfo:
    boot_mode: bool
    application_version: str
    boot_version: str
    firmware_type: str
    device_id: int
    device_id_1: int
    hardware_bootloader_update_supported: bool
    config_area_read_supported: bool

    def to_dict(self) -> Dict[str, object]:
        return {
            "bootMode": self.boot_mode,
            "applicationVersion": self.application_version,
            "bootVersion": self.boot_version,
            "firmwareType": self.firmware_type,
            "deviceId": f"0x{self.device_id:08X}",
            "deviceId1": f"0x{self.device_id_1:08X}",
            "hardwareBootloaderUpdateSupported": self.hardware_bootloader_update_supported,
            "configAreaReadSupported": self.config_area_read_supported,
        }


@dataclass(frozen=True)
class ToolFirmwareState:
    tool: str
    reachable: bool
    current_version: str = ""
    packaged_version: str = ""
    hardware_revision: str = ""
    commands_in_progress: str = ""
    selected_firmware_path: str = ""
    selected_firmware_version: str = ""
    application_version: str = ""
    boot_version: str = ""
    boot_mode: Optional[bool] = None
    bootloader_update_supported: Optional[bool] = None
    state: str = "unknown"
    recommendation: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "tool": self.tool,
            "reachable": self.reachable,
            "currentVersion": self.current_version,
            "packagedVersion": self.packaged_version,
            "hardwareRevision": self.hardware_revision,
            "commandsInProgress": self.commands_in_progress,
            "selectedFirmwarePath": self.selected_firmware_path,
            "selectedFirmwareVersion": self.selected_firmware_version,
            "applicationVersion": self.application_version,
            "bootVersion": self.boot_version,
            "bootMode": self.boot_mode,
            "bootloaderUpdateSupported": self.bootloader_update_supported,
            "state": self.state,
            "recommendation": self.recommendation,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class FirmwareBundle:
    tool: str
    jam_path: Path
    payload_path: Path
    payload_name: str
    payload_version: str


def _format_version(major: str, minor: str) -> str:
    if not major and not minor:
        return ""
    try:
        return f"{int(major, 0):X}.{int(minor, 0):02X}"
    except Exception:
        return f"{major}.{minor}".strip(".")


def _format_byte_version(major: int, minor: int, revision: int = -1) -> str:
    if revision >= 0:
        return f"{major:02X}.{minor:02X}.{revision:02X}"
    return f"{major:02X}.{minor:02X}"


def _u32le(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little", signed=False)


def parse_firmware_info_response(response: bytes) -> NativeFirmwareInfo:
    if len(response) < FIRMWARE_INFO_RESPONSE_LENGTH:
        raise ValueError(f"Firmware info response too short: {len(response)}")

    firmware_type = response[1]
    if firmware_type == FIRMWARE_TYPE_BOOT:
        boot_mode = True
        boot_version = _format_byte_version(response[3], response[4], response[5])
        application_version = _format_byte_version(response[172], response[173], response[174])
        firmware_type_name = "boot"
    elif firmware_type == FIRMWARE_TYPE_APP:
        boot_mode = False
        application_version = _format_byte_version(response[3], response[4], response[5])
        boot_version = _format_byte_version(response[164], response[165], response[166])
        firmware_type_name = "application"
    else:
        raise ValueError(f"Unexpected firmware type byte 0x{firmware_type:02X}")

    return NativeFirmwareInfo(
        boot_mode=boot_mode,
        application_version=application_version,
        boot_version=boot_version,
        firmware_type=firmware_type_name,
        device_id=_u32le(response, 18),
        device_id_1=_u32le(response, 203),
        hardware_bootloader_update_supported=_u32le(response, 227) == BOOT_UPDATE_SUPPORT_MAGIC,
        config_area_read_supported=_u32le(response, 219) == CONFIG_AREA_SUPPORT_MAGIC,
    )


def read_native_firmware_info(driver) -> NativeFirmwareInfo:
    response = driver.exec_raw_command(GET_FIRMWARE_INFO_COMMAND, FIRMWARE_INFO_RESPONSE_LENGTH)
    return parse_firmware_info_response(response)


def _list_usb_products(vid: int) -> list[int]:
    try:
        import usb.backend.libusb1  # type: ignore
        import usb.core  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PyUSB is required for firmware update; install project extra 'usb'.") from exc

    backend = usb.backend.libusb1.get_backend()
    if backend is None:
        try:
            import libusb_package  # type: ignore
        except Exception:
            libusb_package = None  # type: ignore
        if libusb_package is not None:
            backend = libusb_package.get_libusb1_backend()
    if backend is None:
        raise RuntimeError("PyUSB libusb backend not available; install a libusb-1.0 backend such as 'libusb-package'.")

    devices = list(usb.core.find(find_all=True, idVendor=vid, backend=backend) or [])
    return sorted({int(device.idProduct) for device in devices})


def _wait_for_pid(vid: int, preferred_pid: int, *, timeout_s: float) -> int:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        products = _list_usb_products(vid)
        if preferred_pid in products:
            return preferred_pid
        if len(products) == 1:
            return products[0]
        time.sleep(0.25)
    rendered = ", ".join(f"0x{product:04X}" for product in _list_usb_products(vid)) or "<none>"
    raise RuntimeError(f"Timed out waiting for tool re-enumeration for vid=0x{vid:04X}. Seen products: {rendered}")


def _parse_jam_entries(jam_path: Path) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    for raw_line in jam_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "," in line:
            key, value = line.split(",", 1)
            normalized_key = key.strip()
            normalized_value = value.strip()
            entries[normalized_key] = normalized_value
            compact_key = normalized_key.replace(" ", "")
            if compact_key != normalized_key:
                entries[compact_key] = normalized_value
            if " " in normalized_key:
                prefix, suffix = normalized_key.split(None, 1)
                entries[prefix] = suffix.strip()
            continue
        parts = line.replace(" ", "").split(",")
        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip()
            entries[key] = value
    return entries


def _iter_payload_dirs(tool: str, jam_path: Path) -> Iterable[Path]:
    seen: set[Path] = set()

    def _yield(path: Path) -> Iterable[Path]:
        resolved = path.resolve()
        if resolved in seen:
            return []
        seen.add(resolved)
        return [resolved]

    yield from _yield(jam_path.parent)

    manifest = load_manifest()
    toolpack = dict(manifest.get("toolpacks", {})).get(str(tool).upper())
    if isinstance(toolpack, dict):
        scripts_path = toolpack.get("scriptsPath")
        if scripts_path:
            yield from _yield(Path(str(scripts_path)).resolve().parent)
        firmware_path = toolpack.get("firmwarePath")
        if firmware_path:
            yield from _yield(Path(str(firmware_path)).resolve().parent)
        pack = str(toolpack.get("pack", "")).strip()
        version = str(toolpack.get("version", "")).strip()
        if pack and version:
            for mplab_root in sorted(Path("C:/Program Files/Microchip/MPLABX").glob("v*/packs/Microchip")):
                candidate = mplab_root / pack / version / "firmware"
                if candidate.exists():
                    yield from _yield(candidate)

    tool_firmware_root = vendor_root() / "packs" / "Microchip"
    for pack_dir in tool_firmware_root.glob("*/ */firmware"):
        yield from _yield(pack_dir)


def _resolve_bundle(tool: str, *, payload_name: str = PK4_APP_FILE_NAME, jam_path: Optional[Path] = None) -> FirmwareBundle:
    selected_jam = jam_path or resolve_repo_firmware_path(tool)
    if selected_jam is None:
        raise FileNotFoundError(f"No vendored firmware package found for tool '{tool}'")

    selected_jam = Path(selected_jam)
    jam_entries = _parse_jam_entries(selected_jam)
    payload_version = jam_entries.get("app1", "").split(",", 1)[0].replace(" ", "") if payload_name == PK4_APP_FILE_NAME else jam_entries.get(PK4_BOOT_FILE_NAME, "")
    for directory in _iter_payload_dirs(tool, selected_jam):
        candidate = directory / payload_name
        if candidate.exists():
            return FirmwareBundle(
                tool=str(tool).upper(),
                jam_path=selected_jam,
                payload_path=candidate,
                payload_name=payload_name,
                payload_version=payload_version,
            )

    raise FileNotFoundError(f"Unable to locate {payload_name} for {tool} from {selected_jam}")


def _read_intel_hex(path: Path) -> tuple[int, bytes]:
    memory: Dict[int, int] = {}
    base = 0
    start_address: Optional[int] = None
    end_address = -1

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith(":"):
            raise ValueError(f"Invalid Intel HEX record at {path}:{line_number}")
        payload = bytes.fromhex(line[1:])
        count = payload[0]
        offset = int.from_bytes(payload[1:3], "big")
        record_type = payload[3]
        data = payload[4 : 4 + count]

        if record_type == 0x00:
            absolute = base + offset
            if start_address is None:
                start_address = absolute
            for index, value in enumerate(data):
                memory[absolute + index] = value
            end_address = max(end_address, absolute + count - 1)
        elif record_type == 0x01:
            break
        elif record_type == 0x04:
            base = int.from_bytes(data, "big") << 16
        elif record_type == 0x02:
            base = int.from_bytes(data, "big") << 4

    if start_address is None or end_address < start_address:
        raise ValueError(f"No data records found in {path}")

    image = bytearray(b"\xFF" * (end_address - start_address + 1))
    for address, value in memory.items():
        image[address - start_address] = value
    return start_address, bytes(image)


def _expect_status_ok(response: bytes, *, command_name: str, expected_prefix: Optional[bytes] = None, status_index: int = 1) -> None:
    if expected_prefix is not None and not response.startswith(expected_prefix):
        raise RuntimeError(f"{command_name} returned unexpected response prefix: {response[: len(expected_prefix)].hex()}")
    if status_index < len(response) and response[status_index] != 0:
        raise RuntimeError(f"{command_name} failed with status 0x{response[status_index]:02X}")


def _enter_upgrade_mode(driver) -> None:
    response = driver.exec_raw_command(ENTER_UPGRADE_MODE_COMMAND, 2, timeout_ms=10_000)
    _expect_status_ok(response, command_name="enterUpgradeMode", expected_prefix=ENTER_UPGRADE_MODE_COMMAND, status_index=1)


def _erase_flash(driver, *, boot: bool) -> None:
    flash_type = BOOT_FLASH_TYPE if boot else APP_FLASH_TYPE
    response = driver.exec_raw_command(bytes((ERASE_FLASH_COMMAND, flash_type)), 3, timeout_ms=50_000)
    _expect_status_ok(response, command_name="eraseFlash", expected_prefix=bytes((ERASE_FLASH_COMMAND, flash_type)), status_index=2)


def _pack_u32le(value: int) -> bytes:
    return int(value & 0xFFFFFFFF).to_bytes(4, "little")


def _write_flash_row(driver, address: int, data: bytes, *, timeout_ms: int) -> None:
    command = bytearray(13 + len(data))
    command[0] = WRITE_FLASH_COMMAND
    command[1:5] = _pack_u32le(address)
    command[13:] = data
    response = driver.exec_raw_command(bytes(command), 14, timeout_ms=timeout_ms)
    if len(response) < 14 or response[13] != 0:
        status = 0xFF if len(response) < 14 else response[13]
        raise RuntimeError(f"writePFM failed at 0x{address:08X} with status 0x{status:02X}")


def _get_pfm_crc(driver) -> int:
    response = driver.exec_raw_command(GET_CRCS_COMMAND, 64, timeout_ms=10_000)
    if len(response) < 5:
        raise RuntimeError("getCRCs returned too few bytes")
    return int.from_bytes(response[1:5], "little")


def _get_bfm_crc_without_last4(driver) -> int:
    response = driver.exec_raw_command(GET_CRCS_COMMAND, 64, timeout_ms=10_000)
    index = 9 + 6 * 4
    if len(response) < index + 4:
        raise RuntimeError("getCRCs returned too few bytes for BFM CRC")
    return int.from_bytes(response[index : index + 4], "little")


def _jump_to_app(driver) -> None:
    response = driver.exec_raw_command(JUMP_TO_APP_COMMAND, 2, timeout_ms=10_000)
    if len(response) < 1 or response[0] != JUMP_TO_APP_COMMAND[0]:
        raise RuntimeError("jumpToApp did not acknowledge")


def _software_reset(driver) -> None:
    driver.exec_raw_command(SOFTWARE_RESET_COMMAND, 1, timeout_ms=10_000)


def _build_pk4_pfm_image(path: Path) -> tuple[int, bytes, int]:
    start_address, raw_image = _read_intel_hex(path)
    if start_address != PK4_PFM_START:
        raise RuntimeError(f"Unexpected PK4 application start address 0x{start_address:08X}; expected 0x{PK4_PFM_START:08X}")
    if len(raw_image) > PK4_PFM_SIZE:
        raise RuntimeError(f"PK4 application image too large: 0x{len(raw_image):X} bytes")
    whole_image = bytearray(b"\xFF" * PK4_PFM_SIZE)
    whole_image[: len(raw_image)] = raw_image
    crc = zlib.crc32(whole_image[:-4]) & 0xFFFFFFFF
    whole_image[-4:] = _pack_u32le(crc)
    return start_address, bytes(whole_image), crc


def _build_pk4_bfm_image(path: Path) -> tuple[int, bytes, int]:
    start_address, raw_image = _read_intel_hex(path)
    if start_address != PK4_BFM_START:
        raise RuntimeError(f"Unexpected PK4 boot start address 0x{start_address:08X}; expected 0x{PK4_BFM_START:08X}")
    if len(raw_image) > PK4_BFM_SIZE:
        raise RuntimeError(f"PK4 boot image too large: 0x{len(raw_image):X} bytes")
    whole_image = bytearray(b"\xFF" * PK4_BFM_SIZE)
    whole_image[: len(raw_image)] = raw_image
    crc = zlib.crc32(whole_image[:-4]) & 0xFFFFFFFF
    whole_image[-4:] = _pack_u32le(crc)
    return start_address, bytes(whole_image), crc


def _do_we_need_boot_length_kludge(boot_info: NativeFirmwareInfo) -> bool:
    if not boot_info.boot_version:
        return False
    try:
        major_text, minor_text, revision_text = boot_info.boot_version.split(".")
        major = int(major_text, 16)
        minor = int(minor_text, 16)
        revision = int(revision_text, 16)
    except Exception:
        return False
    return major == 0 and minor == 0 and revision > 52


def _write_bfm(driver, image: bytes, *, add_length_kludge: bool) -> None:
    command_length = 512 + PK4_BFM_SIZE
    if add_length_kludge and command_length % 64 == 0:
        command_length += 1
    command = bytearray(command_length)
    command[0] = WRITE_BFM_COMMAND
    command[512 : 512 + len(image)] = image
    response = driver.exec_raw_command(bytes(command), 512, timeout_ms=120_000)
    if len(response) < 512 or response[511] != 0:
        status = 0xFF if len(response) < 512 else response[511]
        raise RuntimeError(f"writeBFM failed with status 0x{status:02X}")


def _apply_pk4_boot_image(driver, bundle: FirmwareBundle, boot_info: NativeFirmwareInfo) -> Dict[str, object]:
    start_address, image, expected_crc = _build_pk4_bfm_image(bundle.payload_path)
    _write_bfm(driver, image, add_length_kludge=_do_we_need_boot_length_kludge(boot_info))
    observed_crc = _get_bfm_crc_without_last4(driver)
    _software_reset(driver)
    return {
        "payloadPath": str(bundle.payload_path),
        "payloadVersion": bundle.payload_version,
        "startAddress": f"0x{start_address:08X}",
        "expectedCrc": f"0x{expected_crc:08X}",
        "observedCrcWithoutLast4": f"0x{observed_crc:08X}",
    }


def _apply_pk4_application_image(driver, bundle: FirmwareBundle) -> Dict[str, object]:
    start_address, image, expected_crc = _build_pk4_pfm_image(bundle.payload_path)
    _erase_flash(driver, boot=False)
    address = start_address
    for offset in range(0, len(image), PK4_PFM_ROW_SIZE):
        _write_flash_row(driver, address, image[offset : offset + PK4_PFM_ROW_SIZE], timeout_ms=60_000)
        address += PK4_PFM_ROW_SIZE
    observed_crc = _get_pfm_crc(driver)
    if observed_crc != expected_crc:
        raise RuntimeError(f"PK4 application CRC mismatch: expected 0x{expected_crc:08X}, observed 0x{observed_crc:08X}")
    _jump_to_app(driver)
    return {
        "payloadPath": str(bundle.payload_path),
        "payloadVersion": bundle.payload_version,
        "startAddress": f"0x{start_address:08X}",
        "expectedCrc": f"0x{expected_crc:08X}",
        "observedCrc": f"0x{observed_crc:08X}",
    }


def apply_tool_firmware(tool: str, vid: int, pid: int, *, jam_path: Optional[Path] = None, mode: str = "app") -> Dict[str, object]:
    normalized_tool = str(tool).strip().lower()
    if normalized_tool != "pk4":
        raise RuntimeError("Firmware apply is currently implemented only for PK4")

    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in {"app", "boot"}:
        raise RuntimeError(f"Unsupported PK4 firmware apply mode: {mode}")

    payload_name = PK4_APP_FILE_NAME if normalized_mode == "app" else PK4_BOOT_FILE_NAME
    bundle = _resolve_bundle(normalized_tool, payload_name=payload_name, jam_path=jam_path)
    driver = _open_driver(normalized_tool, vid, pid)
    initial_info = None
    try:
        initial_info = read_native_firmware_info(driver)
    finally:
        driver.close()

    stage = "bootloader"
    active_pid = pid
    if initial_info is None or not initial_info.boot_mode:
        stage = "entering-bootloader"
        driver = _open_driver(normalized_tool, vid, pid)
        try:
            _enter_upgrade_mode(driver)
        finally:
            driver.close()
        active_pid = _wait_for_pid(vid, PK4_BOOT_PID, timeout_s=10.0)

    driver = _open_driver(normalized_tool, vid, active_pid)
    try:
        boot_info = read_native_firmware_info(driver)
        if not boot_info.boot_mode:
            raise RuntimeError("Tool did not enter bootloader mode before application update")
        if normalized_mode == "app":
            apply_result = _apply_pk4_application_image(driver, bundle)
        else:
            apply_result = _apply_pk4_boot_image(driver, bundle, boot_info)
    finally:
        driver.close()

    final_pid = _wait_for_pid(vid, pid, timeout_s=15.0)
    final_state = probe_tool_firmware(normalized_tool, vid, final_pid)
    return {
        "tool": normalized_tool.upper(),
        "vid": f"0x{vid:04X}",
        "initialPid": f"0x{pid:04X}",
        "activePid": f"0x{active_pid:04X}",
        "finalPid": f"0x{final_pid:04X}",
        "mode": normalized_mode,
        "stage": stage,
        "bundle": {
            "jamPath": str(bundle.jam_path),
            "payloadPath": str(bundle.payload_path),
            "payloadName": bundle.payload_name,
            "payloadVersion": bundle.payload_version,
        },
        "apply": apply_result,
        "finalState": final_state.to_dict(),
    }


def assess_firmware_state(
    tool: str,
    status: Optional[Dict[str, str]],
    *,
    native_info: Optional[NativeFirmwareInfo] = None,
    error: str = "",
) -> ToolFirmwareState:
    selected = resolve_repo_firmware_path(tool)
    selected_version = ""
    if selected is not None:
        from .repo_assets import _parse_jam_filename  # local import to keep module surface small

        _, selected_version = _parse_jam_filename(selected)

    if status is None:
        return ToolFirmwareState(
            tool=str(tool).upper(),
            reachable=False,
            selected_firmware_path="" if selected is None else str(selected),
            selected_firmware_version=selected_version,
            state="communication-failed",
            recommendation="use-vendored-recovery-firmware",
            reason=error or "Unable to query tool firmware status over RI4.",
        )

    current = _format_version(status.get("MajorFirmwareVersion", ""), status.get("MinorFirmwareVersion", ""))
    packaged = _format_version(status.get("MajorFirmwareVersionOnDisk", ""), status.get("MinorFirmwareVersionOnDisk", ""))
    if native_info is not None and native_info.application_version:
        current = native_info.application_version if not native_info.boot_mode else native_info.boot_version
    reason = ""
    recommendation = "none"
    state = "healthy"
    if not current:
        state = "unknown"
        recommendation = "inspect-tool-status"
        reason = "Tool did not report a current firmware version."
    elif native_info is not None and native_info.boot_mode:
        state = "bootloader-mode"
        recommendation = "use-vendored-recovery-firmware"
        reason = "Tool is responding in bootloader mode and should be recovered with the vendored firmware image."
    elif packaged and current != packaged:
        state = "update-recommended"
        recommendation = "apply-vendored-firmware-on-next-connect"
        reason = f"Tool firmware {current} differs from packaged firmware {packaged}."
    elif selected_version and packaged and packaged.replace('.', '') != selected_version:
        state = "toolpack-firmware-mismatch"
        recommendation = "use-selected-vendored-firmware"
        reason = f"Vendored firmware image {selected_version} differs from toolpack reported version {packaged}."
    else:
        reason = "Tool firmware matches the vendored default package."
    if native_info is not None and not native_info.hardware_bootloader_update_supported and recommendation == "apply-vendored-firmware-on-next-connect":
        recommendation = "recovery-may-require-external-tool"
        reason = "Tool firmware is outdated and does not advertise bootloader-update support in app mode."

    return ToolFirmwareState(
        tool=str(tool).upper(),
        reachable=True,
        current_version=current,
        packaged_version=packaged,
        hardware_revision=status.get("HardwareRevision", ""),
        commands_in_progress=status.get("Commands in progress", ""),
        selected_firmware_path="" if selected is None else str(selected),
        selected_firmware_version=selected_version,
        application_version="" if native_info is None else native_info.application_version,
        boot_version="" if native_info is None else native_info.boot_version,
        boot_mode=None if native_info is None else native_info.boot_mode,
        bootloader_update_supported=None if native_info is None else native_info.hardware_bootloader_update_supported,
        state=state,
        recommendation=recommendation,
        reason=reason,
    )


def probe_tool_firmware(tool: str, vid: int, pid: int) -> ToolFirmwareState:
    driver = _open_driver(tool, vid, pid)
    try:
        status: Dict[str, str] = {}
        native_info = None
        try:
            native_info = read_native_firmware_info(driver)
        except Exception:
            native_info = None
        for key in FIRMWARE_STATUS_KEYS:
            status[key] = driver.get_status_value(key)
        return assess_firmware_state(tool, status, native_info=native_info)
    except Exception as exc:
        return assess_firmware_state(tool, None, error=str(exc))
    finally:
        driver.close()


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect vendored PK4/ICD4 firmware packages and assess firmware recovery/update state")
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser("inventory", help="List vendored firmware update packages")
    inventory.add_argument("--tool", choices=("pk4", "icd4"), default="")

    probe = sub.add_parser("probe", help="Probe the connected tool and compare its firmware version to the vendored default")
    probe.add_argument("--tool", choices=("pk4", "icd4"), required=True)
    probe.add_argument("--vid", default="0x04D8")
    probe.add_argument("--pid", default="")

    apply_cmd = sub.add_parser("apply", help="Apply the PK4 application firmware using the vendored package metadata and companion hex payload")
    apply_cmd.add_argument("--tool", choices=("pk4",), required=True)
    apply_cmd.add_argument("--vid", default="0x04D8")
    apply_cmd.add_argument("--pid", default="")
    apply_cmd.add_argument("--jam", default="")
    apply_cmd.add_argument("--mode", choices=("app", "boot"), default="app")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "inventory":
        packages = iter_repo_firmware_packages()
        if str(args.tool).strip():
            packages = [package for package in packages if package["tool"] == str(args.tool).upper()]
        print(json.dumps({"packages": packages}, indent=2, sort_keys=True))
        return 0

    vid = int(str(args.vid), 0)
    pid = int(str(args.pid), 0) if str(args.pid).strip() else _discover_pid(vid)
    if args.command == "apply":
        result = apply_tool_firmware(
            str(args.tool),
            vid,
            pid,
            jam_path=Path(str(args.jam)) if str(args.jam).strip() else None,
            mode=str(args.mode),
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    result = probe_tool_firmware(str(args.tool), vid, pid)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())