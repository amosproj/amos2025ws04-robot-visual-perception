<!--
SPDX-FileCopyrightText: 2025 robot-visual-perception

SPDX-License-Identifier: CC-BY-4.0
-->

# Camera calibration guide

Step-by-step guide to calibrate the software for a specific camera.

## Why?

The system needs two types of calibration:

1. **Camera intrinsics** which converts 2D pixel coordinates to 3D positions (X, Y, Z)
2. **Depth scale factor** that converts relative depth values to absolute distances in meters

Without calibration, 3D positions and distances will be inaccurate.

## 1. Camera intrinsics

Camera intrinsics describe how the camera projects 3D points onto the 2D image. You need four values:
- `fx`, `fy`: Focal lengths in pixels (horizontal and vertical)
- `cx`, `cy`: Principal point coordinates in pixels (optical center, usually image center)

### Option A: Using known intrinsics

If you have calibrated values from the camera manufacturer or previous calibration:

```bash
export CAMERA_FX=<fx>   
export CAMERA_FY=<fy>  
export CAMERA_CX=<cx>  
export CAMERA_CY=<cy> 
```

**Note:** Values are in pixels, not millimeters.

### Option B: Using field of view (FOV)

If you don't have precise intrinsics, use the camera's FOV from specifications:

```bash
export CAMERA_FOV_X_DEG=<horizontal_fov>
export CAMERA_FOV_Y_DEG=<vertical_fov>
```

The system automatically calculates `fx` and `fy` from FOV. Principal point defaults to image center.

**Note:** FOV-based calibration is less accurate but should be sufficient.

### Option C: OpenCV calibration

For an even better accuracy, perform proper camera calibration:

1. Print a checkerboard pattern (e.g., 9x6 inner corners)
2. Capture 15-20 images from different angles and distances
3. Run the calibration script:

```python
import cv2
import numpy as np
import glob

CHECKERBOARD = (9, 6)
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)

objpoints, imgpoints = [], []

for fname in glob.glob('calibration_images/*.jpg'):
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)
    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)

ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

print(f"fx = {mtx[0, 0]:.2f}, fy = {mtx[1, 1]:.2f}")
print(f"cx = {mtx[0, 2]:.2f}, cy = {mtx[1, 2]:.2f}")
```

4. Set the extracted values (refer to the option A)

### Verify intrinsics

To check the computed intrinsics at runtime:

```bash
export LOG_INTRINSICS=true
```

You'll need to check analyzer logs for something like: `intrinsics fx=... fy=... cx=... cy=...`

