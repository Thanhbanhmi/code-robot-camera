import tkinter as tk
from tkinter import Button, Label
import cv2
from PIL import Image, ImageTk
import numpy as np
import threading

class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Camera Viewer")
        self.root.geometry("1280x720")

        # Video display
        self.video_label = Label(root)
        self.video_label.pack()

        # Buttons
        self.button_frame = tk.Frame(root)
        self.button_frame.pack()

        self.basler_button = Button(self.button_frame, text="Basler Camera", command=lambda: self.start_camera(1))
        self.basler_button.pack(side=tk.LEFT, padx=5)

        self.csi_button = Button(self.button_frame, text="CSI Camera", command=lambda: self.start_camera(3))
        self.csi_button.pack(side=tk.LEFT, padx=5)

        self.webcam_button = Button(self.button_frame, text="Webcam", command=lambda: self.start_camera(2))
        self.webcam_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = Button(self.button_frame, text="Stop Camera", command=self.stop_camera)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Camera variables
        self.capture = None
        self.running = False
        self.map1 = None
        self.map2 = None
        self.DIM = (3264, 2464)
        self.K = np.array([[1440.537083032325, 0.0, 1650.7126495134578],
                           [0.0, 1427.8144289645445, 1292.2500140866257],
                           [0.0, 0.0, 1.0]])
        self.D = np.array([[0.03610631228367159], 
                           [-0.020977866401714916], 
                           [0.025216689917902522], 
                           [-0.015219021079518105]])

    def start_camera(self, mode):
        self.stop_camera()
        if mode == 1:  # Basler camera
            print("Initializing Basler camera...")
            # Add Basler camera initialization logic here
        elif mode == 2:  # Webcam
            print("Initializing Webcam...")
            self.capture = cv2.VideoCapture(0)
        elif mode == 3:  # CSI Camera
            print("Initializing CSI Camera...")
            gst_pipeline = (
                f"nvarguscamerasrc sensor-id=0 ! "
                f"video/x-raw(memory:NVMM), width=(int){3264}, height=(int){2464}, framerate=(fraction)21 ! "
                f"nvvidconv flip-method=0 ! "
                f"video/x-raw, width=(int){3264}, height=(int){2464}, format=(string)BGRx ! "
                f"videoconvert ! "
                f"video/x-raw, format=(string)BGR ! appsink"
            )
            self.capture = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

        if self.capture and self.capture.isOpened():
            self.running = True
            self.update_frame()
        else:
            print("Failed to open camera.")

    def update_frame(self):
            if self.running and self.capture and self.capture.isOpened():
                try:
                    if self.map1 is None or self.map2 is None:
                        self.map1, self.map2 = cv2.fisheye.initUndistortRectifyMap(
                            self.K, self.D, np.eye(3), self.K, self.DIM, cv2.CV_16SC2
                        )

                    while self.running:
                        ret, frame = self.capture.read()
                        if not ret:
                            print("Failed to read frame.")
                            break
                        undistorted_frame = cv2.remap(frame, self.map1, self.map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

                        h, w = undistorted_frame.shape[:2]
                        cv2.line(undistorted_frame, (w // 2, 0), (w // 2, h), (0, 255, 0), 2)
                        cv2.line(undistorted_frame, (0, h // 2), (w, h // 2), (0, 255, 0), 2)

                        cv2.imshow("Camera Stream", undistorted_frame)

                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.stop_camera()
                            break
                finally:
                    cv2.destroyAllWindows()


    def stop_camera(self):
        self.running = False
        if self.capture and self.capture.isOpened():
            self.capture.release()
        cv2.destroyAllWindows()

    def on_closing(self):
        self.stop_camera()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
