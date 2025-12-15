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


def get_midas_model_config(model_type: str) -> tuple[int, str]:
    """Get configuration for different MiDaS model types.
    
    Args:
        model_type: Type of MiDaS model (e.g., 'MiDaS_small', 'DPT_Hybrid', 'DPT_Large')
        
    Returns:
        Tuple of (input_size, onnx_filename)
    """
    config = {
        "MiDaS_small": (384, "midas_small.onnx"),
        "DPT_Hybrid": (384, "dpt_hybrid.onnx"),
        "DPT_Large": (384, "dpt_large.onnx"),
    }
    return config.get(model_type, (384, f"{model_type.lower()}.onnx"))


def export_midas_to_onnx(
    cache_dir: Path,
    output_dir: Path,
    model_type: str = "MiDaS_small",
    model_repo: str = "intel-isl/MiDaS"
) -> Path:
    """Export MiDaS model to ONNX format.
    
    Args:
        cache_dir: Directory with cached model
        output_dir: Directory to save ONNX model
        model_type: Type of MiDaS model to export
        model_repo: Repository for the MiDaS model
        
    Returns:
        Path to the exported ONNX model
    """
    logger.info("Exporting %s model to ONNX...", model_type)
    try:
        torch.hub.set_dir(str(cache_dir))
        model = torch.hub.load(model_repo, model_type, trust_repo=True)
        model.eval()

        input_size, onnx_filename = get_midas_model_config(model_type)
        onnx_path = output_dir / onnx_filename
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
        
        logger.info("%s ONNX model ready at: %s", model_type, onnx_path)
        return onnx_path
    except Exception as e:
        logger.error("Failed to export %s to ONNX: %s", model_type, e)
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
    
    # Model options
    parser.add_argument(
        "--midas-type",
        type=str,
        default="MiDaS_small",
        choices=["MiDaS_small", "DPT_Hybrid", "DPT_Large"],
        help="Type of MiDaS model to download (default: MiDaS_small)",
    )
    parser.add_argument(
        "--midas-repo",
        type=str,
        default="intel-isl/MiDaS",
        help="Repository for MiDaS model (default: intel-isl/MiDaS)",
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
    
    logger.info("Downloading %s model...", args.midas_type)
    midas_cache = ensure_midas_model_available(
        model_type=args.midas_type,
        midas_repo=args.midas_repo,
        cache_directory=midas_cache
    )
    
    # Export to ONNX if requested
    yolo_onnx_path = None
    midas_onnx_path = None
    
    if args.export_onnx:
        logger.info("Exporting models to ONNX...")
        yolo_onnx_path = export_yolo_to_onnx(yolo_path, args.output_dir)
        midas_onnx_path = export_midas_to_onnx(
            cache_dir=midas_cache,
            output_dir=args.output_dir,
            model_type=args.midas_type,
            model_repo=args.midas_repo
        )
    
    print_summary(yolo_path, midas_cache, yolo_onnx_path, midas_onnx_path)


if __name__ == "__main__":
    main()
