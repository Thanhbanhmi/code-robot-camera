import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import os
import numpy as np
from PIL import Image, ImageTk

# Hàm gstreamer_pipeline để cấu hình camera CSI
def gstreamer_pipeline(
    sensor_id=0,
    capture_width=3264,
    capture_height=2464,
    display_width=3264,
    display_height=2464,
    framerate=21,
    flip_method=0,
):
    return (
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            sensor_id,
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

# Hệ số mặc định cho calibration
DIM = (3264, 2464)
K = None
D = None

class CameraCalibrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Camera Calibration App")
        self.root.geometry("800x600")

        # Camera và trạng thái
        self.video_capture = None
        self.captured_images = []
        self.image_folder = "captured_images"
        os.makedirs(self.image_folder, exist_ok=True)

        # Giao diện
        self.create_widgets()

    def create_widgets(self):
        # Khung hiển thị camera
        self.camera_frame = ttk.Label(self.root)
        self.camera_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        self.init_black_frame(self.camera_frame, 640, 480)

        # Nút điều khiển
        ttk.Button(self.root, text="Start Camera", command=self.start_camera).grid(row=1, column=0, padx=10, pady=10)
        ttk.Button(self.root, text="Capture Image", command=self.capture_image).grid(row=1, column=1, padx=10, pady=10)
        ttk.Button(self.root, text="Calibrate", command=self.calibrate_camera).grid(row=2, column=0, padx=10, pady=10)
        ttk.Button(self.root, text="Stop Camera", command=self.stop_camera).grid(row=2, column=1, padx=10, pady=10)

        # Khung hiển thị danh sách ảnh đã chụp
        self.image_list_frame = ttk.LabelFrame(self.root, text="Captured Images")
        self.image_list_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.image_listbox = tk.Listbox(self.image_list_frame, height=10, width=50)
        self.image_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.image_list_frame, orient="vertical", command=self.image_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.image_listbox.config(yscrollcommand=scrollbar.set)

    def init_black_frame(self, frame, width, height):
        black_image = np.zeros((height, width, 3), dtype=np.uint8)
        img = Image.fromarray(black_image)
        imgtk = ImageTk.PhotoImage(image=img)
        frame.imgtk = imgtk
        frame.config(image=imgtk)

    def start_camera(self):
        if self.video_capture is None:
            self.video_capture = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)
            if not self.video_capture.isOpened():
                messagebox.showerror("Error", "Unable to open camera.")
                self.video_capture = None
                return
            self.update_camera_frame()

    def update_camera_frame(self):
        if self.video_capture and self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (640, 480))
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_frame.imgtk = imgtk
                self.camera_frame.config(image=imgtk)

            self.root.after(10, self.update_camera_frame)

    def capture_image(self):
        if self.video_capture and self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
            if ret:
                image_name = f"image_{len(self.captured_images) + 1}.jpg"
                image_path = os.path.join(self.image_folder, image_name)
                cv2.imwrite(image_path, frame)
                self.captured_images.append(image_path)
                self.image_listbox.insert(tk.END, image_name)
                messagebox.showinfo("Capture Image", f"Image saved as {image_name}")

    def calibrate_camera(self):
        if len(self.captured_images) < 20:
            messagebox.showwarning("Calibration", "Please capture at least 20 images for calibration.")
            return

        # Tìm các góc của bàn cờ
        chessboard_size = (9, 6)  # Kích thước bàn cờ (số ô vuông bên trong)
        objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)

        objpoints = []  # Điểm 3D trong không gian thực
        imgpoints = []  # Điểm 2D trong không gian ảnh

        for image_path in self.captured_images:
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ret, corners = cv2.findChessboardCorners(gray, chessboard_size, None)

            if ret:
                objpoints.append(objp)
                imgpoints.append(corners)

        # Calibration
        ret, K, D, rvecs, tvecs = cv2.fisheye.calibrate(
            objpoints,
            imgpoints,
            gray.shape[::-1],
            None,
            None,
            flags=cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC + cv2.fisheye.CALIB_CHECK_COND + cv2.fisheye.CALIB_FIX_SKEW,
        )

        if ret:
            messagebox.showinfo("Calibration", "Calibration successful!")
            print("K:", K)
            print("D:", D)
        else:
            messagebox.showerror("Calibration", "Calibration failed.")

    def stop_camera(self):
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
            self.init_black_frame(self.camera_frame, 640, 480)

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraCalibrationApp(root)
    root.mainloop()