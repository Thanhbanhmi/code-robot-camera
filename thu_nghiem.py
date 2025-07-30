import tkinter as tk  # Thư viện tkinter để tạo giao diện đồ họa
from tkinter import ttk  # Thư viện ttk để sử dụng các widget cải tiến
from PIL import Image, ImageTk  # Thư viện PIL để xử lý hình ảnh
import cv2  # Thư viện OpenCV để xử lý video và camera
import numpy as np  # Thư viện numpy để xử lý mảng
import threading
import subprocess
import os
import time
from arduino_control import ArduinoControl
from Quydao import CameraHandler
from datetime import datetime

class IntegratedControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Thệ Thống Robot Camera Công Nghiệp")  # Đặt tiêu đề cho cửa sổ
        self.root.geometry("1024x600")  # Đặt kích thước cho cửa sổ
        self.root.resizable(False, False) # Không cho phép thay đổi kích thước cửa sổ

        # Định nghĩa bảng màu
        self.colors = {
            "background": "#2E2E2E",      # Nền tối
            "foreground": "#E0E0E0",      # Chữ sáng
            "primary": "#4A90E2",         # Màu chủ đạo (xanh dương)
            "secondary": "#5CB85C",       # Màu phụ (xanh lá cây)
            "accent": "#F0AD4E",          # Màu nhấn (cam)
            "border": "#424242",          # Viền
            "label_bg": "#3A3A3A",        # Nền cho LabelFrame
            "button_active_bg": "#3A7BD5",# Màu nền nút khi hover
            "button_fg": "#FFFFFF"        # Màu chữ nút
        }

        # Cấu hình phong cách chung cho các widget ttk
        style = ttk.Style()
        style.theme_use('clam')  # Sử dụng theme 'clam' làm cơ sở để tùy chỉnh

        style.configure('TFrame', background=self.colors["background"])
        style.configure('TLabel', background=self.colors["background"], foreground=self.colors["foreground"])
        # Loại bỏ thuộc tính 'style' từ TLabelFrame để tránh lỗi 'Layout TLabelFrame not found'
        style.configure('TLabelFrame', background=self.colors["background"], foreground=self.colors["accent"], relief="flat", borderwidth=2, lightcolor=self.colors["border"], darkcolor=self.colors["border"])
        style.configure('TButton', background=self.colors["primary"], foreground=self.colors["button_fg"], font=('Arial', 10, 'bold'), borderwidth=0, relief="raised")
        style.map('TButton',
                  background=[('active', self.colors["button_active_bg"]), ('pressed', self.colors["button_active_bg"])],
                  foreground=[('active', self.colors["button_fg"]), ('pressed', self.colors["button_fg"])])
        style.configure('TRadiobutton', background=self.colors["background"], foreground=self.colors["foreground"])
        style.configure('TEntry', fieldbackground=self.colors["label_bg"], foreground=self.colors["foreground"], borderwidth=1, relief="solid")

        self.root.config(bg=self.colors["background"]) # Đặt màu nền cho cửa sổ chính

        self.cap = None  # Khởi tạo biến để lưu trữ đối tượng camera

        # Instances
        self.arduino_control = ArduinoControl()
        self.camera_handler = CameraHandler()

        #Khởi tạo danh sách P01
        self.P0_list = []   #Danh sách lưu các điểm cần gửi

        # Cấu hình lưới để chia 3 cột cách đều nhau
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=3)
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
        self.column1 = ttk.Frame(self.root, width=180, style='TFrame')
        self.column1.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.column1.grid_columnconfigure(0, weight=1)  # Đảm bảo các widget con bên trong cột 1 bị giới hạn bởi chiều ngang của cột 1
        self.create_arduino_controls()

    def create_arduino_controls(self):
        """
        Tạo phần điều khiển Arduino với bố cục dạng cột.
        """
        # Thay đổi từ tk.LabelFrame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        frame_arduino = ttk.LabelFrame(self.column1, text="Điều Khiển Arduino")
        frame_arduino.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        frame_arduino.grid_columnconfigure(0, weight=1) # Đảm bảo main_frame mở rộng

        # Bố cục chính: tạo một cột chính
        main_frame = ttk.Frame(frame_arduino, style='TFrame')
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1) # Đảm bảo các frame con trong main_frame mở rộng theo chiều ngang

        # Hàng 1: Vị trí hiện tại
        # Thay đổi từ tk.LabelFrame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        position_frame = ttk.LabelFrame(main_frame, text="Vị trí hiện tại")
        position_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        position_frame.grid_columnconfigure(1, weight=1) # Cho cột giá trị mở rộng

        positions = [("X:", "current_x"), ("Y:", "current_y"), ("Z:", "current_z"), ("S:", "current_s")]
        for idx, (label_text, attr_name) in enumerate(positions):
            ttk.Label(position_frame, text=label_text, font=("Arial", 10, "bold"), foreground=self.colors["foreground"], background=self.colors["label_bg"]).grid(row=idx, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(position_frame, textvariable=getattr(self, attr_name), foreground=self.colors["primary"], background=self.colors["label_bg"]).grid(row=idx, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Hàng 2: Chế độ
        # Thay đổi từ tk.LabelFrame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        mode_frame = ttk.LabelFrame(main_frame, text="Chế Độ")
        mode_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        mode_frame.grid_columnconfigure(0, weight=1)

        self.mode_var = tk.StringVar(value="K0")
        ttk.Radiobutton(mode_frame, text="Tương Đối (K0)", variable=self.mode_var, value="K0", style='TRadiobutton').grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Radiobutton(mode_frame, text="Tuyệt Đối(K1)", variable=self.mode_var, value="K1", style='TRadiobutton').grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)

        # Hàng 3: Nhập tọa độ
        # Thay đổi từ tk.LabelFrame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        coord_frame = ttk.LabelFrame(main_frame, text="Tọa độ nhập")
        coord_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        coord_frame.grid_columnconfigure(1, weight=1)

        coords = [("X:", "entry_x"), ("Y:", "entry_y"), ("Z:", "entry_z"), ("S:", "entry_s")]
        for idx, (label_text, attr_name) in enumerate(coords):
            ttk.Label(coord_frame, text=label_text, foreground=self.colors["foreground"], background=self.colors["label_bg"]).grid(row=idx, column=0, sticky=tk.W, padx=5, pady=2)
            setattr(self, attr_name, ttk.Entry(coord_frame, width=10, style='TEntry'))
            getattr(self, attr_name).grid(row=idx, column=1, padx=5, pady=2, sticky="ew")

        # Hàng 4: Nút điều khiển
        # Thay đổi từ tk.LabelFrame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        control_frame = ttk.LabelFrame(main_frame, text="Nút điều khiển")
        control_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")
        control_frame.grid_columnconfigure(0, weight=1)

        buttons = [
            ("Điều Khiển Thủ Công", self.send_command),
            ("Home", lambda: self.send_simple_command("H")),
            ("Center", lambda: self.send_simple_command("C")),
            ("Đèn Laser", self.toggle_led),
        ]
        for idx, (btn_text, command) in enumerate(buttons):
            btn = ttk.Button(control_frame, text=btn_text, command=command, style='TButton')
            btn.grid(row=idx, column=0, pady=5, padx=5, sticky="ew")

    def create_column2(self):
        # Cột 2: Hiển thị camera
        self.column2 = ttk.Frame(self.root, width=426, height=240, style='TFrame')
        self.column2.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.column2.grid_columnconfigure(0, weight=1)
        self.column2.grid_rowconfigure(3, weight=1) # Cho phần info_boxes mở rộng
        # Ngăn các widget con mở rộng vượt quá kích thước của column2
        self.column2.grid_propagate(False)
        self.create_camera_and_mode_controls()
        self.create_info_boxes()

    def create_camera_and_mode_controls(self):
        """
        Tạo phần điều khiển camera với bố cục dạng cột.
        """
        # Khung hiển thị camera (sử dụng ttk.Label để có thể tùy chỉnh style)
        self.camera_frame = ttk.Label(self.column2, background="black", relief="solid", borderwidth=1, style='TLabel')
        self.camera_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew") # Đặt row thành 0
        self.init_black_frame(self.camera_frame, 426, 240)


        # Hàng 2: Điều khiển Camera và Lựa chọn mode nội suy
        # Sửa lỗi chính tả tk.Framse thành tk.Frame
        control_and_mode_frame = ttk.Frame(self.column2, style='TFrame')
        control_and_mode_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew") # Đặt row thành 1
        control_and_mode_frame.grid_columnconfigure(0, weight=1)
        control_and_mode_frame.grid_columnconfigure(1, weight=1) # Chia 2 cột con

        # Cột 1: Điều khiển Camera
        # Thay đổi từ tk.Frame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        frame_camera_controls = ttk.LabelFrame(control_and_mode_frame, text="Điều Khiển Camera")
        frame_camera_controls.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        frame_camera_controls.grid_columnconfigure(0, weight=1)

        button_frame_camera = ttk.Frame(frame_camera_controls, style='TFrame')
        button_frame_camera.grid(row=0, column=0, pady=2, sticky="nsew")
        button_frame_camera.grid_columnconfigure(0, weight=1)
        button_frame_camera.grid_columnconfigure(1, weight=1)

        self.csi_button = ttk.Button(button_frame_camera, text="Bật ", command=lambda: self.select_camera("csi"), style='TButton')
        self.csi_button.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        self.close_camera_button = ttk.Button(button_frame_camera, text="Tắt", command=self.close_camera, style='TButton')
        self.close_camera_button.grid(row=0, column=1, padx=2, pady=2, sticky="ew")

        # Cột 2: Lựa chọn mode nội suy
        # Thay đổi từ tk.Frame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        frame_mode_inter = ttk.LabelFrame(control_and_mode_frame, text="Chế độ nội suy")
        frame_mode_inter.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        frame_mode_inter.grid_columnconfigure(0, weight=1)

        self.mode_inter = tk.IntVar(value=1)  # Giá trị mặc định là mode 1
        ttk.Radiobutton(frame_mode_inter, text="Tuyến tính (Mode 1)", variable=self.mode_inter, value=1, style='TRadiobutton').grid(row=0, column=0, pady=2, sticky="w", padx=5)
        ttk.Radiobutton(frame_mode_inter, text="Phi tuyến(Mode 2)", variable=self.mode_inter, value=2, style='TRadiobutton').grid(row=1, column=0, pady=2, sticky="w", padx=5)

        # Hàng 3: Nhập số điểm SEG và Step Size
        # Thay đổi từ tk.Frame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        frame_seg_step = ttk.LabelFrame(self.column2, text="Cấu hình nội suy") # Đặt frame này ở row 2 của column2
        frame_seg_step.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        frame_seg_step.grid_columnconfigure(1, weight=1)
        frame_seg_step.grid_columnconfigure(3, weight=1)

        # Label và ô nhập cho số điểm SEG
        ttk.Label(frame_seg_step, text="Số điểm:", font=("Arial", 10, "bold"), foreground=self.colors["foreground"], background=self.colors["label_bg"]).grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.num_points_var = tk.IntVar(value=20)  # Giá trị mặc định là 20
        ttk.Entry(frame_seg_step, textvariable=self.num_points_var, width=10, style='TEntry').grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        # Label và ô nhập cho Step Size
        ttk.Label(frame_seg_step, text="Steps size:", font=("Arial", 10, "bold"), foreground=self.colors["foreground"], background=self.colors["label_bg"]).grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.step_size_var = tk.IntVar(value=10)  # Giá trị mặc định là 10
        ttk.Entry(frame_seg_step, textvariable=self.step_size_var, width=10, style='TEntry').grid(row=0, column=3, padx=5, pady=2, sticky="ew")

    def create_info_boxes(self):
        """
        Tạo các ô thông tin ở hàng thứ ba của cột 2.
        """
        info_boxes_frame = ttk.Frame(self.column2, style='TFrame')
        info_boxes_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")
        
        # Cấu hình để các cột và hàng mở rộng theo chiều cao và chiều rộng
        info_boxes_frame.grid_columnconfigure(0, weight=1)  # Cột 1 chiếm 1 phần
        info_boxes_frame.grid_columnconfigure(1, weight=1)  # Cột 2 chiếm 1 phần
        info_boxes_frame.grid_rowconfigure(0, weight=1)  # Hàng 0 mở rộng theo chiều cao

        # Cột 1: Ô thông tin 1 (Equation & Points)
        # Thay đổi từ tk.LabelFrame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        info_box1 = ttk.LabelFrame(info_boxes_frame, text="Thông tin ")
        info_box1.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        info_box1.grid_columnconfigure(0, weight=1)
        info_box1.grid_rowconfigure(1, weight=1) # Cho text area mở rộng

        self.equation_label = ttk.Label(info_box1, text="Phương trình: N/A", font=("Arial", 9), foreground=self.colors["foreground"], background=self.colors["label_bg"])
        self.equation_label.grid(row=0, column=0, sticky="nw", pady=(2, 2), padx=5)

        # Vùng hiển thị tọa độ với thanh cuộn trong info_box1
        text_frame = ttk.Frame(info_box1, style='TFrame')
        text_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=2)
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.points_text = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set, height=6, bg=self.colors["label_bg"], fg=self.colors["foreground"], insertbackground=self.colors["foreground"], selectbackground=self.colors["primary"], selectforeground=self.colors["button_fg"], borderwidth=1, relief="solid")
        self.points_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.points_text.yview)

        # Cột 2: Ô thông tin 2 (Logs)
        # Thay đổi từ tk.LabelFrame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        info_box2 = ttk.LabelFrame(info_boxes_frame, text="Logs")
        info_box2.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        info_box2.grid_columnconfigure(0, weight=1)
        info_box2.grid_rowconfigure(0, weight=1)

        text_frame_logs = ttk.Frame(info_box2, style='TFrame')
        text_frame_logs.grid(row=0, column=0, sticky="nsew", padx=5, pady=2)
        text_frame_logs.grid_columnconfigure(0, weight=1)
        text_frame_logs.grid_rowconfigure(0, weight=1)

        scrollbar_logs = ttk.Scrollbar(text_frame_logs)
        scrollbar_logs.grid(row=0, column=1, sticky="ns")

        self.log_text = tk.Text(text_frame_logs, state=tk.DISABLED, wrap="word", yscrollcommand=scrollbar_logs.set, height=6, bg=self.colors["label_bg"], fg=self.colors["foreground"], insertbackground=self.colors["foreground"], selectbackground=self.colors["primary"], selectforeground=self.colors["button_fg"], borderwidth=1, relief="solid")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar_logs.config(command=self.log_text.yview)

    def create_column3(self):
        # Cột 3: Hiển thị ảnh chụp màn hình và điều khiển dữ liệu
        self.column3 = ttk.Frame(self.root, width=248, style='TFrame')
        self.column3.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        # Ngăn các widget con mở rộng vượt quá kích thước của column3
        self.column3.grid_propagate(False)

        self.column3.grid_columnconfigure(0, weight=1)  # Cột 1
        self.column3.grid_rowconfigure(4, weight=1)  # Đảm bảo hàng 4 mở rộng (phần data_info_text)

        # Khung hiển thị ảnh chụp màn hình
        self.screenshot_frame = ttk.Label(self.column3, background="black", relief="solid", borderwidth=1, style='TLabel')
        self.screenshot_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nsew") # Đặt row thành 0

        # Nút chụp ảnh
        self.screenshot_button = ttk.Button(self.column3, text="Chụp & xử lí", command=self.get_data, style='TButton')
        self.screenshot_button.grid(row=1, column=0, pady=2, padx=5, sticky="ew") # Đặt row thành 1

        # Nút mở và tắt hình ảnh
        button_frame_image_actions = ttk.Frame(self.column3, style='TFrame')
        button_frame_image_actions.grid(row=2, column=0, pady=2, padx=5, sticky="ew") # Đặt row thành 2
        button_frame_image_actions.grid_columnconfigure(0, weight=1)
        button_frame_image_actions.grid_columnconfigure(1, weight=1)

        self.open_image_button = ttk.Button(button_frame_image_actions, text="Mở ảnh", command=self.open_image, style='TButton')
        self.open_image_button.grid(row=0, column=0, padx=2, sticky="nsew")

        self.close_image_button = ttk.Button(button_frame_image_actions, text="Đóng ảnh", command=self.close_image, style='TButton')
        self.close_image_button.grid(row=0, column=1, padx=2, sticky="nsew")

        # Ô thông tin mới (Data Log)
        # Thay đổi từ tk.LabelFrame sang ttk.LabelFrame và bỏ style='TLabelFrame'
        info_box3 = ttk.LabelFrame(self.column3, text="Kết quả xử lí")
        info_box3.grid(row=3, column=0, padx=5, pady=5, sticky="nsew") # Đặt row thành 3
        info_box3.grid_columnconfigure(0, weight=1)
        info_box3.grid_rowconfigure(0, weight=1)

        # Vùng hiển thị thông tin với thanh cuộn
        text_frame_info = ttk.Frame(info_box3, style='TFrame')
        text_frame_info.grid(row=0, column=0, sticky="nsew", padx=5, pady=2)
        text_frame_info.grid_columnconfigure(0, weight=1)
        text_frame_info.grid_rowconfigure(0, weight=1)

        scrollbar_info = ttk.Scrollbar(text_frame_info)
        scrollbar_info.grid(row=0, column=1, sticky="ns")

        self.data_info_text = tk.Text(text_frame_info, wrap="word", yscrollcommand=scrollbar_info.set, height=6, bg=self.colors["label_bg"], fg=self.colors["foreground"], insertbackground=self.colors["foreground"], selectbackground=self.colors["primary"], selectforeground=self.colors["button_fg"], borderwidth=1, relief="solid")
        self.data_info_text.grid(row=0, column=0, sticky="nsew")
        scrollbar_info.config(command=self.data_info_text.yview)

        # Khởi tạo khung đen khi chưa có ảnh chụp màn hình
        self.init_black_frame(self.screenshot_frame, 248, 160)

        # Các nút điều khiển di chuyển
        button_frame_data = ttk.Frame(info_box3, style='TFrame')
        button_frame_data.grid(row=1, column=0, pady=5, sticky="ew", padx=5) # Đặt row thành 1 trong info_box3
        button_frame_data.grid_columnconfigure(0, weight=1)

        buttons = [
            ("Di chuyển đến tâm kim loại", self.send_P0_center_metal),
            ("Di chuyển theo điểm phân đoạn", self.send_seg_points),
            ("Di chuyển theo điểm nội suy", self.send_interpolated_points),
        ]
        for idx, (btn_text, command) in enumerate(buttons):
            ttk.Button(button_frame_data, text=btn_text, command=command, style='TButton').grid(row=idx, column=0, pady=2, sticky="ew")

        
    def init_black_frame(self, frame, width, height):
        """
        Hiển thị khung camera với văn bản thông báo khi chưa có camera.
        """
        
        gray_image = np.ones((height, width, 3), dtype=np.uint8) * 30 # Màu nền tối
        
        # Thêm văn bản vào ảnh
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = "Camera chua bat"
        text_size = cv2.getTextSize(text, font, 0.7, 1)[0]
        
        # Tính toán vị trí để căn giữa văn bản
        text_x = (width - text_size[0]) // 2
        text_y = (height + text_size[1]) // 2
        
        # Thêm văn bản vào ảnh
        cv2.putText(gray_image, text, (text_x, text_y), font, 0.7, (150, 150, 150), 1, cv2.LINE_AA) # Màu chữ xám nhạt
        
        # Thêm viền camera
        cv2.rectangle(gray_image, (1, 1), (width-2, height-2), (100, 100, 100), 1) # Viền xám
        
        # Chuyển đổi và hiển thị
        img = Image.fromarray(gray_image)
        imgtk = ImageTk.PhotoImage(image=img)
        frame.imgtk = imgtk  # Lưu trữ đối tượng ImageTk
        frame.config(image=imgtk)  # Hiển thị ảnh đen trên khung

    def select_camera(self, camera_type):
        if self.cap is not None:
            self.cap.release()  # Giải phóng camera hiện tại nếu có

        if camera_type == "csi":
            mode = 3  # Mode 3: CSI camera
      
        
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
            frame = cv2.resize(frame, (426, 240), interpolation=cv2.INTER_NEAREST)

            # Chỉ tạo mới đối tượng ImageTk nếu cần
            if not hasattr(self, "camera_frame_imgtk") or self.camera_frame_imgtk is None:
                img = Image.fromarray(frame)
                self.camera_frame_imgtk = ImageTk.PhotoImage(image=img)
                self.camera_frame.configure(image=self.camera_frame_imgtk)
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
            self.add_to_log("Camera đã đóng thành công.", "Thông tin")

        if hasattr(self.camera_handler, "stop_camera"):
            try:
                self.camera_handler.stop_camera()  # Gọi hàm dừng camera trong CameraHandler
                self.add_to_log("Camera handler đã dừng thành công.", "Thông tin")
            except Exception as e:
                self.add_to_log(f"Lỗi khi dừng camera handler: {e}", "Lỗi")

        # Hiển thị khung đen trên giao diện
        self.init_black_frame(self.camera_frame, 426, 240)

    def get_data(self):
        """
        Xử lý sự kiện nhấn nút chụp ảnh và hiển thị hình ảnh trong column3.
        """
        self.data_info_text.config(state=tk.NORMAL)
        self.data_info_text.delete("1.0", tk.END)
        self.data_info_text.config(state=tk.DISABLED)
        # Lấy chế độ nội suy từ giao diện
        interpolation_mode = self.mode_inter.get()
        num_points = self.num_points_var.get()
        step_size = self.step_size_var.get()

        # Truyền các giá trị mode, số điểm, và step size vào CameraHandler
        self.camera_handler.set_mode(1)  # Đặt chế độ chụp ảnh
        self.camera_handler.set_interpolation_mode(interpolation_mode)
        self.camera_handler.set_num_points(num_points)
        self.camera_handler.set_step_size(step_size)
          
        # In log để kiểm tra
        print(f"Selected interpolation mode: {interpolation_mode}")  # Debugging
        print(f"Number of points (num_points): {num_points}")  # Debugging
        print(f"Step size: {step_size}")  # Debugging
        
        self.camera_handler.set_annotated_frame_callback(self.display_annotated_frame)

    def display_annotated_frame(self, annotated_frame):
        """
        Giám sát thư mục hình ảnh và hiển thị hình ảnh mới nhất khi có sẵn.
        """
        if annotated_frame is not None:
            try:
                if len(annotated_frame.shape) == 3 and annotated_frame.shape[2] == 3:
                    frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                else:
                    frame_rgb = annotated_frame

                resized_frame = cv2.resize(frame_rgb, (248, 160))

                img = Image.fromarray(resized_frame)
                img_tk = ImageTk.PhotoImage(image=img)

                self.root.after(0, lambda: self.update_screenshot_frame(img_tk))
            
            except Exception as e:
                self.root.after(0, lambda: self.add_to_log(f"Lỗi hiển thị khung hình chú thích: {e}", "Lỗi"))

    def update_screenshot_frame(self, img_tk):
        self.screenshot_image = img_tk
        self.screenshot_frame.imgtk = self.screenshot_image
        self.screenshot_frame.config(image=self.screenshot_image)

    def open_image(self):
        """
        Mở hình ảnh vừa chụp trong một cửa sổ mới.
        """
        image_directory = os.path.join(os.getcwd(), "images")

        if not os.path.exists(image_directory):
            self.add_to_log("Thư mục ảnh không tồn tại.", "Cảnh báo")
            return
        
        try:
            if os.name =='nt':
                os.startfile(image_directory)
            elif os.name =='posix':
                subprocess.Popen(['xdg-open', image_directory])
            else:
                self.add_to_log("Hệ điều hành không được hỗ trợ.", "Lỗi")
        except Exception as e:
            self.add_to_log(f"Lỗi khi mở thư mục ảnh: {e}", "Lỗi")
            

    def close_image(self):
        """
        Đóng cửa sổ hiển thị hình ảnh.
        """
        if hasattr(self, "image_window") and self.image_window.winfo_exists():
            self.image_window.destroy()
        else:
            self.add_to_log("Không có cửa sổ ảnh để đóng.", "Cảnh báo")

    # Chương trình điều khiển
    def send_command(self):
        x = self.entry_x.get() or ""
        y = self.entry_y.get() or ""
        z = self.entry_z.get() or ""
        s = self.entry_s.get() or ""
        mode = self.mode_var.get()

        command = f"M{mode}X{x}Y{y}Z{z}S{s}"
        self.add_to_log(command, "Lệnh đã gửi")
        response = self.arduino_control.send_command(command)
        self.add_to_log(response)

    def send_P0_center_metal(self):
        P0 = self.camera_handler.P0_center_metal
        if P0 is None:
            self.add_to_log("Không tìm thấy điểm tâm kim loại để di chuyển.", "Lỗi")
            return

        x = P0[0, 0]
        y = P0[1, 0]
        z = 80
        s = 40
        mode = 1

        command = f"M{mode}X{x}Y{y}S{s}"
        self.add_to_log(command, "Lệnh di chuyển đến tâm kim loại đã gửi")
        response = self.arduino_control.send_command(command)
        self.add_to_log(response)
        command_z = f"M{mode}Z{z}"
        self.add_to_log(command_z, "Lệnh di chuyển đến tâm kim loại đã gửi (Z)")
        response_z = self.arduino_control.send_command(command_z)
        self.add_to_log(response_z)

    def send_seg_points(self):
        if not self.camera_handler.P0_seg_list:
            self.add_to_log("Không có điểm phân đoạn để gửi.", "Cảnh báo")
            return

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
        if not self.camera_handler.P0_interpolated_list:
            self.add_to_log("Không có điểm nội suy để gửi.", "Cảnh báo")
            return

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
            z = 80  # Độ cao
            s = 20  # Tốc độ
            mode = 1  # Chế độ

            # Tạo lệnh và gửi
            command = f"M{mode}X{x}Y{y}Z{z}S{s}"
            self.add_to_log(command, f"Lệnh đã gửi cho điểm ({x}, {y})")
            self.arduino_control.send_command(command)
        else:
            self.add_to_log("Tất cả các điểm đã được gửi.", "Thông tin")
            self.P0_list.clear()

    def send_simple_command(self, command):
        self.add_to_log(command, "Lệnh đã gửi")
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
        
        # Xóa nội dung cũ nếu có (hoặc chỉ chèn nếu muốn giữ lịch sử)
        # self.points_text.delete("1.0", "end") 

        if seg_points:
                    self.points_text.delete("1.0", "end")  # Xóa toàn bộ nội dung cũ
                    # Phân giải seg_points thành mảng 2 chiều và lưu vào biến toàn cục
                    self.seg_array = [tuple(map(int, point.strip("()").split(","))) for point in seg_points.strip("[]").split("), (")]
                    
                    # Hiển thị SEG Points trên giao diện
                    self.points_text.insert("end", f"Điểm phân đoạn:\n", "title") # Sử dụng tag "title"
                    for idx, (x, y) in enumerate(self.seg_array):
                        self.points_text.insert("end", f"Điểm {idx + 1}: ({x}, {y})\n")
                    
                    print(f"DEBUG: SEG Points array stored: {self.seg_array}")  # Log kiểm tra

        if interpolated_points:
            # Lưu mảng tọa độ vào biến toàn cục
            self.interpolated_array = [tuple(map(int, point.strip("()").split(","))) for point in interpolated_points.strip("[]").split("), (")]
            
            # Hiển thị Interpolated Points trên giao diện
            self.points_text.insert("end", f"\nĐiểm nội suy:\n", "title") # Sử dụng tag "title"
            for idx, (x, y) in enumerate(self.interpolated_array):
                self.points_text.insert("end", f"Điểm {idx + 1}: ({x}, {y})\n")
            
            print(f"DEBUG: Interpolated Points array stored: {self.interpolated_array}")  # Log kiểm tra


        if regression_eq:
            self.equation_label.config(text=f"Phương trình: {regression_eq}")
            print(f"DEBUG: Equation displayed: {regression_eq}")  # Log kiểm tra

        self.points_text.config(state="disabled")  # Ngăn chỉnh sửa nội dung

        # Cấu hình tag cho tiêu đề trong points_text
        self.points_text.tag_configure("title", font=("Arial", 10, "bold"), foreground=self.colors["accent"])


    def add_to_log(self, message, log_type="Thông tin"):
        """
        Thêm log vào giao diện và hiển thị trực tiếp nội dung SEG Points, Regression Points, Equation, và Interpolated Points.
        """
        # Ghi log vào khu vực log
        self.log_text.config(state=tk.NORMAL)
        # Định nghĩa màu cho các loại log
        log_colors = {
            "Thông tin": self.colors["foreground"],
            "Lệnh đã gửi": self.colors["primary"],
            "Cảnh báo": self.colors["accent"],
            "Lỗi": "red",
            "Lệnh di chuyển đến tâm kim loại đã gửi": self.colors["primary"],
            "Lệnh di chuyển đến tâm kim loại đã gửi (Z)": self.colors["primary"],
            "Lệnh đã gửi cho điểm": self.colors["primary"]
        }
        color = log_colors.get(log_type, self.colors["foreground"])
        self.log_text.insert(tk.END, f"[{log_type}] {message}\n", (log_type.replace(" ", "_").lower())) # Sử dụng tag theo log_type
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

        # Cấu hình tag cho các loại log
        self.log_text.tag_configure(log_type.replace(" ", "_").lower(), foreground=color)


        # Phân tích log và hiển thị trong khung data
        self.data_info_text.config(state=tk.NORMAL) # Cho phép chỉnh sửa data_info_text
        if "P0_metal" in message:
            self.data_info_text.insert(tk.END, f"{message}\n", "data_info")
        elif "P0 for SEG point" in message:
            self.data_info_text.insert(tk.END, f"{message}\n", "data_info")
        elif "P0 for Interpolated point" in message:
            self.data_info_text.insert(tk.END, f"{message}\n", "data_info")
        elif "Image saved at:" in message:
            self.data_info_text.insert(tk.END, f"{message}\n", "data_info")
        elif "Image name:" in message:
            self.data_info_text.insert(tk.END, f"{message}\n", "data_info")
        self.data_info_text.config(state=tk.DISABLED) # Khóa data_info_text lại

        # Cấu hình tag cho data_info_text
        self.data_info_text.tag_configure("data_info", foreground=self.colors["foreground"])

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
                    self.extract_numeric_coordinates(response)
                    if self.P0_list:  # Tiếp tục lắng nghe nếu còn điểm trong danh sách
                        self.add_to_log(response)  # Ghi log phản hồi

                        self.send_next_p0_point()  # Gửi điểm tiếp theo
                else: # Đảm bảo mọi phản hồi khác từ Arduino cũng được log
                    self.add_to_log(response, "Phản hồi Arduino")


    def parse_current_position(self, response):
        data = response.replace("CURRENT_POSITION:", "").split()
        position = {item.split('=')[0]: item.split('=')[1] for item in data}

        self.current_x.set(f"X: {position.get('X', 'N/A')}")
        self.current_y.set(f"Y: {position.get('Y', 'N/A')}")
        self.current_z.set(f"Z: {position.get('Z', 'N/A')}")
        self.current_s.set(f"S: {position.get('S', 'N/A')}")

    def extract_numeric_coordinates(self, response):
        try:
            data_response = response.replace("CURRENT_POSITION:", "").replace(",", "").split()
            position_response = {item.split('=')[0]: item.split('=')[1] for item in data_response}

            def is_valid_number(value):
                try:
                    float(value)
                    return True
                except ValueError:
                    return False
            x_value = position_response.get('X', '0')
            y_value = position_response.get('Y', '0')
            z_value = position_response.get('Z', '0')
            self.numeric_current_x = float(x_value) if is_valid_number(x_value) else 0.0
            self.numeric_current_y = float(y_value) if is_valid_number(y_value) else 0.0
            self.numeric_current_z = float(z_value) if is_valid_number(z_value) else 0.0

            self.camera_handler.set_current_position(self.numeric_current_x, self.numeric_current_y)
            self.camera_handler.update_camera_parameters_based_on_z(self.numeric_current_z)
            # print(f"X: {self.numeric_current_x}, Y: {self.numeric_current_y}, Z: {self.numeric_current_z}") # Log này có thể gây nhiễu log chính
        except Exception as e:
            print(f"Error extracting numeric coordinates: {e}") # Đổi thông báo lỗi để dễ debug

    def on_closing(self):
        if self.cap is not None:
            self.cap.release()  # Giải phóng camera khi tắt chương trình
        # Đảm bảo camera handler cũng được dừng
        if hasattr(self.camera_handler, "stop_camera"):
            self.camera_handler.stop_camera()
        self.root.destroy()  # Đóng cửa sổ

if __name__ == "__main__":
    root = tk.Tk()
    app = IntegratedControlApp(root)
    app.start_listening()
    # controller = CameraHandler() # Dòng này có thể bị trùng lặp vì đã khởi tạo trong __init__
    root.protocol("WM_DELETE_WINDOW", app.on_closing)  # Xử lý sự kiện khi đóng cửa sổ
    root.mainloop()  # Bắt