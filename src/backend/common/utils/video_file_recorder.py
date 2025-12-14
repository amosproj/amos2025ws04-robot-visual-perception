# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

import cv2
import signal
import sys
import time
from typing import Any

# general settings
OUTPUT_FILE = "video.mp4"
FPS = 30
CAMERA_INDEX = 0
WARMUP_FRAMES = 20

running = True


def signal_handler(sig: int, frame: Any) -> None:
    global running
    print("\nStopping recording...")
    running = False


signal.signal(signal.SIGINT, signal_handler)

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
if not cap.isOpened():
    print("Could not open camera")
    sys.exit(1)

# camera settings
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, FPS)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# camera warm-up
print("Warming up camera...")
for _ in range(WARMUP_FRAMES):
    cap.read()
    time.sleep(0.05)

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

fourcc = cv2.VideoWriter.fourcc(*"mp4v")  # type: ignore[attr-defined]
out = cv2.VideoWriter(OUTPUT_FILE, fourcc, FPS, (width, height))
if not out.isOpened():
    print("Could not open VideoWriter")
    sys.exit(1)

print("Recording started...")
print("Press Ctrl+C to stop")

while running:
    ret, frame = cap.read()
    if not ret:
        print("Frame drop: Retrying")
        time.sleep(0.01)
        continue

    out.write(frame)

cap.release()
out.release()
print(f"Video saved as: {OUTPUT_FILE}")
