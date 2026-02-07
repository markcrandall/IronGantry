"""CLI for IronGantry — argparse-based, zero external dependencies."""

import argparse
import sys

from irongantry import __version__
from irongantry.engine import IronGantryEngine


def _cmd_version(_args: argparse.Namespace) -> None:
    print(f"IronGantry v{__version__}")


def _cmd_init(args: argparse.Namespace) -> None:
    engine = IronGantryEngine()
    engine.init(args.name)


def _cmd_build(_args: argparse.Namespace) -> None:
    engine = IronGantryEngine()
    engine.build()


def _cmd_run(_args: argparse.Namespace) -> None:
    engine = IronGantryEngine()
    engine.run()


def _cmd_ship(_args: argparse.Namespace) -> None:
    engine = IronGantryEngine()
    engine.ship()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="irongantry",
        description="IronGantry: Security-hardened Python container engine.",
    )
    sub = parser.add_subparsers(dest="command")

    # version
    sub.add_parser("version", help="Print version")

    # init
    p_init = sub.add_parser("init", help="Create an IronGantryfile")
    p_init.add_argument(
        "name",
        nargs="?",
        default="my_app",
        help="Project name (default: my_app)",
    )

    # build
    sub.add_parser("build", help="Create venv and install packages")

    # run
    sub.add_parser("run", help="Execute entrypoint")

    # ship
    sub.add_parser("ship", help="Zip project for distribution")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "version": _cmd_version,
        "init": _cmd_init,
        "build": _cmd_build,
        "run": _cmd_run,
        "ship": _cmd_ship,
    }
    try:
        dispatch[args.command](args)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
