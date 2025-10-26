import cv2

def test_camera(index=0):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"❌ Camera {index} cannot be opened")
        return
    ret, frame = cap.read()
    cap.release()
    if ret:
        print(f"✅ Camera {index} works. Frame shape: {frame.shape}")
    else:
        print(f"❌ Failed to read from camera {index}")

if __name__ == "__main__":
    test_camera(0)  # try 0, if fails try 1
