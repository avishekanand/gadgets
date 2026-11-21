"""CLI: `python -m dashboard render|panels|serve [--config PATH]`."""
from __future__ import annotations

import argparse
from datetime import datetime

from dashboard.config import load_config
from dashboard.service import render_once, render_panels, serve


def main() -> None:
    ap = argparse.ArgumentParser(prog="dashboard")
    ap.add_argument("cmd", choices=["render", "panels", "serve"])
    ap.add_argument("--config", default=None, help="path to config.toml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.cmd == "render":
        path = render_once(cfg, datetime.now())
        print(f"wrote {path}")
    elif args.cmd == "panels":
        for p in render_panels(cfg, datetime.now()):
            print(f"wrote {p}")
    else:
        print(f"serving {cfg.out_dir} on {cfg.server_host}:{cfg.server_port}")
        serve(cfg)


if __name__ == "__main__":
    main()
