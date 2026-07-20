import argparse

from mchp_gdbrsp import GdbRemoteClient


def main() -> int:
    ap = argparse.ArgumentParser(description="Minimal GDB RSP client demo (OpenOCD gdb_port)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3333)
    ap.add_argument("--addr", default="0", help="hex address to read")
    ap.add_argument("--len", dest="length", default="16", help="hex length to read")
    args = ap.parse_args()

    addr = int(args.addr, 16)
    length = int(args.length, 16)

    with GdbRemoteClient(host=args.host, port=args.port) as c:
        caps = c.qSupported()
        data = c.read_memory(addr, length)

    print(f"Connected: {args.host}:{args.port}")
    print(f"qSupported keys: {sorted(list(caps.keys()))[:10]}")
    print(f"m{addr:x},{length:x} -> {data.hex()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
