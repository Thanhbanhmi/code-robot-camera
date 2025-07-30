import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import numpy as np
from Quydao import CameraHandler

class CameraInterfaceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Camera Interface")
        self.root.geometry("800x600")  # Kích thước cửa sổ

        self.camera_handler = CameraHandler()
        self.cap = None  # Biến lưu trữ camera

        # Tạo giao diện
        self.create_camera_display()
        self.create_camera_controls()

    def create_camera_display(self):
        """
        Tạo màn hình hiển thị camera.
        """
        self.display_frame = ttk.LabelFrame(self.root, text="Camera Display", padding=10)
        self.display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.camera_frame = ttk.Label(self.display_frame)
        self.camera_frame.pack(fill=tk.BOTH, expand=True)

        # Hiển thị khung đen khi chưa có camera
        self.init_black_frame(self.camera_frame, 640, 480)

    def create_camera_controls(self):
        """
        Tạo các nút điều khiển chế độ camera.
        """
        self.control_frame = ttk.LabelFrame(self.root, text="Camera Controls", padding=10)
        self.control_frame.pack(fill=tk.X, padx=10, pady=10)

        # Nút chọn chế độ camera
        ttk.Button(self.control_frame, text="Basler Camera", command=lambda: self.select_camera("basler")).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Webcam", command=lambda: self.select_camera("webcam")).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="CSI Camera", command=lambda: self.select_camera("csi")).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Close Camera", command=self.close_camera).pack(side=tk.LEFT, padx=5)

    def init_black_frame(self, frame, width, height):
        """
        Hiển thị khung đen khi chưa có camera.
        """
        black_image = np.zeros((height, width, 3), dtype=np.uint8)
        img = Image.fromarray(black_image)
        imgtk = ImageTk.PhotoImage(image=img)
        frame.imgtk = imgtk
        frame.config(image=imgtk)

    def select_camera(self, camera_type):
        """
        Chọn chế độ camera và bắt đầu hiển thị.
        """
        if self.cap is not None:
            self.cap.release()  # Giải phóng camera hiện tại

        if camera_type == "basler":
            mode = 1  # Basler camera
        elif camera_type == "webcam":
            mode = 2  # Webcam
        elif camera_type == "csi":
            mode = 3  # CSI camera
        else:
            print("Invalid camera type selected.")
            return

        print(f"Selected camera mode: {mode}")
        self.camera_handler.set_mode(mode)

        # Bắt đầu hiển thị camera
        self.start_camera_stream()

    def start_camera_stream(self):
        """
        Bắt đầu hiển thị camera.
        """
        self.cap = cv2.VideoCapture(0)  # Mở camera (có thể cần chỉnh index)
        if not self.cap.isOpened():
            print("Failed to open camera.")
            return

        def update_frame():
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.camera_frame.imgtk = imgtk
                    self.camera_frame.config(image=imgtk)
                self.root.after(10, update_frame)

        update_frame()

    def close_camera(self):
        """
        Đóng camera và hiển thị khung đen.
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.init_black_frame(self.camera_frame, 640, 480)

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraInterfaceApp(root)
    root.mainloop()