# src/webrtc/calibrate.py
import cv2 as cv, numpy as np, glob, json, os

CB_SIZE   = (9, 6)     # inner corners (columns, rows)
SQUARE_M  = 0.024      # each square size in meters
IMG_DIR   = "calib"    # folder with calibration photos
OUT_PATH  = "intrinsics.json"

def main():
    objp = np.zeros((CB_SIZE[0]*CB_SIZE[1],3), np.float32)
    objp[:,:2] = np.mgrid[0:CB_SIZE[0], 0:CB_SIZE[1]].T.reshape(-1,2)
    objp *= SQUARE_M

    obj_points, img_points = [], []
    gray_shape = None

    files = sorted(glob.glob(os.path.join(IMG_DIR, "*.jpg")) + glob.glob(os.path.join(IMG_DIR, "*.png")))
    if not files:
        raise SystemExit(f"No images found in '{IMG_DIR}'. Add checkerboard photos and rerun.")

    for fn in files:
        img = cv.imread(fn); gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        ok, corners = cv.findChessboardCorners(gray, CB_SIZE, None)
        if ok:
            corners2 = cv.cornerSubPix(gray, corners, (11,11), (-1,-1),
                                       (cv.TERM_CRITERIA_EPS+cv.TERM_CRITERIA_MAX_ITER, 30, 0.001))
            obj_points.append(objp); img_points.append(corners2)
            gray_shape = gray.shape[::-1]

    if not obj_points:
        raise SystemExit("No corners detected. Check CB_SIZE or image quality.")

    ret, K, dist, _, _ = cv.calibrateCamera(obj_points, img_points, gray_shape, None, None)
    fx, fy, cx, cy = float(K[0,0]), float(K[1,1]), float(K[0,2]), float(K[1,2])

    json.dump({"fx":fx, "fy":fy, "cx":cx, "cy":cy}, open(OUT_PATH, "w"), indent=2)
    print(f"Saved intrinsics to {OUT_PATH}: fx={fx:.1f}, fy={fy:.1f}, cx={cx:.1f}, cy={cy:.1f}")

if __name__ == "__main__":
    main()
