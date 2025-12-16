# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple

import uvicorn
from common.core.model_downloader import (
    ensure_midas_model_available,
    ensure_yolo_model_downloaded,
    get_midas_cache_dir,
)

from analyzer.main import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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

    def validate_path(
        path_str: Optional[str], is_dir: bool = False
    ) -> Tuple[Optional[Path], bool]:
        """Validate a path and return the resolved Path object and validation status.

        Args:
            path_str: The path string to validate. If None or empty string, returns (None, True).
            is_dir: If True, validates as a directory; otherwise as a file.

        Returns:
            Tuple of (resolved Path object or None, validation success status).
            Returns (None, True) if path_str is None or empty.
        """
        if not path_str:
            return None, True

        path = Path(path_str).resolve()

        # In dev mode, ensure parent directory exists for files, create directory if it's a directory
        if args.dev:
            if is_dir:
                path.mkdir(parents=True, exist_ok=True)
            else:
                # For files, ensure parent directory exists
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    logger.warning(f"File does not exist but will be created: {path}")
            return path, True

        # In non-dev mode, validate path existence and type
        if not path.exists():
            path_type = "directory" if is_dir else "file"
            logger.error(f"{path_type.capitalize()} does not exist: {path}")
            logger.info(
                "Hint: Use --dev flag to automatically download models, or provide a valid path."
            )
            return None, False

        if (is_dir and not path.is_dir()) or (not is_dir and path.is_dir()):
            expected = "directory" if is_dir else "file"
            actual = "directory" if path.is_dir() else "file"
            logger.error(f"Expected a {expected}, but got a {actual}: {path}")
            return None, False

        return path, True

    # Validate YOLO model path
    yolo_model_path, is_valid = validate_path(args.yolo_model_path, is_dir=False)
    if not is_valid:
        sys.exit(1)

    # Validate MiDaS model path
    midas_cache_directory, is_valid = validate_path(args.midas_model_path, is_dir=True)
    if not is_valid:
        sys.exit(1)

    if args.dev:
        logger.info("Development mode: Ensuring models are downloaded and cached...")
        if yolo_model_path is None:
            yolo_model_path = ensure_yolo_model_downloaded()
        else:
            if not yolo_model_path.exists():
                logger.info(
                    f"YOLO model not found at {yolo_model_path}, downloading..."
                )
                yolo_model_path.parent.mkdir(parents=True, exist_ok=True)
                yolo_model_path = ensure_yolo_model_downloaded(
                    model_name=yolo_model_path.name,
                    cache_dir=yolo_model_path.parent,
                )

        if midas_cache_directory is None:
            midas_cache_directory = get_midas_cache_dir()

        try:
            midas_cache_directory = ensure_midas_model_available(
                cache_dir=midas_cache_directory
            )
            logger.info("MiDaS model is ready at %s", midas_cache_directory)
        except RuntimeError as e:
            logger.error("Failed to download or load the MiDaS model: %s", e)
            logger.error("Please check your internet connection and try again.")
            sys.exit(1)

    app = create_app(yolo_model_path, midas_cache_directory)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
