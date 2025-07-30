import tkinter as tk
from tkinter import ttk
import threading
from arduino_control import ArduinoControl
from Quydao import CameraHandler
import numpy as np

class IntegratedControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Arduino Control Panel")
        self.root.geometry("1920x1080+0+0") # kích thước

        self.P0_list = []
        self.current_p0_index = 0  # Biến đếm cho việc gửi các điểm P0

        self.seg_array = []  # Khởi tạo biến lưu SEG Points
        self.interpolated_array = []  # Biến toàn cục lưu mảng 2 chiều chứa Interpolated Points

        # Instances
        # self.arduino_control = ArduinoControl()
        self.camera_handler = CameraHandler()

        # Current Position Variables
        self.current_x = tk.StringVar(value="X: N/A")
        self.current_y = tk.StringVar(value="Y: N/A")
        self.current_z = tk.StringVar(value="Z: N/A")
        self.current_s = tk.StringVar(value="S: N/A")
        self.led_state = False  # False: LED Off, True: LED On

        # GUI Components
        self.create_widgets()

        # Start Arduino Listening Thread
        self.start_listening()

    # Giao điện chính

    def create_widgets(self):
        """
        Tạo các thành phần giao diện cho ứng dụng.
        """
        # Tiêu đề chính
        title = tk.Label(self.root, text="Integrated Control Panel", font=("Arial", 16, "bold"))
        title.pack(pady=10)

        # Phần điều khiển Arduino
        self.create_arduino_controls()

        # Phần thông tin (Equation và Points)
        self.create_information_section()

        # Phần log hiển thị
        self.create_logs_section()

    def create_arduino_controls(self):
        """
        Tạo phần điều khiển Arduino với bố cục dạng cột, điều chỉnh độ rộng cho hài hòa.
        """
        frame_arduino = tk.LabelFrame(self.root, text="Arduino Control", padx=10, pady=10)
        frame_arduino.pack(pady=5, fill=tk.X)

        # Bố cục chính: tạo hai cột chính
        main_frame = tk.Frame(frame_arduino)
        main_frame.pack(fill=tk.X)

        # Cột 1: Nhập tọa độ
        coord_frame = tk.LabelFrame(main_frame, text="Coordinates", padx=10, pady=10, width=150)
        coord_frame.grid(row=0, column=0, padx=10, pady=5, sticky=tk.N)

        coords = [("X:", "entry_x"), ("Y:", "entry_y"), ("Z:", "entry_z"), ("S:", "entry_s")]
        for idx, (label_text, attr_name) in enumerate(coords):
            tk.Label(coord_frame, text=label_text).grid(row=idx, column=0, sticky=tk.W, padx=5, pady=2)
            setattr(self, attr_name, tk.Entry(coord_frame, width=10))
            getattr(self, attr_name).grid(row=idx, column=1, padx=5, pady=2)

        # Thêm không gian "padding" để tăng chiều ngang
        tk.Label(coord_frame, text="", width=10).grid(row=len(coords), column=0, columnspan=2)

        # Cột 2: Nút điều khiển
        control_frame = tk.LabelFrame(main_frame, text="Controls", padx=10, pady=10)
        control_frame.grid(row=0, column=1, padx=10, pady=5, sticky=tk.N)

        buttons = [
            ("Send Command", self.send_command),
            ("Home", lambda: self.send_simple_command("H")),
            ("Center", lambda: self.send_simple_command("C")),
            ("Toggle LED", self.toggle_led),
        ]
        for idx, (btn_text, command) in enumerate(buttons):
            tk.Button(control_frame, text=btn_text, command=command, width=15).pack(pady=5)

        # Cột 3: Chế độ
        mode_frame = tk.LabelFrame(main_frame, text="Mode", padx=10, pady=10)
        mode_frame.grid(row=0, column=2, padx=10, pady=5, sticky=tk.N)

        self.mode_var = tk.StringVar(value="K0")
        tk.Radiobutton(mode_frame, text="Absolute (K0)", variable=self.mode_var, value="K0").pack(anchor=tk.W, padx=5)
        tk.Radiobutton(mode_frame, text="Relative (K1)", variable=self.mode_var, value="K1").pack(anchor=tk.W, padx=5)

        # Cột 4: Vị trí hiện tại
        position_frame = tk.LabelFrame(main_frame, text="Current Position", padx=10, pady=10)
        position_frame.grid(row=0, column=3, padx=10, pady=5, sticky=tk.N)

        positions = [("X:", "current_x"), ("Y:", "current_y"), ("Z:", "current_z"), ("S:", "current_s")]
        for idx, (label_text, attr_name) in enumerate(positions):
            tk.Label(position_frame, text=label_text, font=("Arial", 10, "bold")).grid(row=idx, column=0, sticky=tk.W, padx=5)
            tk.Label(position_frame, textvariable=getattr(self, attr_name)).grid(row=idx, column=1, sticky=tk.W, padx=5)

        # Cột 5: Di chuyển đến tâm miếng thép
        move_center_frame = tk.LabelFrame(main_frame, text="Move to the center of the weld", padx=10, pady=10)
        move_center_frame.grid(row=0, column=4, padx=10, pady=5, sticky=tk.N)

        buttons = [
            ("Move", self.send_P0_center_metal)
        ]
        for idx, (btn_text, command) in enumerate(buttons):
            tk.Button(move_center_frame, text=btn_text, command=command, width=15).pack(pady=5)

        # Cột 5 Hàng 2: Di chuyển dọc tâm miếng thép
        move_seg_frame = tk.LabelFrame(main_frame, text="Move along the border", padx=10, pady=5)
        move_seg_frame.grid(row=0, column=4, padx=10, pady=80, sticky=tk.N)

        buttons = [
            ("Move", self.send_seg_points)
        ]
        for idx, (btn_text, command) in enumerate(buttons):
            tk.Button(move_seg_frame, text=btn_text, command=command, width=15).pack(pady=10)

        # Cột 6 Hàng 1: Di chuyển dọc tâm miếng thép
        move_interpolated_frame = tk.LabelFrame(main_frame, text="Move along the center", padx=10, pady=10)
        move_interpolated_frame.grid(row=0, column=5, padx=10, pady=5, sticky=tk.N)

        buttons = [
            ("Move", self.send_interpolated_points)
        ]
        for idx, (btn_text, command) in enumerate(buttons):
            tk.Button(move_interpolated_frame, text=btn_text, command=command, width=15).pack(pady=10)

    def create_information_section(self):
        """
        Tạo phần hiển thị thông tin Equation và Points với thanh cuộn.
        """
        info_frame = tk.LabelFrame(self.root, text="Information", padx=10, pady=5)
        info_frame.pack(pady=5, fill="x")

        # Phương trình hồi quy
        self.equation_label = tk.Label(info_frame, text="Equation: N/A", font=("Arial", 10))
        self.equation_label.pack(anchor="w")

        # Vùng hiển thị tọa độ với thanh cuộn
        text_frame = tk.Frame(info_frame)
        text_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.points_text = tk.Text(text_frame, height=6, wrap="word", yscrollcommand=scrollbar.set)
        self.points_text.pack(side=tk.LEFT, fill="both", expand=True)

        scrollbar.config(command=self.points_text.yview)

        # Kiểm tra widget
        assert self.points_text, "Failed to create points_text widget."


    def create_logs_section(self):
        """
        Tạo phần hiển thị logs với thanh cuộn.
        """
        frame_logs = tk.LabelFrame(self.root, text="Logs", padx=10, pady=5)
        frame_logs.pack(pady=10, fill=tk.BOTH, expand=True)

        text_frame = tk.Frame(frame_logs)
        text_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(text_frame, height=8, state=tk.DISABLED, wrap="word", yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill="both", expand=True)

        scrollbar.config(command=self.log_text.yview)

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
        z = 10
        s = 40
        mode = 1

        command = f"M{mode}X{x}Y{y}Z{z}S{s}"
        self.add_to_log(command, "Command Center Metal Sent")
        response = self.arduino_control.send_command(command)
        self.add_to_log(response)

    def send_seg_points(self):
        self.P0_list = self.camera_handler.P0_seg_list
        self.P0_list = np.array(self.P0_list)
        self.current_p0_index = 0  # Đặt biến đếm

        # Gửi giá trị P0 đầu tiên
        self.send_next_p0_point()

    def send_interpolated_points(self):
        self.P0_list = self.camera_handler.P0_interpolated_list
        self.P0_list = np.array(self.P0_list)
        self.current_p0_index = 0  # Đặt biến đếm

        # Gửi giá trị P0 đầu tiên
        self.send_next_p0_point()

    def send_next_p0_point(self):
        if self.current_p0_index < len(self.P0_list): 
            P0 = self.P0_list[self.current_p0_index] # Lấy tọa độ P0
            x, y = P0[0].item(), P0[1].item()
            z = 10  # Độ cao
            s = 30  # Tốc độ
            mode = 1  # Chế độ

            command = f"M{mode}X{x}Y{y}Z{z}S{s}"
            self.add_to_log(command, f"Command Point {self.current_p0_index + 1} Sent")
            response = self.arduino_control.send_command(command)
            self.add_to_log(response)

            self.current_p0_index += 1  # Gửi xong thì tăng biến đếm

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

        # Phân tích log và cập nhật giao diện trực tiếp
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
                    self.send_next_p0_point()  # Send the next P0 point
                self.add_to_log(response)

    def parse_current_position(self, response):
        data = response.replace("CURRENT_POSITION:", "").split()
        position = {item.split('=')[0]: item.split('=')[1] for item in data}
        self.current_x.set(f"X: {position.get('X', 'N/A')}")
        self.current_y.set(f"Y: {position.get('Y', 'N/A')}")
        self.current_z.set(f"Z: {position.get('Z', 'N/A')}")
        self.current_s.set(f"S: {position.get('S', 'N/A')}")
       
    def open_camera(self):
        """Mở camera stream."""
        threading.Thread(target=self.camera_handler.start_camera_stream, args=(self.add_to_log,), daemon=True).start()

    def capture_image(self):
        """
        Xử lý sự kiện nhấn nút chụp ảnh.
        """
        # Lấy chế độ nội suy từ giao diện
        interpolation_mode = self.mode_var.get()
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

    def close_camera(self):
        """Dừng camera stream."""
        self.camera_handler.stop_camera()

    # def Distance_AB_camera(self):
    #     """Khoảng cách AB"""
    #     print(f"Khoảng cách AB: {calculate_distance_and_display}")  # Debugging

if __name__ == "__main__":
    root = tk.Tk()    
    controller = CameraHandler()
    app = IntegratedControlApp(root)
    root.mainloop()
