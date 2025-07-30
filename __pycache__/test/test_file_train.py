from ultralytics import YOLO
import tkinter as tk
from tkinter import Button
import cv2
import numpy as np
import threading

class CameraApp:
    def __init__(self, root, model_path="250415Loiboxbest.pt"):
        self.root = root
        self.root.title("Camera Viewer with YOLO")
        self.root.geometry("1280x720")

        # Load YOLO model
        self.model = YOLO(model_path)

        # Buttons
        self.button_frame = tk.Frame(root)
        self.button_frame.pack()

        self.start_button = Button(self.button_frame, text="Start Camera", command=self.start_camera)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = Button(self.button_frame, text="Stop Camera", command=self.stop_camera)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Camera variables
        self.capture = None
        self.running = False

        # Camera calibration parameters
        self.DIM = (1280, 720)
        self.K = np.array([[577.0988173630536, 0.0, 645.2100526057641],
                           [0.0, 427.74292474712604, 380.15980737189005],
                           [0.0, 0.0, 1.0]])
        self.D = np.array([[0.02832547708143901], 
                           [-0.01510612949140927], 
                           [0.007157549577718251], 
                           [-0.005106826913288143]])
        self.map1, self.map2 = None, None

    def start_camera(self):
        self.stop_camera()
        # Initialize CSI camera with GStreamer pipeline
        gst_pipeline = (
            f"nvarguscamerasrc sensor-id=0 ! "
            f"video/x-raw(memory:NVMM), width=(int){3264}, height=(int){2464}, framerate=(fraction)21 ! "
            f"nvvidconv flip-method=0 ! "
            f"video/x-raw, width=(int){1280}, height=(int){720}, format=(string)BGRx ! "
            f"videoconvert ! "
            f"video/x-raw, format=(string)BGR ! appsink"
        )
        self.capture = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

        if self.capture.isOpened():
            self.running = True
            # Initialize undistortion maps
            self.map1, self.map2 = cv2.fisheye.initUndistortRectifyMap(
                self.K, self.D, np.eye(3), self.K, self.DIM, cv2.CV_16SC2
            )
            # Start a new thread for updating frames
            threading.Thread(target=self.update_frame, daemon=True).start()
        else:
            print("Failed to open CSI camera.")

    def update_frame(self):
        while self.running and self.capture.isOpened():
            ret, frame = self.capture.read()
            if ret:
                # Apply undistortion
                frame = cv2.remap(frame, self.map1, self.map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

                # Run YOLO prediction
                results = self.model.predict(frame, conf=0.5, verbose=False)

                # Annotate frame with YOLO results
                for result in results:
                    boxes = result.boxes.xyxy.cpu().numpy()  # Bounding boxes
                    classes = result.boxes.cls.cpu().numpy()  # Class IDs
                    scores = result.boxes.conf.cpu().numpy()  # Confidence scores

                    for box, cls, score in zip(boxes, classes, scores):
                        x1, y1, x2, y2 = map(int, box)
                        label = f"{self.get_class_name(cls)}: {score:.2f}"
                        color = self.get_class_color(cls)

                        # Draw bounding box and label
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Display frame
                cv2.imshow("YOLO CSI Camera Stream", frame)

                # Exit on 'q' key
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.stop_camera()
                    break
            else:
                print("Failed to read frame.")
        cv2.destroyAllWindows()

    def stop_camera(self):
        self.running = False
        if self.capture and self.capture.isOpened():
            self.capture.release()
        cv2.destroyAllWindows()

    def get_class_name(self, class_id):
        # Map class IDs to names
        class_names = {0: "Error", 1: "Metal", 2: "Weld"}
        return class_names.get(class_id, "Unknown")

    def get_class_color(self, class_id):
        # Map class IDs to colors
        class_colors = {0: (0, 0, 255), 1: (255, 0, 0), 2: (0, 255, 0)}
        return class_colors.get(class_id, (255, 255, 255))

    def on_closing(self):
        self.stop_camera()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root, model_path="250415Loiboxbest.pt")
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()