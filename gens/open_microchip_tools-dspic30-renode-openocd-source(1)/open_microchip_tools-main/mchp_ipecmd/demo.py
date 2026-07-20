from __future__ import annotations

import argparse

from .client import IpecmdClient
from .server import IpecmdServer


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="mchp_ipecmd demo")
    p.add_argument("command", nargs="*", default=["PING"], help="Command args (sent as # delimited line)")
    args = p.parse_args(argv)

    with IpecmdServer(host="127.0.0.1", port=0) as srv:
        client = IpecmdClient(host="127.0.0.1", port=srv.port)
        res = client.send(args.command)

    for line in res.lines:
        print(line)
    print(f"ERRORCODE:{res.error_code}")
    return int(res.error_code)


if __name__ == "__main__":
    raise SystemExit(main())
