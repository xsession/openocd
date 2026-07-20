from __future__ import annotations

from mchp_ri4.ri4_com import Ri4Com
from mchp_ri4.transport import PyusbTransport
from mchp_ri4.icd4_comms_usb import ICD4CommsUsb


def main() -> int:
    # Example only: replace VID/PID with your actual tool.
    transport = PyusbTransport(vid=0x04D8, pid=0x9012)
    com = Ri4Com(transport)
    icd = ICD4CommsUsb(com)
    print(icd.get_status_value_from_key("Commands in progress"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
