# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""Download YOLO and MiDaS models for the analyzer service."""
import sys
from pathlib import Path

script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent
backend_path = project_root / "src" / "backend"

if Path.cwd().name == "backend" and (Path.cwd() / "common").exists():
    backend_path = Path.cwd()

sys.path.insert(0, str(backend_path))

from common.core.model_downloader import (
    ensure_midas_model_available,
    ensure_yolo_model_downloaded,
)


def main() -> None:
    """Download YOLO and MiDaS models."""
    models_dir = backend_path / "models"
    yolo_model_path = models_dir / "yolov8n.pt"
    midas_cache_dir = models_dir / "midas_cache"

    print("Downloading YOLO model...")
    try:
        yolo_path = ensure_yolo_model_downloaded(
            model_name="yolov8n.pt",
            cache_directory=models_dir,
        )
        print(f"YOLO model ready at: {yolo_path}")
    except Exception as e:
        print(f"Failed to download YOLO model: {e}")
        sys.exit(1)

    print("Downloading MiDaS model...")
    try:
        ensure_midas_model_available(cache_directory=midas_cache_dir)
        print(f"MiDaS model cached in: {midas_cache_dir}")
    except Exception as e:
        print(f"Failed to download MiDaS model: {e}")
        sys.exit(1)

    print("All models downloaded successfully.")
    print(f"YOLO model: {yolo_model_path}")
    print(f"MiDaS cache: {midas_cache_dir}")


if __name__ == "__main__":
    main()

