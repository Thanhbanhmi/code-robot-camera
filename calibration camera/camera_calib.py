import numpy as np
import cv2

# Hệ số K và D từ bước calibration
DIM = (1280, 720)
K = np.array([[577.0988173630536, 0.0, 645.2100526057641],
              [0.0, 427.74292474712604, 380.15980737189005],
              [0.0, 0.0, 1.0]])
D = np.array([[0.02832547708143901], 
              [-0.01510612949140927], 
              [0.007157549577718251], 
              [-0.005106826913288143]])

def gstreamer_pipeline(sensor_id=0,
                       capture_width=3264,
                       capture_height=2464,
                       display_width=1280,
                       display_height=720,
                       framerate=21,
                       flip_method=0):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! "
        f"videoconvert ! "
        f"video/x-raw, format=(string)BGR ! appsink"
    )

def show_camera():
    window_title = "CSI Camera"
    video_capture = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)
    
    if video_capture.isOpened():
        try:
            # Tạo map1, map2 một lần duy nhất
            map1, map2 = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), K, DIM, cv2.CV_16SC2)
            cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)

            while True:
                ret_val, frame = video_capture.read()
                if not ret_val:
                    break
                
                # Chuyển đổi ảnh đã sửa méo
                undistorted_frame = cv2.remap(frame, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                 # Vẽ hai đường tâm
                h, w = undistorted_frame.shape[:2]
                cv2.line(undistorted_frame, (w // 2, 0), (w // 2, h), (0, 255, 0), 2)
                cv2.line(undistorted_frame, (0, h // 2), (w, h // 2), (0, 255, 0), 2)

                cv2.imshow(window_title, undistorted_frame)
              
                keyCode = cv2.waitKey(1) & 0xFF
                if keyCode == 27 or keyCode == ord('q'):
                    break
        finally:
            video_capture.release()
            cv2.destroyAllWindows()
    else:
        print("Error: Unable to open camera")

if __name__ == "__main__":
    show_camera()
