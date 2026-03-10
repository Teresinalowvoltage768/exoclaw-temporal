"""Entry point: python -m exoclaw_temporal.session_based"""

from __future__ import annotations

import asyncio
import sys


def main() -> None:
    if "--worker" in sys.argv:
        from exoclaw_temporal.session_based.worker import run_worker

        temporal_url = _get_arg("--temporal-url", "localhost:7233")
        asyncio.run(run_worker(temporal_url))
    else:
        asyncio.run(_run_cli())


async def _run_cli() -> None:
    from exoclaw_temporal.session_based.app import create

    temporal_url = _get_arg("--temporal-url", "localhost:7233")
    bot = await create(temporal_url=temporal_url)
    await bot.run_cli()


def _get_arg(flag: str, default: str) -> str:
    args = sys.argv
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
    return default


if __name__ == "__main__":
    main()
