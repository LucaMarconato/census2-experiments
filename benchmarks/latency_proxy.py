#!/usr/bin/env python3
"""TCP proxy on 127.0.0.1 that delays each HTTP request by a fixed time, to mimic S3 latency.

With --count-file it also keeps the number of requests seen so far in that file: the true
number of storage round trips of whatever runs through it.

    python benchmarks/latency_proxy.py --listen 4567 --target 4566 --delay-ms 10
"""

import argparse
import asyncio
from pathlib import Path

METHODS = (b"GET ", b"HEAD", b"PUT ", b"POST", b"DELE", b"OPTI")


seen = 0


async def pipe(reader, writer, delay: float | None, count_file: Path | None = None) -> None:
    """Copy bytes one way. `delay` is None for responses: they are neither delayed nor counted."""
    global seen
    try:
        while data := await reader.read(1 << 16):
            if delay is not None and data[:4] in METHODS:  # a new request on this connection: one round trip
                seen += 1
                if count_file:
                    count_file.write_text(str(seen))
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
    p.add_argument("--count-file", type=Path, help="keep the number of requests seen in this file")
    a = p.parse_args()

    async def handle(cr, cw):
        sr, sw = await asyncio.open_connection("127.0.0.1", a.target)
        await asyncio.gather(pipe(cr, sw, a.delay_ms / 1000, a.count_file), pipe(sr, cw, None))

    server = await asyncio.start_server(handle, "127.0.0.1", a.listen)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
