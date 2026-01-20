# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np


class DummyResult:
    def __init__(self, boxes):
        self.boxes = boxes
        self.masks = None  # No masks for simplicity


class DummyArray:
    def __init__(self, arr):
        self._arr = np.array(arr)

    def cpu(self):
        return self

    def numpy(self):
        return self._arr


class DummyBoxes:
    def __init__(self, xyxy, cls, conf):
        self.xyxy = DummyArray(xyxy)
        self.cls = DummyArray(cls)
        self.conf = DummyArray(conf)

    def __len__(self):
        arr = self.xyxy.numpy()
        return 0 if arr.size == 0 else arr.shape[0]
