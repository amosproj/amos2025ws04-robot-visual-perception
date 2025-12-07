# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""Export a MiDaS model to ONNX with dynamic spatial dimensions.

Environment variables:
    MIDAS_MODEL_REPO: torch.hub repo id (default: intel-isl/MiDaS)
    MIDAS_MODEL_TYPE: MiDaS model type (MiDaS_small, DPT_Hybrid, DPT_Large)
    MIDAS_CACHE_DIR: optional cache directory for torch.hub downloads
    MIDAS_ONNX_MODEL_PATH: output path (default: models/midas_small.onnx)
    MIDAS_ONNX_INPUT_HEIGHT / MIDAS_ONNX_INPUT_WIDTH: dummy input size for export (default: 256 / 256)
    ONNX_OPSET: ONNX opset version (default: 18)
"""

from __future__ import annotations

import os
from pathlib import Path

import torch


def _str_to_bool(value: str) -> bool:
    return value.lower() not in {"false", "0", "no", "off", ""}


def main() -> None:
    model_repo = os.getenv("MIDAS_MODEL_REPO", "intel-isl/MiDaS")
    model_type = os.getenv("MIDAS_MODEL_TYPE", "MiDaS_small")
    cache_dir = os.getenv("MIDAS_CACHE_DIR")
    opset = int(os.getenv("ONNX_OPSET", "18"))
    height = int(os.getenv("MIDAS_ONNX_INPUT_HEIGHT", "256"))
    width = int(os.getenv("MIDAS_ONNX_INPUT_WIDTH", "256"))
    onnx_path = Path(
        os.getenv("MIDAS_ONNX_MODEL_PATH", "models/midas_small.onnx")
    ).resolve()

    if cache_dir:
        cache_path = Path(cache_dir).expanduser().resolve()
        cache_path.mkdir(parents=True, exist_ok=True)
        torch.hub.set_dir(str(cache_path))

    print(f"Loading MiDaS model '{model_type}' from {model_repo}...")
    model = torch.hub.load(model_repo, model_type, trust_repo=True)
    model.eval()

    dummy_input = torch.randn(1, 3, height, width, requires_grad=False)
    onnx_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Exporting to ONNX ({onnx_path}) with opset={opset} ...")
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=opset,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch", 2: "height", 3: "width"},
            "output": {0: "batch", 1: "height", 2: "width"},
        },
    )
    print(f"Export complete: {onnx_path}")
    print(
        "Tip: set MIDAS_ONNX_MODEL_PATH to use a custom output location, "
        "and MIDAS_ONNX_INPUT_HEIGHT/WIDTH if your ONNX runtime forbids 256x256 inputs."
    )


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    main()
