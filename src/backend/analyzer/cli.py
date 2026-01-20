# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import argparse
import logging
from pathlib import Path

import uvicorn

from analyzer.main import create_app


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_analyzer_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the analyzer service.

    Returns:
        Parsed arguments namespace with yolo_model_path, midas_model_path, etc.
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

    # Create app with provided paths (or None to use defaults/config)
    yolo_path = Path(args.yolo_model_path) if args.yolo_model_path else None
    midas_path = Path(args.midas_model_path) if args.midas_model_path else None

    # Note: We rely on the app lifespan (and underlying libraries) to handle
    # model downloading if files are missing.
    app = create_app(yolo_model_path=yolo_path, midas_cache_directory=midas_path)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
