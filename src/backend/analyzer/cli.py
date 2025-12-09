# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import argparse
import sys
from pathlib import Path
from typing import Optional

import uvicorn

from analyzer.main import create_app


def parse_analyzer_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the analyzer service.

    Returns:
        Parsed arguments namespace with yolo_model_path, midas_model_path, and dev_mode.
    """
    parser = argparse.ArgumentParser(
        description="Analyzer service for object detection and distance estimation"
    )
    parser.add_argument(
        "--yolo-model-path",
        type=str,
        default=None,
        help="Path to the YOLO model file. If not provided, uses config default.",
    )
    parser.add_argument(
        "--midas-model-path",
        type=str,
        default=None,
        help="Path to the MiDaS model cache directory. If not provided, uses PyTorch Hub default.",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable development mode. Downloads models if not cached.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to bind the server to (default: 8001)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point for the analyzer service CLI."""
    args = parse_analyzer_arguments()

    yolo_model_path: Optional[Path] = None
    if args.yolo_model_path:
        yolo_model_path = Path(args.yolo_model_path).resolve()
        if not args.dev:
            if not yolo_model_path.exists():
                print(f"Error: YOLO model path does not exist: {yolo_model_path}")
                print(
                    "Hint: Use --dev flag to automatically download models, or provide a valid path to an existing model file."
                )
                sys.exit(1)
            if yolo_model_path.is_dir():
                print(
                    f"Error: YOLO model path must be a file, not a directory: {yolo_model_path}"
                )
                sys.exit(1)

    midas_cache_directory: Optional[Path] = None
    if args.midas_model_path:
        midas_cache_directory = Path(args.midas_model_path).resolve()
        if not args.dev:
            if not midas_cache_directory.exists():
                print(
                    f"Error: MiDaS cache directory does not exist: {midas_cache_directory}"
                )
                print(
                    "Hint: Use --dev flag to automatically download models, or provide a valid path to an existing cache directory."
                )
                sys.exit(1)
            if midas_cache_directory.is_file():
                print(
                    f"Error: MiDaS model path must be a directory, not a file: {midas_cache_directory}"
                )
                sys.exit(1)
        else:
            midas_cache_directory.mkdir(parents=True, exist_ok=True)

    if args.dev:
        from common.core.model_downloader import (
            ensure_midas_model_available,
            ensure_yolo_model_downloaded,
        )

        print("Development mode: Ensuring models are downloaded and cached...")
        if yolo_model_path is None:
            yolo_model_path = ensure_yolo_model_downloaded()
        else:
            if not yolo_model_path.exists():
                print(f"YOLO model not found at {yolo_model_path}, downloading...")
                yolo_model_path.parent.mkdir(parents=True, exist_ok=True)
                yolo_model_path = ensure_yolo_model_downloaded(
                    model_name=yolo_model_path.name,
                    cache_directory=yolo_model_path.parent,
                )

        if midas_cache_directory is None:
            from common.core.model_downloader import get_midas_cache_directory

            midas_cache_directory = get_midas_cache_directory()
        ensure_midas_model_available(cache_directory=midas_cache_directory)

    if args.reload:
        """ When using reload, we need to pass the import string and set environment variables """

        uvicorn.run(
            "analyzer.main:app",
            host=args.host,
            port=args.port,
            reload=True,
        )
    else:
        """ Without reload, we can pass the app instance directly """
        app = create_app(yolo_model_path, midas_cache_directory)

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
        )


if __name__ == "__main__":
    main()
