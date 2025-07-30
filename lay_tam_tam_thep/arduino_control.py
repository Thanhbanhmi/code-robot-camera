import serial
import threading

class ArduinoControl:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600):
        self.arduino = serial.Serial(port, baudrate, timeout=1)
        self.lock = threading.Lock()  # Thêm khóa để bảo vệ cổng serial

    def send_command(self, command):
        """
        Gửi lệnh xuống Arduino qua Serial.
        """
        with self.lock:  # Đảm bảo việc truy cập cổng serial được đồng bộ
            try:
                self.arduino.write((command + "\n").encode())
                return f"Sent: {command}"
            except Exception as e:
                return f"Error: {e}"

    def listen_to_arduino(self):
        """
        Lắng nghe phản hồi từ Arduino.
        """
        with self.lock:  # Đồng bộ hóa truy cập cổng serial
            try:
                if self.arduino.in_waiting > 0:
                    return self.arduino.readline().decode().strip()
            except Exception as e:
                return f"Error reading from Arduino: {e}"
            return ""
    
    def update_current_position(self, response):
        """
        Xử lý phản hồi từ Arduino để cập nhật tọa độ hiện tại.
        """
        current_position = {"X": "N/A", "Y": "N/A", "Z": "N/A", "S": "N/A"}
        try:
            if response.startswith("CURRENT_POSITION:"):
                _, values = response.split(":")
                coords = values.split(",")
                for coord in coords:
                    if "X=" in coord:
                        current_position["X"] = coord.strip()
                    elif "Y=" in coord:
                        current_position["Y"] = coord.strip()
                    elif "Z=" in coord:
                        current_position["Z"] = coord.strip()
                    elif "S=" in coord:
                        current_position["S"] = coord.strip()
        except Exception as e:
            return f"Error updating position: {e}"
        return current_position
