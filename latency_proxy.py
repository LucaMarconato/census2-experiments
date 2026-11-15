#!/usr/bin/env python3
"""TCP proxy on 127.0.0.1 that delays each HTTP request by a fixed time, to mimic S3 latency.

    python3 latency_proxy.py --listen 4567 --target 4566 --delay-ms 10
"""

import argparse
import asyncio

METHODS = (b"GET ", b"HEAD", b"PUT ", b"POST", b"DELE", b"OPTI")


async def pipe(reader, writer, delay: float) -> None:
    try:
        while data := await reader.read(1 << 16):
            if delay and data[:4] in METHODS:  # a new request on this connection: one round trip
                await asyncio.sleep(delay)
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        writer.close()


async def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--listen", type=int, default=4567)
    p.add_argument("--target", type=int, default=4566)
    p.add_argument("--delay-ms", type=float, default=10)
    a = p.parse_args()

    async def handle(cr, cw):
        sr, sw = await asyncio.open_connection("127.0.0.1", a.target)
        await asyncio.gather(pipe(cr, sw, a.delay_ms / 1000), pipe(sr, cw, 0))

    server = await asyncio.start_server(handle, "127.0.0.1", a.listen)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
