# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""CLI helper to download analyzer models without starting the backend."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from common.core.model_downloader import ensure_midas_model_available, ensure_yolo_model_downloaded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download YOLO and MiDaS models into the desired directories.",
    )
    parser.add_argument(
        "--yolo-path",
        default=os.getenv("YOLO_MODEL_PATH", "models/yolov8n.pt"),
        help="Full path (including filename) where the YOLO .pt model should be stored.",
    )
    parser.add_argument(
        "--midas-cache",
        default=os.getenv("MIDAS_CACHE_PATH"),  # falls back to torch default if empty
        help="Destination directory for MiDaS weights (defaults to torch hub cache).",
    )
    parser.add_argument(
        "--skip-midas",
        action="store_true",
        help="Skip downloading MiDaS weights.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    yolo_path = Path(args.yolo_path).expanduser().resolve()
    yolo_path.parent.mkdir(parents=True, exist_ok=True)
    ensure_yolo_model_downloaded(
        model_name=yolo_path.name,
        cache_directory=yolo_path.parent,
    )

    if not args.skip_midas:
        default_midas_dir = Path("models/midas_cache")
        midas_cache = (
            Path(args.midas_cache).expanduser().resolve()
            if args.midas_cache
            else default_midas_dir.resolve()
        )
        midas_cache.mkdir(parents=True, exist_ok=True)
        ensure_midas_model_available(cache_directory=midas_cache)


if __name__ == "__main__": 
    main()

