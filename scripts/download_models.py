# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""
Unified script for downloading and exporting YOLO and MiDaS models.

Examples:
    # Download models to default locations
    python scripts/download_models.py --download-only

    # Download and export to ONNX
    python scripts/download_models.py --export-onnx
    
    # Custom paths
    python scripts/download_models.py --yolo-model my_yolo.pt --output-dir ./dist
"""
import argparse
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Add src/backend to sys.path to allow importing common
script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent
backend_path = project_root / "src" / "backend"

if not backend_path.exists():
    # If running from backend dir directly
    if Path.cwd().name == "backend":
        backend_path = Path.cwd()

sys.path.insert(0, str(backend_path))

try:
    from common.config import config
    from common.core.model_downloader import (
        ensure_midas_model_available,
        ensure_yolo_model_downloaded,
        export_midas_to_onnx,
        export_yolo_to_onnx,
        DEFAULT_MIDAS_MODEL,
        DEFAULT_MIDAS_REPO,
    )
except ImportError as e:
    logger.error("Failed to import backend modules: %s", e)
    logger.error("Please run this script from the project root or src/backend.")
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and export ML models")
    
    # Actions
    parser.add_argument(
        "--export-onnx",
        action="store_true",
        help="Export downloaded models to ONNX",
    )
    
    # YOLO Options
    parser.add_argument(
        "--yolo-model",
        type=str,
        default="yolo11n.pt",
        help="YOLO model path or name (default: yolo11n.pt)",
    )
    parser.add_argument(
        "--yolo-onnx-output",
        type=Path,
        help="Custom output path for YOLO ONNX model",
    )
    
    # MiDaS Options
    midas_group = parser.add_argument_group('MiDaS options')
    midas_group.add_argument(
        "--midas-type",
        "--midas-model-type",
        dest="midas_type",
        type=str,
        default=DEFAULT_MIDAS_MODEL,
        choices=["MiDaS_small", "DPT_Hybrid", "DPT_Large"],
        help="Type of MiDaS model to use",
    )
    midas_group.add_argument(
        "--midas-repo",
        type=str,
        default=DEFAULT_MIDAS_REPO,
        help="Repository for MiDaS model",
    )
    midas_group.add_argument(
        "--midas-cache",
        type=Path,
        default=None,
        help="Directory to cache MiDaS model files. Defaults to config if not set.",
    )
    midas_group.add_argument(
        "--midas-onnx-output",
        type=Path,
        help="Custom output path for MiDaS ONNX model",
    )
    
    # General Options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "models",
        help="Base directory for downloaded models (default: ./models)",
    )
    
    # ONNX Options
    parser.add_argument("--onnx-opset", type=int, default=18, help="ONNX opset version")
    parser.add_argument("--onnx-simplify", action="store_true", default=True)
    parser.add_argument("--no-onnx-simplify", action="store_false", dest="onnx_simplify")

    parser.add_argument(
        "--models",
        type=str,
        default="yolo,midas",
        help="Comma-separated list of models to process (default: yolo,midas)",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    models_to_process = [m.strip().lower() for m in args.models.split(",")]
    midas_cache_final = None
    
    # --- YOLO Processing ---
    if "yolo" in models_to_process:
        # Determine YOLO paths
        # If args.yolo_model is a path, use it. If it's a name, combine with output_dir.
        if Path(args.yolo_model).is_absolute() or Path(args.yolo_model).parent.name:
             # Provided as path
             yolo_target = Path(args.yolo_model).resolve()
        else:
             # Provided as name, save to output_dir
             yolo_target = output_dir / args.yolo_model

        logger.info("--- Processing YOLO ---")
        yolo_final_path = ensure_yolo_model_downloaded(
            model_name=yolo_target.name,
            cache_dir=yolo_target.parent,
        )
        
        if args.export_onnx:
            if args.yolo_onnx_output:
                yolo_onnx_target = args.yolo_onnx_output.resolve()
            else:
                yolo_onnx_target = yolo_final_path.with_suffix(".onnx")
                
            export_yolo_to_onnx(
                yolo_path=yolo_final_path,
                output_path=yolo_onnx_target,
                opset=args.onnx_opset,
                simplify=args.onnx_simplify
            )

    # --- MiDaS Processing ---
    if "midas" in models_to_process:
        logger.info("\n--- Processing MiDaS ---")
        
        midas_cache = args.midas_cache
        if midas_cache is None:
            # Use config default if available, otherwise defaults to hub cache
            # config.MIDAS_CACHE_DIR is set in config.py
            try:
                 midas_cache = config.MIDAS_CACHE_DIR
            except Exception:
                 pass
                 
        midas_cache_final = ensure_midas_model_available(
            model_type=args.midas_type,
            midas_repo=args.midas_repo,
            cache_dir=midas_cache,
        )
        
        if args.export_onnx:
            if args.midas_onnx_output:
                midas_onnx_target = args.midas_onnx_output.resolve()
            else:
                midas_onnx_target = output_dir / f"{args.midas_type.lower()}.onnx"

            export_midas_to_onnx(
                cache_dir=midas_cache_final,
                output_path=midas_onnx_target,
                model_type=args.midas_type,
                model_repo=args.midas_repo,
                opset=args.onnx_opset,
            )

    logger.info("\n--- Done ---")
    logger.info("Models available at: %s", output_dir)
    if midas_cache_final:
        logger.info("MiDaS Cache: %s", midas_cache_final)


if __name__ == "__main__":
    main()
