# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple

import torch
from ultralytics import YOLO  # type: ignore[import-untyped]

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Project paths
script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent
backend_path = project_root / "src" / "backend"

# Handle different working directories
if Path.cwd().name == "backend" and (Path.cwd() / "common").exists():
    backend_path = Path.cwd()

sys.path.insert(0, str(backend_path))

from common.core.model_downloader import (
    ensure_midas_model_available,
    ensure_yolo_model_downloaded,
)

# Constants
DEFAULT_MODEL_DIR = project_root / "models"
DEFAULT_MIDAS_MODEL = "MiDaS_small"


def export_yolo_to_onnx(yolo_path: Path, output_dir: Path) -> Path:
    """Export YOLO model to ONNX format.
    
    Args:
        yolo_path: Path to the YOLO model file
        output_dir: Directory to save the exported ONNX model
        
    Returns:
        Path to the exported ONNX model
    """
    logger.info("Exporting YOLO model to ONNX...")
    try:
        model = YOLO(str(yolo_path))
        onnx_path = output_dir / "yolo11n.onnx"
        
        model.export(
            format="onnx",
            imgsz=640,
            opset=18,
            simplify=True,
            dynamic=True,
            batch=True,
            name=onnx_path.stem,
            project=str(onnx_path.parent),
        )
        
        logger.info("YOLO ONNX model ready at: %s", onnx_path)
        return onnx_path
    except Exception as e:
        logger.error("Failed to export YOLO to ONNX: %s", e)
        sys.exit(1)


def export_midas_to_onnx(cache_dir: Path, output_dir: Path) -> Path:
    """Export MiDaS model to ONNX format.
    
    Args:
        cache_dir: Directory with cached model
        output_dir: Directory to save ONNX model
        
    Returns:
        Path to the exported ONNX model
    """
    logger.info("Exporting MiDaS model to ONNX...")
    try:
        torch.hub.set_dir(str(cache_dir))
        model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", trust_repo=True)
        model.eval()

        input_size = 384  # Standard input size for MiDaS
        onnx_path = output_dir / "midas_small.onnx"
        onnx_path.parent.mkdir(parents=True, exist_ok=True)
        
        dummy_input = torch.randn(1, 3, input_size, input_size)
        
        torch.onnx.export(
            model,
            dummy_input,
            str(onnx_path),
            export_params=True,
            opset_version=18,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={
                "input": {0: "batch_size", 2: "height", 3: "width"},
                "output": {0: "batch_size", 2: "height", 3: "width"}
            },
        )
        
        logger.info("MiDaS ONNX model ready at: %s", onnx_path)
        return onnx_path
    except Exception as e:
        logger.error("Failed to export MiDaS to ONNX: %s", e)
        sys.exit(1)


def print_summary(
    yolo_path: Path,
    midas_cache_dir: Path,
    yolo_onnx_path: Optional[Path] = None,
    midas_onnx_path: Optional[Path] = None,
) -> None:
    """Print summary of downloaded models and their locations."""
    logger.info("\n=== Model Summary ===")
    logger.info("YOLO model: %s", yolo_path)
    if yolo_onnx_path:
        logger.info("YOLO ONNX model: %s", yolo_onnx_path)
    
    logger.info("\nMiDaS cache: %s", midas_cache_dir)
    if midas_onnx_path:
        logger.info("MiDaS ONNX model: %s", midas_onnx_path)
    logger.info("=" * 40 + "\n")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Download and export ML models")
    
    # Model paths
    parser.add_argument(
        "--yolo-model",
        type=Path,
        help="Path to save YOLO model (default: <output-dir>/yolo11n.pt)",
    )
    parser.add_argument(
        "--midas-cache",
        type=Path,
        help="Directory to cache MiDaS model (default: <output-dir>/midas_cache)",
    )
    
    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_MODEL_DIR,
        help="Base directory for model outputs (default: ./models)",
    )
    parser.add_argument(
        "--export-onnx",
        action="store_true",
        help="Export models to ONNX format",
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point for model management."""
    args = parse_args()
    
    # Setup paths
    args.output_dir.mkdir(parents=True, exist_ok=True)
    yolo_path = args.yolo_model or args.output_dir / "yolo11n.pt"
    midas_cache = args.midas_cache or args.output_dir / "midas_cache"
    
    # Download models
    logger.info("Downloading YOLO model...")
    yolo_path = ensure_yolo_model_downloaded(
        model_name=yolo_path.name,
        cache_dir=yolo_path.parent,
    )
    
    logger.info("Downloading MiDaS model...")
    midas_cache = ensure_midas_model_available(cache_dir=midas_cache)
    
    # Export to ONNX if requested
    yolo_onnx_path = None
    midas_onnx_path = None
    
    if args.export_onnx:
        logger.info("Exporting models to ONNX...")
        yolo_onnx_path = export_yolo_to_onnx(yolo_path, args.output_dir)
        midas_onnx_path = export_midas_to_onnx(
            midas_cache,
            args.output_dir
        )
    
    print_summary(yolo_path, midas_cache, yolo_onnx_path, midas_onnx_path)


if __name__ == "__main__":
    main()
