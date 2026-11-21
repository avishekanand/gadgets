"""CLI: `python -m dashboard render|serve [--config PATH]`."""
from __future__ import annotations

import argparse
from datetime import datetime

from dashboard.config import load_config
from dashboard.service import render_once, serve


def main() -> None:
    ap = argparse.ArgumentParser(prog="dashboard")
    ap.add_argument("cmd", choices=["render", "serve"])
    ap.add_argument("--config", default=None, help="path to config.toml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.cmd == "render":
        path = render_once(cfg, datetime.now())
        print(f"wrote {path}")
    else:
        print(f"serving {cfg.out_dir} on {cfg.server_host}:{cfg.server_port}")
        serve(cfg)


if __name__ == "__main__":
    main()
