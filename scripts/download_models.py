# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""Download YOLO and MiDaS models for the analyzer service."""
import argparse
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


def download_yolo_model(models_dir: Path) -> Path:
    """Download YOLO model and return its path."""
    print("Downloading YOLO model...")
    try:
        yolo_path = ensure_yolo_model_downloaded(
            model_name="yolo11n.pt",
            cache_directory=models_dir,
        )
        print(f"YOLO model ready at: {yolo_path}")
        return yolo_path
    except Exception as e:
        print(f"Failed to download YOLO model: {e}")
        sys.exit(1)


def export_yolo_to_onnx(yolo_path: Path, output_dir: Path) -> None:
    """Export YOLO model to ONNX format."""
    print("Exporting YOLO model to ONNX...")
    try:
        from ultralytics import YOLO  # type: ignore[import-untyped]

        model = YOLO(str(yolo_path))
        onnx_path = output_dir / "yolo11n.onnx"
        exported_path = model.export(format="onnx", opset=18, imgsz=640, simplify=True)
        exported_path = Path(exported_path).resolve()
        if exported_path != onnx_path:
            onnx_path.parent.mkdir(parents=True, exist_ok=True)
            exported_path.replace(onnx_path)
        print(f"ONNX model ready at: {onnx_path}")
    except Exception as e:
        print(f"Failed to export YOLO to ONNX: {e}")
        sys.exit(1)


def download_midas_model(cache_dir: Path) -> Path:
    """Download MiDaS model and return its cache directory."""
    print("Downloading MiDaS model...")
    # Try to ensure the model is available, but don't fail if it can't be pre-loaded
    # The model will be downloaded on first use if this fails
    ensure_midas_model_available(cache_directory=cache_dir)
    print(f"MiDaS model will be cached in: {cache_dir}")
    return cache_dir


def export_midas_to_onnx(cache_dir: Path, output_dir: Path) -> None:
    """Export MiDaS model to ONNX format."""
    print("Exporting MiDaS model to ONNX...")
    try:
        import torch

        torch.hub.set_dir(str(cache_dir))
        model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", trust_repo=True)
        model.eval()

        dummy_input = torch.randn(1, 3, 384, 384)
        onnx_path = output_dir / "midas_small.onnx"
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
        print(f"MiDaS ONNX model ready at: {onnx_path}")
    except Exception as e:
        print(f"Failed to export MiDaS to ONNX: {e}")
        sys.exit(1)


def print_summary(yolo_path: Path, midas_cache_dir: Path, include_onnx: bool = False) -> None:
    """Print summary of downloaded models and their locations."""
    print("\nAll models downloaded successfully.")
    print(f"YOLO model: {yolo_path}")
    if include_onnx:
        print(f"YOLO ONNX model: {yolo_path.parent / 'yolo11n.onnx'}")
        print(f"MiDaS ONNX model: {yolo_path.parent / 'midas_small.onnx'}")
    print(f"MiDaS cache: {midas_cache_dir}")


def main() -> None:
    """Download YOLO and MiDaS models, with optional ONNX export."""
    parser = argparse.ArgumentParser(description="Download YOLO and MiDaS models")
    parser.add_argument(
        "--onnx",
        action="store_true",
        help="Export YOLO and MiDaS models to ONNX format after downloading",
    )
    args = parser.parse_args()

    models_dir = backend_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    midas_cache_dir = models_dir / "midas_cache"

    # Download base models
    yolo_path = download_yolo_model(models_dir)
    midas_cache_dir = download_midas_model(midas_cache_dir)

    # Export to ONNX if requested
    if args.onnx:
        export_yolo_to_onnx(yolo_path, models_dir)
        export_midas_to_onnx(midas_cache_dir, models_dir)

    # Print summary
    print_summary(yolo_path, midas_cache_dir, include_onnx=args.onnx)


if __name__ == "__main__":
    main()

