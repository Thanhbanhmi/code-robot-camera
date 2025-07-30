import tkinter as tk  # Thư viện tkinter để tạo giao diện đồ họa
from tkinter import ttk  # Thư viện ttk để sử dụng các widget cải tiến
from PIL import Image, ImageTk  # Thư viện PIL để xử lý hình ảnh
import cv2  # Thư viện OpenCV để xử lý video và camera
import numpy as np  # Thư viện numpy để xử lý mảng
import threading
import subprocess
import os
from arduino_control import ArduinoControl
from Quydao import CameraHandler
from datetime import datetime

class IntegratedControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Arduino Control Interface")  # Đặt tiêu đề cho cửa sổ
        self.root.geometry("1920x1080")  # Đặt kích thước cho cửa sổ

        self.cap = None  # Khởi tạo biến để lưu trữ đối tượng camera

        # Instances
        self.arduino_control = ArduinoControl()
        self.camera_handler = CameraHandler()

        # Cấu hình lưới để chia 3 cột cách đều nhau
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Current Position Variables
        self.current_x = tk.StringVar(value="X: N/A")
        self.current_y = tk.StringVar(value="Y: N/A")
        self.current_z = tk.StringVar(value="Z: N/A")
        self.current_s = tk.StringVar(value="S: N/A")
        self.led_state = False  # False: LED Off, True: LED On

        # Tạo các cột
        self.create_column1()
        self.create_column2()
        self.create_column3()

    def create_column1(self):
        # Cột 1: Tạo phần điều khiển Arduino
        self.column1 = ttk.Frame(self.root, width=480)
        self.column1.grid(row=0, column=0, sticky="ns", padx=5, pady=5)
        self.column1.grid_columnconfigure(0, weight=1)  # Đảm bảo các widget con bên trong cột 1 bị giới hạn bởi chiều ngang của cột 1
        self.create_arduino_controls()

    def create_arduino_controls(self):
        """
        Tạo phần điều khiển Arduino với bố cục dạng cột, điều chỉnh độ rộng cho hài hòa.
        """
        frame_arduino = tk.LabelFrame(self.column1, text="Arduino Control", padx=5, pady=5)
        frame_arduino.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Bố cục chính: tạo hai cột chính
        main_frame = tk.Frame(frame_arduino)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Hàng 1 cột 1: Vị trí hiện tại
        position_frame = tk.LabelFrame(main_frame, text="Current Position", padx=5, pady=5)
        position_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        positions = [("X:", "current_x"), ("Y:", "current_y"), ("Z:", "current_z"), ("S:", "current_s")]
        for idx, (label_text, attr_name) in enumerate(positions):
            tk.Label(position_frame, text=label_text, font=("Arial", 10, "bold")).grid(row=idx, column=0, sticky=tk.W, padx=5)
            tk.Label(position_frame, textvariable=getattr(self, attr_name)).grid(row=idx, column=1, sticky=tk.W, padx=5)
        
        # Hàng 1 cột 2: Chế độ
        mode_frame = tk.LabelFrame(main_frame, text="Mode", padx=5, pady=5)
        mode_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.mode_var = tk.StringVar(value="K0")
        tk.Radiobutton(mode_frame, text="Absolute (K0)", variable=self.mode_var, value="K0").grid(row=0, column=0, sticky=tk.W, padx=5)
        tk.Radiobutton(mode_frame, text="Relative (K1)", variable=self.mode_var, value="K1").grid(row=1, column=0, sticky=tk.W, padx=5)

        # Hàng 2 cột 1: Nhập tọa độ
        coord_frame = tk.LabelFrame(main_frame, text="Coordinates", padx=5, pady=5, width=100)
        coord_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        coords = [("X:", "entry_x"), ("Y:", "entry_y"), ("Z:", "entry_z"), ("S:", "entry_s")]
        for idx, (label_text, attr_name) in enumerate(coords):
            tk.Label(coord_frame, text=label_text).grid(row=idx, column=0, sticky=tk.W, padx=5, pady=2)
            setattr(self, attr_name, tk.Entry(coord_frame, width=10))
            getattr(self, attr_name).grid(row=idx, column=1, padx=5, pady=2)

        # Thêm không gian "padding" để tăng chiều ngang
        tk.Label(coord_frame, text="", width=5).grid(row=len(coords), column=0, columnspan=2)

        # Hàng 2 cột 2: Nút điều khiển
        control_frame = tk.LabelFrame(main_frame, text="Controls", padx=5, pady=5)
        control_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        buttons = [
            ("Send Command", self.send_command),
            ("Home", lambda: self.send_simple_command("H")),
            ("Center", lambda: self.send_simple_command("C")),
            ("Toggle LED", self.toggle_led),
        ]
        for idx, (btn_text, command) in enumerate(buttons):
            tk.Button(control_frame, text=btn_text, command=command, width=15).grid(row=idx, column=0, pady=5)

        # Hàng 3: Di chuyển đến tâm miếng thép
        move_center_frame = tk.LabelFrame(main_frame, text="Move to the center of the weld", padx=10, pady=10)
        move_center_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

        buttons = [
            ("Move", self.send_P0_center_metal)
        ]
        for idx, (btn_text, command) in enumerate(buttons):
            tk.Button(move_center_frame, text=btn_text, command=command, width=15).grid(row=idx, column=0, pady=5)

        # Hàng 4: Di chuyển dọc tâm miếng thép
        move_seg_frame = tk.LabelFrame(main_frame, text="Move along the border", padx=5, pady=5)
        move_seg_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")

        buttons = [
            ("Move", self.send_seg_points)
        ]
        for idx, (btn_text, command) in enumerate(buttons):
            tk.Button(move_seg_frame, text=btn_text, command=command, width=15).grid(row=idx, column=0, pady=10)

        # Hàng 5: Di chuyển dọc tâm miếng thép
        move_interpolated_frame = tk.LabelFrame(main_frame, text="Move along the center", padx=10, pady=10)
        move_interpolated_frame.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")

        buttons = [
            ("Move", self.send_interpolated_points)
        ]
        for idx, (btn_text, command) in enumerate(buttons):
            tk.Button(move_interpolated_frame, text=btn_text, command=command, width=15).grid(row=idx, column=0, pady=10)

    def create_column2(self):
        # Cột 2: Hiển thị camera
        self.column2 = ttk.Frame(self.root, width=640, height=360)
        self.column2.grid(row=0, column=1, sticky="ns", padx=5, pady=5)
        self.column2.grid_columnconfigure(0, weight=1)
        self.column2.grid_rowconfigure(3, weight=1)
        # Ngăn các widget con mở rộng vượt quá kích thước của column2
        self.column2.grid_propagate(False)
        self.create_camera_and_mode_controls()
        self.create_info_boxes()

    def create_camera_and_mode_controls(self):
        """
        Tạo phần điều khiển camera với bố cục dạng cột, điều chỉnh độ rộng cho hài hòa.
        """
        frame_controls = ttk.Label(self.column2, text="Display", font=("Helvetica", 14), anchor="center")
        frame_controls.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.camera_frame = ttk.Label(self.column2)
        self.camera_frame.grid(row=1, column=0, padx=5, pady=5, sticky="n")
        self.init_black_frame(self.camera_frame, 640, 360)

        # Hàng 2: Điều khiển Camera và Lựa chọn mode nội suy
        control_and_mode_frame = tk.Frame(self.column2)
        control_and_mode_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        
        # Cột 1: Điều khiển Camera
        frame_camera = tk.Frame(control_and_mode_frame)
        frame_camera.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        tk.Label(frame_camera, text="Camera Control", font=("Arial", 10, "bold")).grid(row=0, column=0, pady=5, sticky="w")
        button_frame = tk.Frame(frame_camera)
        button_frame.grid(row=1, column=0, pady=5, sticky="nsew")
        self.basler_button = ttk.Button(button_frame, text="Camera Basler", command=lambda: self.select_camera("basler"))
        self.basler_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.csi_button = ttk.Button(button_frame, text="Camera CSI", command=lambda: self.select_camera("csi"))
        self.csi_button.grid(row=0, column=1, padx=5, sticky="ew")

        self.webcam_button = ttk.Button(button_frame, text="Webcam", command=lambda: self.select_camera("webcam"))
        self.webcam_button.grid(row=0, column=2, padx=5, sticky="ew")

        self.close_camera_button = ttk.Button(button_frame, text="Close", command=self.close_camera)
        self.close_camera_button.grid(row=1, column=1, padx=5, sticky="nsew")

        # Cột 2: Lựa chọn mode nội suy
        frame_mode = tk.Frame(control_and_mode_frame)
        frame_mode.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

        tk.Label(frame_mode, text="Interpolation Mode", font=("Arial", 10, "bold")).grid(row=0, column=0, pady=5, sticky="w")
        self.mode_inter = tk.IntVar(value=1)  # Giá trị mặc định là mode 1
        tk.Radiobutton(frame_mode, text="Linear (Mode 1)", variable=self.mode_inter, value=1).grid(row=1, column=0, pady=2, sticky="w")
        tk.Radiobutton(frame_mode, text="Non-linear (Mode 2)", variable=self.mode_inter, value=2).grid(row=2, column=0, pady=2, sticky="w")

        # Cột 3: Nhập số điểm SEG và Step Size
        frame_seg = tk.Frame(control_and_mode_frame)
        frame_seg.grid(row=0, column=2, padx=10, pady=5, sticky="n")

        # Label và ô nhập cho số điểm SEG
        tk.Label(frame_seg, text="Number of Points", font=("Arial", 10, "bold")).pack(anchor="w", pady=5)
        self.num_points_var = tk.IntVar(value=20)  # Giá trị mặc định là 20
        tk.Entry(frame_seg, textvariable=self.num_points_var, width=10).pack(anchor="w")

        # Label và ô nhập cho Step Size
        tk.Label(frame_seg, text="Step Size", font=("Arial", 10, "bold")).pack(anchor="w", pady=5)
        self.step_size_var = tk.IntVar(value=10)  # Giá trị mặc định là 10
        tk.Entry(frame_seg, textvariable=self.step_size_var, width=10).pack(anchor="w")

    def create_info_boxes(self):
        """
        Tạo các ô thông tin ở hàng thứ ba của cột 2.
        """
        info_boxes_frame = tk.Frame(self.column2)
        info_boxes_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        # Cấu hình để các cột và hàng mở rộng theo chiều cao và chiều rộng
        info_boxes_frame.grid_columnconfigure(0, weight=1)  # Cột 1 chiếm 1 phần
        info_boxes_frame.grid_columnconfigure(1, weight=1)  # Cột 2 chiếm 1 phần
        info_boxes_frame.grid_rowconfigure(0, weight=1)  # Hàng 0 mở rộng theo chiều cao

        # Cột 1: Ô thông tin 1 (Equation & Points)
        info_box1 = tk.LabelFrame(info_boxes_frame, text="Information", padx=10, pady=5)
        info_box1.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        info_box1.grid_columnconfigure(0, weight=1)
        info_box1.grid_rowconfigure(0, weight=1)
        info_box1.grid_rowconfigure(1, weight=1)
       
        self.equation_label = tk.Label(info_box1, text="Equation: N/A", font=("Arial", 10))
        self.equation_label.grid(row=0, column=0, sticky="nw", pady=(0, 5))  # Giảm khoảng cách dưới

        # Vùng hiển thị tọa độ với thanh cuộn trong info_box1
        text_frame = tk.Frame(info_box1)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.points_text = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set, height=8)
        self.points_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.points_text.yview)

        # Cột 2: Ô thông tin 2 (Logs)
        info_box2 = tk.LabelFrame(info_boxes_frame, text="Logs", padx=10, pady=10)
        info_box2.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        info_box2.grid_columnconfigure(0, weight=1)
        info_box2.grid_rowconfigure(0, weight=1)

        text_frame_logs = tk.Frame(info_box2)
        text_frame_logs.grid(row=0, column=0, sticky="nsew")
        text_frame_logs.grid_columnconfigure(0, weight=1)
        text_frame_logs.grid_rowconfigure(0, weight=1)

        scrollbar_logs = tk.Scrollbar(text_frame_logs)
        scrollbar_logs.grid(row=0, column=1, sticky="ns")

        self.log_text = tk.Text(text_frame_logs, state=tk.DISABLED, wrap="word", yscrollcommand=scrollbar_logs.set, height=8)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar_logs.config(command=self.log_text.yview)

    def create_column3(self):
        # Cột 3: Hiển thị ảnh chụp màn hình
        self.column3 = ttk.Frame(self.root, width=480)
        self.column3.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        # Ngăn các widget con mở rộng vượt quá kích thước của column3
        self.column3.grid_propagate(False)

        self.column3.grid_columnconfigure(0, weight=1)  # Cột 1
        self.column3.grid_rowconfigure(4, weight=1)  # Đảm bảo hàng 4 mở rộng

        # Tiêu đề
        self.screenshot_label = ttk.Label(self.column3, text="Image", font=("Helvetica", 14))
        self.screenshot_label.grid(row=0, column=0, pady=10)

        # Khung hiển thị ảnh chụp màn hình
        self.screenshot_frame = ttk.Label(self.column3)
        self.screenshot_frame.grid(row=1, column=0, pady=5)

        # Nút chụp ảnh
        self.screenshot_button = ttk.Button(self.column3, text="Capture Image", command=self.capture_image)
        self.screenshot_button.grid(row=2, column=0, pady=5, sticky="nsew")

        # Nút mở và tắt hình ảnh
        button_frame = ttk.Frame(self.column3)
        button_frame.grid(row=3, column=0, pady=5, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.open_image_button = ttk.Button(button_frame, text="Open Image", command=self.open_image)
        self.open_image_button.grid(row=0, column=0, padx=0, sticky="nsew")

        self.close_image_button = ttk.Button(button_frame, text="Close Image", command=self.close_image)
        self.close_image_button.grid(row=0, column=1, padx=0, sticky="nsew")

        # Ô thông tin mới
        info_box3 = tk.LabelFrame(self.column3, text="Data", padx=5, pady=5)
        info_box3.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")
        info_box3.grid_columnconfigure(0, weight=1)
        info_box3.grid_rowconfigure(0, weight=1)

        # Vùng hiển thị thông tin với thanh cuộn
        text_frame_info = tk.Frame(info_box3)
        text_frame_info.grid(row=0, column=0, sticky="nsew")
        text_frame_info.grid_columnconfigure(0, weight=1)
        text_frame_info.grid_rowconfigure(0, weight=1)

        scrollbar_info = tk.Scrollbar(text_frame_info)
        scrollbar_info.grid(row=0, column=1, sticky="ns")

        self.data_info_text = tk.Text(text_frame_info, wrap="word", yscrollcommand=scrollbar_info.set, height=8)
        self.data_info_text.grid(row=0, column=0, sticky="nsew")
        scrollbar_info.config(command=self.data_info_text.yview)

        # Khởi tạo khung đen khi chưa có ảnh chụp màn hình
        self.init_black_frame(self.screenshot_frame, 640 // 3, 360 // 3)
        
    def init_black_frame(self, frame, width, height):
        black_image = np.zeros((height, width, 3), dtype=np.uint8)  # Tạo ảnh đen
        img = Image.fromarray(black_image)  # Chuyển đổi sang đối tượng Image
        imgtk = ImageTk.PhotoImage(image=img)  # Chuyển đổi sang đối tượng ImageTk
        frame.imgtk = imgtk  # Lưu trữ đối tượng ImageTk
        frame.config(image=imgtk)  # Hiển thị ảnh đen trên khung

    def select_camera(self, camera_type):
        if self.cap is not None:
            self.cap.release()  # Giải phóng camera hiện tại nếu có

        if camera_type == "basler":
            mode = 1  # Mode 1: Basler camera
        elif camera_type == "csi":
            mode = 3  # Mode 3: CSI camera
        elif camera_type == "webcam":
            mode = 2  # Mode 2: Webcam
        else:
            self.add_to_log("Invalid camera type selected.", "Error")
            return
        
        # Khởi tạo camera với mode tương ứng
        threading.Thread(
            target=self.camera_handler.start_camera_stream,
            args=(mode, self.add_to_log, self.update_display_frame),
            daemon=True
        ).start()

    def update_display_frame(self, frame):
        """
        Hiển thị khung hình lên khung Display.
        """
        try:
            # Chuyển đổi khung hình từ BGR sang RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_NEAREST)

            # Chỉ tạo mới đối tượng ImageTk nếu cần
            if not hasattr(self, "camera_frame_imgtk") or self.camera_frame_imgtk is None:
                img = Image.fromarray(frame)
                self.camera_frame_imgtk = ImageTk.PhotoImage(image=img)
            else:
                img = Image.fromarray(frame)
                self.camera_frame_imgtk.paste(img)

            # Cập nhật hình ảnh trên giao diện
            self.camera_frame.config(image=self.camera_frame_imgtk)
        except Exception as e:
            print(f"Error updating display frame: {e}")

    def close_camera(self):
        """
        Dừng camera và giải phóng tài nguyên.
        """
        if self.cap is not None:
            self.cap.release()  # Giải phóng camera nếu đang sử dụng
            self.cap = None
            self.add_to_log("Camera closed successfully.", "Info")

        if hasattr(self.camera_handler, "stop_camera"):
            try:
                self.camera_handler.stop_camera()  # Gọi hàm dừng camera trong CameraHandler
                self.add_to_log("Camera handler stopped successfully.", "Info")
            except Exception as e:
                self.add_to_log(f"Error stopping camera handler: {e}", "Error")

        # Hiển thị khung đen trên giao diện
        self.init_black_frame(self.camera_frame, 640, 360)

    def capture_image(self):
        """
        Xử lý sự kiện nhấn nút chụp ảnh và hiển thị hình ảnh trong column3.
        """
        # Lấy chế độ nội suy từ giao diện
        interpolation_mode = self.mode_inter.get()
        num_points = self.num_points_var.get()
        step_size = self.step_size_var.get()

        # Truyền các giá trị mode, số điểm, và step size vào CameraHandler
        self.camera_handler.set_mode(1)  # Đặt chế độ chụp ảnh
        self.camera_handler.set_interpolation_mode(interpolation_mode)
        self.camera_handler.set_num_points(num_points)
        self.camera_handler.set_step_size(step_size)

        # Chụp ảnh từ camera
        if self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                # Xử lý ảnh
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Chuyển đổi màu sắc từ BGR sang RGB
                frame = cv2.resize(frame, (640 // 3, 360 // 3))  # Thay đổi kích thước ảnh (giảm 3 lần)
                img = Image.fromarray(frame)  # Chuyển đổi sang đối tượng Image
                self.screenshot_image = ImageTk.PhotoImage(image=img)  # Lưu trữ đối tượng ImageTk
                self.screenshot_frame.imgtk = self.screenshot_image  # Lưu trữ đối tượng ImageTk
                self.screenshot_frame.config(image=self.screenshot_image)  # Hiển thị ảnh chụp trên khung screenshot

                # Lưu ảnh vào file
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                image_path = f"captured_images/image_{timestamp}.png"
                img.save(image_path)

                # Ghi thông tin vào ô Data
                self.additional_info_text.config(state=tk.NORMAL)  # Cho phép chỉnh sửa
                self.additional_info_text.insert(tk.END, f"Image captured at: {timestamp}\n")
                self.additional_info_text.insert(tk.END, f"Image saved at: {image_path}\n")
                self.additional_info_text.insert(tk.END, f"Selected interpolation mode: {interpolation_mode}\n")
                self.additional_info_text.insert(tk.END, f"Number of points (num_points): {num_points}\n")
                self.additional_info_text.insert(tk.END, f"Step size: {step_size}\n")
                self.additional_info_text.insert(tk.END, "-" * 50 + "\n")
                self.additional_info_text.config(state=tk.DISABLED)  # Ngăn chỉnh sửa
                self.additional_info_text.see(tk.END)  # Cuộn xuống cuối

            else:
                self.add_to_log("Failed to capture image. Please check the camera connection.", "Warning")
        else:
            self.add_to_log("No camera connected. Please connect a camera and try again.", "Warning")
        # In log để kiểm tra
        print(f"Selected interpolation mode: {interpolation_mode}")  # Debugging
        print(f"Number of points (num_points): {num_points}")  # Debugging
        print(f"Step size: {step_size}")  # Debugging

    def open_image(self):
        """
        Mở hình ảnh vừa chụp trong một cửa sổ mới.
        """
        image_directory = os.path.join(os.getcwd(), "images")

        if not os.path.exists(image_directory):
            self.add_to_log("Image directory does not exists.", "Warning")
            return
        
        try:
            if os.name =='nt':
                os.startfile(image_directory)
            elif os.name =='posix':
                subprocess.Poen(['xdg-open', image_directory])
            else:
                self.add_to_log("Unsupported operating system.", "Error")
        except Exception as e:
            self.add_to_log(f"Error opening image directory: {e}", "Error")
            

    def close_image(self):
        """
        Đóng cửa sổ hiển thị hình ảnh.
        """
        if hasattr(self, "image_window") and self.image_window.winfo_exists():
            self.image_window.destroy()
        else:
            self.add_to_log("No image window to close.", "Warning")

    # Chương trình điều khiển
    def send_command(self):
        x = self.entry_x.get() or ""
        y = self.entry_y.get() or ""
        z = self.entry_z.get() or ""
        s = self.entry_s.get() or ""
        mode = self.mode_var.get()

        command = f"M{mode}X{x}Y{y}Z{z}S{s}"
        self.add_to_log(command, "Command Sent")
        response = self.arduino_control.send_command(command)
        self.add_to_log(response)

    def send_P0_center_metal(self):
        P0 = self.camera_handler.P0_center_metal
        x = P0[0, 0]
        y = P0[1, 0]
        z = 0
        s = 40
        mode = 1

        command = f"M{mode}X{x}Y{y}Z{z}S{s}"
        self.add_to_log(command, "Command Center Metal Sent")
        response = self.arduino_control.send_command(command)
        self.add_to_log(response)

    def send_seg_points(self):
        self.P0_list = self.camera_handler.P0_seg_list.copy()  # Tạo bản sao danh sách
        self.P0_list = [np.array(point) for point in self.P0_list]  # Chuyển đổi sang mảng numpy nếu cần

        # Gửi giá trị P0 đầu tiên
        self.send_next_p0_point()

        # Bắt đầu lắng nghe phản hồi từ Arduino
        threading.Thread(target=self.listen_to_arduino, daemon=True).start()

    def send_interpolated_points(self):
        """
        Gửi các điểm P0 trong danh sách nội suy.
        """
        self.P0_list = self.camera_handler.P0_interpolated_list.copy()  # Tạo bản sao danh sách
        self.P0_list = [np.array(point) for point in self.P0_list]  # Chuyển đổi sang mảng numpy nếu cần

        # Gửi giá trị P0 đầu tiên
        self.send_next_p0_point()

        # Bắt đầu lắng nghe phản hồi từ Arduino
        threading.Thread(target=self.listen_to_arduino, daemon=True).start()

    def send_next_p0_point(self):
        """
        Gửi điểm P0 tiếp theo trong danh sách nếu còn.
        """
        if self.P0_list:  # Kiểm tra nếu danh sách không rỗng
            # Lấy và loại bỏ giá trị đầu tiên trong danh sách
            P0 = self.P0_list.pop(0)
            x, y = P0[0].item(), P0[1].item()
            z = 50  # Độ cao
            s = 30  # Tốc độ
            mode = 1  # Chế độ

            # Tạo lệnh và gửi
            command = f"M{mode}X{x}Y{y}Z{z}S{s}"
            self.add_to_log(command, f"Command Sent for Point ({x}, {y})")
            self.arduino_control.send_command(command)
        else:
            self.add_to_log("All points have been sent.", "Info")

    def send_simple_command(self, command):
        self.add_to_log(command, "Command Sent")
        response = self.arduino_control.send_command(command)
        self.add_to_log(response)

    def toggle_led(self):
        command = "L" if not self.led_state else "l"
        self.led_state = not self.led_state
        response = self.arduino_control.send_command(command)
        self.add_to_log(response)

    def update_information_section(self, seg_points=None, interpolated_points=None, regression_eq=None):
        """
        Cập nhật thông tin hiển thị trong phần Information của giao diện.
        """
        self.points_text.config(state="normal")  # Cho phép chỉnh sửa nội dung

        # Không xóa nội dung cũ để giữ tất cả thông tin
        if seg_points:
                    self.points_text.delete("1.0", "end")  # Xóa toàn bộ nội dung cũ
                    # Phân giải seg_points thành mảng 2 chiều và lưu vào biến toàn cục
                    self.seg_array = [tuple(map(int, point.strip("()").split(","))) for point in seg_points.strip("[]").split("), (")]
                    
                    # Hiển thị SEG Points trên giao diện
                    self.points_text.insert("end", f"\nSEG Points:\n")
                    for idx, (x, y) in enumerate(self.seg_array):
                        self.points_text.insert("end", f"Point {idx + 1}: ({x}, {y})\n")
                    
                    print(f"DEBUG: SEG Points array stored: {self.seg_array}")  # Log kiểm tra

        if interpolated_points:
            # Lưu mảng tọa độ vào biến toàn cục
            self.interpolated_array = [tuple(map(int, point.strip("()").split(","))) for point in interpolated_points.strip("[]").split("), (")]
            
            # Hiển thị Interpolated Points trên giao diện
            self.points_text.insert("end", f"\nInterpolated Points:\n")
            for idx, (x, y) in enumerate(self.interpolated_array):
                self.points_text.insert("end", f"Point {idx + 1}: ({x}, {y})\n")
            
            print(f"DEBUG: Interpolated Points array stored: {self.interpolated_array}")  # Log kiểm tra


        if regression_eq:
            self.equation_label.config(text=f"Equation: {regression_eq}")
            print(f"DEBUG: Equation displayed: {regression_eq}")  # Log kiểm tra

        self.points_text.config(state="disabled")  # Ngăn chỉnh sửa nội dung

    def add_to_log(self, message, log_type="Info"):
        """
        Thêm log vào giao diện và hiển thị trực tiếp nội dung SEG Points, Regression Points, Equation, và Interpolated Points.
        """
        # Ghi log vào khu vực log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{log_type}] {message}\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

        # Phân tích log và hiển thị trong khung data
        if "P0 for SEG point" in message:
            self.data_info_text.config(state=tk.NORMAL)
            self.data_info_text.insert(tk.END, f"{message}\n")
            self.data_info_text.config(state=tk.DISABLED)
   
        elif "P0 for Interpolated point" in message:
            self.data_info_text.config(state=tk.NORMAL)
            self.data_info_text.insert(tk.END, f"{message}\n")
            self.data_info_text.config(state=tk.DISABLED)

        elif "Image saved at:" in message:
            self.data_info_text.config(state=tk.NORMAL)
            self.data_info_text.insert(tk.END, f"{message}\n")
            self.data_info_text.config(state=tk.DISABLED)

        elif "Image name:" in message:
            self.data_info_text.config(state=tk.NORMAL)
            self.data_info_text.insert(tk.END, f"{message}\n")
            self.data_info_text.config(state=tk.DISABLED)

        if "SEG Points:" in message:
            seg_points = message.replace("SEG Points:", "").strip()
            print(f"DEBUG: Raw SEG Points String: {seg_points}")  # Kiểm tra raw string

            self.update_information_section(seg_points=seg_points)

        elif "Equation:" in message:
            regression_eq = message.replace("Equation:", "").strip()
            self.update_information_section(regression_eq=regression_eq)

        elif "Interpolated Points:" in message:
            interpolated_points = message.replace("Interpolated Points:", "").strip()
            self.update_information_section(interpolated_points=interpolated_points)

    def start_listening(self):
        threading.Thread(target=self.listen_to_arduino, daemon=True).start()

    def listen_to_arduino(self):
        while True:
            response = self.arduino_control.listen_to_arduino()
            if response:
                if response.startswith("CURRENT_POSITION:"):
                    self.parse_current_position(response)
                    while self.P0_list:  # Tiếp tục lắng nghe nếu còn điểm trong danh sách
                        response = self.arduino_control.listen_to_arduino()
                        if response:
                            self.add_to_log(response)  # Ghi log phản hồi

                            # Kiểm tra nếu phản hồi bắt đầu bằng "M"
                            if response.startswith("CURRENT_POSITION:"):
                                self.send_next_p0_point()  # Gửi điểm tiếp theo
                self.add_to_log(response)

    def parse_current_position(self, response):
        data = response.replace("CURRENT_POSITION:", "").split()
        position = {item.split('=')[0]: item.split('=')[1] for item in data}
        self.current_x.set(f"X: {position.get('X', 'N/A')}")
        self.current_y.set(f"Y: {position.get('Y', 'N/A')}")
        self.current_z.set(f"Z: {position.get('Z', 'N/A')}")
        self.current_s.set(f"S: {position.get('S', 'N/A')}")

    def on_closing(self):
        if self.cap is not None:
            self.cap.release()  # Giải phóng camera khi tắt chương trình
        self.root.destroy()  # Đóng cửa sổ

if __name__ == "__main__":
    root = tk.Tk()
    controller = CameraHandler()
    app = IntegratedControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)  # Xử lý sự kiện khi đóng cửa sổ
    root.mainloop()