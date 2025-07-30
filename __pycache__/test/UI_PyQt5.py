import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QRadioButton, QGroupBox, QTextEdit, QScrollArea, QGridLayout, QFrame, QSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
import numpy as np
from datetime import datetime
import threading
from arduino_control import ArduinoControl
from Quydao import CameraHandler
import cv2


class IntegratedControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arduino Control Interface")  # Đặt tiêu đề cho cửa sổ
        self.setGeometry(100, 100, 1024, 600)  # Đặt kích thước và vị trí cửa sổ

        #self.arduino_control = ArduinoControl()
        self.camera_handler = CameraHandler()

        # Widget chính chứa toàn bộ giao diện
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Bố cục chính (chia thành 3 cột)
        self.main_layout = QHBoxLayout(self.central_widget)

        # Khởi tạo các biến
        self.cap = None  # Biến lưu trữ đối tượng camera
        self.led_state = False  # Trạng thái LED (bật/tắt)

        # Tạo các cột
        self.create_column1()  # Cột 1: Điều khiển Arduino
        self.create_column2()  # Cột 2: Hiển thị camera và điều khiển
        self.create_column3()  # Cột 3: Ảnh chụp màn hình và nhật ký

    def create_column1(self):
        # Cột 1: Điều khiển Arduino
        column1 = QVBoxLayout()

        # Nhóm điều khiển Arduino
        arduino_group = QGroupBox("Arduino Control")
        arduino_layout = QVBoxLayout()

        # Hiển thị vị trí hiện tại
        position_group = QGroupBox("Current Position")
        position_layout = QVBoxLayout()
        self.current_x = QLabel("X: N/A")
        self.current_y = QLabel("Y: N/A")
        self.current_z = QLabel("Z: N/A")
        self.current_s = QLabel("S: N/A")
        position_layout.addWidget(self.current_x)
        position_layout.addWidget(self.current_y)
        position_layout.addWidget(self.current_z)
        position_layout.addWidget(self.current_s)
        position_group.setLayout(position_layout)

        # Chọn chế độ (Absolute/Relative)
        mode_group = QGroupBox("Mode")
        mode_layout = QVBoxLayout()
        self.mode_absolute = QRadioButton("Absolute (K0)")  # Chế độ tuyệt đối
        self.mode_relative = QRadioButton("Relative (K1)")  # Chế độ tương đối
        self.mode_absolute.setChecked(True)  # Mặc định chọn chế độ tuyệt đối
        mode_layout.addWidget(self.mode_absolute)
        mode_layout.addWidget(self.mode_relative)
        mode_group.setLayout(mode_layout)

        # Nhập tọa độ
        coord_group = QGroupBox("Coordinates")
        coord_layout = QGridLayout()
        coord_layout.addWidget(QLabel("X:"), 0, 0)
        self.entry_x = QLineEdit()  # Ô nhập tọa độ X
        coord_layout.addWidget(self.entry_x, 0, 1)
        coord_layout.addWidget(QLabel("Y:"), 1, 0)
        self.entry_y = QLineEdit()  # Ô nhập tọa độ Y
        coord_layout.addWidget(self.entry_y, 1, 1)
        coord_layout.addWidget(QLabel("Z:"), 2, 0)
        self.entry_z = QLineEdit()  # Ô nhập tọa độ Z
        coord_layout.addWidget(self.entry_z, 2, 1)
        coord_layout.addWidget(QLabel("S:"), 3, 0)
        self.entry_s = QLineEdit()  # Ô nhập tốc độ S
        coord_layout.addWidget(self.entry_s, 3, 1)
        coord_group.setLayout(coord_layout)

        # Các nút điều khiển
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout()
        self.send_command_button = QPushButton("Send Command")  # Nút gửi lệnh
        self.home_button = QPushButton("Home")  # Nút về vị trí gốc
        self.center_button = QPushButton("Center")  # Nút di chuyển đến tâm
        self.toggle_led_button = QPushButton("Toggle LED")  # Nút bật/tắt LED
        control_layout.addWidget(self.send_command_button)
        control_layout.addWidget(self.home_button)
        control_layout.addWidget(self.center_button)
        control_layout.addWidget(self.toggle_led_button)
        control_group.setLayout(control_layout)

        # Thêm các nhóm vào bố cục Arduino
        arduino_layout.addWidget(position_group)
        arduino_layout.addWidget(mode_group)
        arduino_layout.addWidget(coord_group)
        arduino_layout.addWidget(control_group)
        arduino_group.setLayout(arduino_layout)

        # Thêm nhóm Arduino vào cột 1
        column1.addWidget(arduino_group)
        self.main_layout.addLayout(column1)

    def create_column2(self):
        # Cột 2: Hiển thị camera và điều khiển
        column2 = QVBoxLayout()

        # Hiển thị camera
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(640, 360)  # Kích thước khung hiển thị camera
        self.camera_label.setStyleSheet("background-color: black;")  # Màu nền đen
        column2.addWidget(self.camera_label, alignment=Qt.AlignCenter)

        # Các nút điều khiển camera
        camera_controls = QHBoxLayout()
        self.basler_button = QPushButton("Camera Basler")  # Nút chọn camera Basler
        self.csi_button = QPushButton("Camera CSI")  # Nút chọn camera CSI
        self.webcam_button = QPushButton("Webcam")  # Nút chọn webcam
        self.close_camera_button = QPushButton("Close")  # Nút đóng camera
        camera_controls.addWidget(self.basler_button)
        camera_controls.addWidget(self.csi_button)
        camera_controls.addWidget(self.webcam_button)
        camera_controls.addWidget(self.close_camera_button)
        column2.addLayout(camera_controls)

        # Tạo lưới để chia thành 2 cột
        grid_layout = QGridLayout()

        # Cột 1: 3 nút nhấn
        move_center_group = QGroupBox("Move to the center of the weld")
        move_center_layout = QVBoxLayout()
        self.move_center_button = QPushButton("Move")  # Nút di chuyển đến tâm
        move_center_layout.addWidget(self.move_center_button)
        move_center_group.setLayout(move_center_layout)
        grid_layout.addWidget(move_center_group, 0, 0)  # Đặt vào cột 1, hàng 1

        move_seg_group = QGroupBox("Move along the border")
        move_seg_layout = QVBoxLayout()
        self.move_seg_button = QPushButton("Move")  # Nút di chuyển dọc biên
        move_seg_layout.addWidget(self.move_seg_button)
        move_seg_group.setLayout(move_seg_layout)
        grid_layout.addWidget(move_seg_group, 1, 0)  # Đặt vào cột 1, hàng 2

        move_interpolated_group = QGroupBox("Move along the center")
        move_interpolated_layout = QVBoxLayout()
        self.move_interpolated_button = QPushButton("Move")  # Nút di chuyển dọc tâm
        move_interpolated_layout.addWidget(self.move_interpolated_button)
        move_interpolated_group.setLayout(move_interpolated_layout)
        grid_layout.addWidget(move_interpolated_group, 2, 0)  # Đặt vào cột 1, hàng 3

        # Cột 2: Chọn chế độ nội suy và cài đặt số điểm
        interpolation_group = QGroupBox("Interpolation Mode")
        interpolation_layout = QVBoxLayout()
        self.mode_linear = QRadioButton("Linear (Mode 1)")  # Nội suy tuyến tính
        self.mode_nonlinear = QRadioButton("Non-linear (Mode 2)")  # Nội suy phi tuyến
        self.mode_linear.setChecked(True)  # Mặc định chọn nội suy tuyến tính
        interpolation_layout.addWidget(self.mode_linear)
        interpolation_layout.addWidget(self.mode_nonlinear)
        interpolation_group.setLayout(interpolation_layout)
        grid_layout.addWidget(interpolation_group, 0, 1, 1, 1)  # Đặt vào cột 2, hàng 1

        points_group = QGroupBox("Settings")
        points_layout = QVBoxLayout()
        points_layout.addWidget(QLabel("Number of Points:"))  # Nhãn số điểm
        self.num_points_spinbox = QSpinBox()  # Ô nhập số điểm
        self.num_points_spinbox.setValue(20)  # Giá trị mặc định là 20
        points_layout.addWidget(self.num_points_spinbox)
        points_layout.addWidget(QLabel("Step Size:"))  # Nhãn bước nhảy
        self.step_size_spinbox = QSpinBox()  # Ô nhập bước nhảy
        self.step_size_spinbox.setValue(10)  # Giá trị mặc định là 10
        points_layout.addWidget(self.step_size_spinbox)
        points_group.setLayout(points_layout)
        grid_layout.addWidget(points_group, 1, 1, 2, 1)  # Đặt vào cột 2, hàng 2 và 3

        # Thêm lưới vào column2
        column2.addLayout(grid_layout)

        self.main_layout.addLayout(column2)

    def create_column3(self):
        # Cột 3: Ảnh chụp màn hình và nhật ký
        column3 = QVBoxLayout()

        # Hiển thị ảnh chụp màn hình
        self.screenshot_label = QLabel()
        self.screenshot_label.setFixedSize(320, 180)  # Kích thước khung hiển thị ảnh
        self.screenshot_label.setStyleSheet("background-color: black;")  # Màu nền đen
        column3.addWidget(self.screenshot_label, alignment=Qt.AlignCenter)

        # Các nút điều khiển ảnh chụp
        screenshot_buttons = QHBoxLayout()
        self.capture_button = QPushButton("Capture Image")  # Nút chụp ảnh
        self.open_image_button = QPushButton("Open Image")  # Nút mở ảnh
        self.close_image_button = QPushButton("Close Image")  # Nút đóng ảnh
        screenshot_buttons.addWidget(self.capture_button)
        screenshot_buttons.addWidget(self.open_image_button)
        screenshot_buttons.addWidget(self.close_image_button)
        column3.addLayout(screenshot_buttons)

        # Nhật ký (Logs)
        logs_group = QGroupBox("Logs")
        logs_layout = QVBoxLayout()
        self.log_text = QTextEdit()  # Khu vực hiển thị nhật ký
        self.log_text.setReadOnly(True)  # Chỉ cho phép đọc
        logs_layout.addWidget(self.log_text)
        logs_group.setLayout(logs_layout)
        column3.addWidget(logs_group)

        self.main_layout.addLayout(column3)

    def update_camera_frame(self, frame):
        """Cập nhật khung hình camera."""
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Chuyển đổi màu từ BGR sang RGB
        height, width, channel = frame.shape
        bytes_per_line = channel * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        self.camera_label.setPixmap(pixmap)  # Hiển thị khung hình trên giao diện

    def capture_image(self):
        """Chụp ảnh từ camera."""
        if self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"captured_images/image_{timestamp}.png"
                cv2.imwrite(filename, frame)  # Lưu ảnh vào file
                self.log_text.append(f"Image saved: {filename}")  # Ghi log
            else:
                self.log_text.append("Failed to capture image.")  # Ghi log lỗi
        else:
            self.log_text.append("No camera connected.")  # Ghi log nếu không có camera

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
        z = 80
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
            z = 80  # Độ cao
            s = 20  # Tốc độ
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

    # def add_to_log(self, message, log_type="Info"):
    #     """
    #     Thêm log vào giao diện và hiển thị trực tiếp nội dung SEG Points, Regression Points, Equation, và Interpolated Points.
    #     """
    #     # Ghi log vào khu vực log
    #     self.log_text.config(state=tk.NORMAL)
    #     self.log_text.insert(tk.END, f"[{log_type}] {message}\n")
    #     self.log_text.config(state=tk.DISABLED)
    #     self.log_text.see(tk.END)

    #     # Phân tích log và hiển thị trong khung data
    #     if "P0 for SEG point" in message:
    #         self.data_info_text.config(state=tk.NORMAL)
    #         self.data_info_text.insert(tk.END, f"{message}\n")
    #         self.data_info_text.config(state=tk.DISABLED)
   
    #     elif "P0 for Interpolated point" in message:
    #         self.data_info_text.config(state=tk.NORMAL)
    #         self.data_info_text.insert(tk.END, f"{message}\n")
    #         self.data_info_text.config(state=tk.DISABLED)

    #     elif "Image saved at:" in message:
    #         self.data_info_text.config(state=tk.NORMAL)
    #         self.data_info_text.insert(tk.END, f"{message}\n")
    #         self.data_info_text.config(state=tk.DISABLED)

    #     elif "Image name:" in message:
    #         self.data_info_text.config(state=tk.NORMAL)
    #         self.data_info_text.insert(tk.END, f"{message}\n")
    #         self.data_info_text.config(state=tk.DISABLED)

    #     if "SEG Points:" in message:
    #         seg_points = message.replace("SEG Points:", "").strip()
    #         print(f"DEBUG: Raw SEG Points String: {seg_points}")  # Kiểm tra raw string

    #         self.update_information_section(seg_points=seg_points)

    #     elif "Equation:" in message:
    #         regression_eq = message.replace("Equation:", "").strip()
    #         self.update_information_section(regression_eq=regression_eq)

    #     elif "Interpolated Points:" in message:
    #         interpolated_points = message.replace("Interpolated Points:", "").strip()
    #         self.update_information_section(interpolated_points=interpolated_points)

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
    app = QApplication(sys.argv)
    window = IntegratedControlApp()
    window.show()
    sys.exit(app.exec_())