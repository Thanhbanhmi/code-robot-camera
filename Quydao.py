# File: Quydao.py

import threading
from pypylon import pylon
from ultralytics import YOLO
from Thuattoan import calculate_equation_and_points
from Thuattoan import calculate_center_of_metal
from Thuattoan import calculate_weld_edge_points
from Thuattoan import calculate_interpolated_points
from Thuattoan import get_camera_transformation_matrices
import datetime
import numpy as np
import os
import cv2


def reset_camera():
    os.system("sudo systemctl restart nvargus-daemon")

class CameraHandler:

    def __init__(self, model_path="best.pt"):
        """
        Quản lý camera Basler và xử lý YOLO.
        Args:
            model_path (str): Đường dẫn đến file model YOLO.
        """
        reset_camera()
        self.camera = None
        self.converter = None
        self.model = YOLO(model_path)
        self.current_frame = None  # Khung hình chia sẻ
        self.running = False  # Trạng thái camera stream
        self.lock = threading.Lock()  # Đảm bảo đồng bộ
        self.interpolation_mode = 1  # Mặc định là mode 1 (tuyến tính)
        self.num_points = 10  # Giá trị mặc định
        self.step_size = 20  # Giá trị mặc định
        self.P0 = None
        self.map1 = None
        self.map2 = None
        self.width_video = 3264  # Chiều rộng khung hình
        self.height_video = 2464     # Chiều cao khung hình

        #Thông số camera
        self.camera_parameters = {
            1: {  # Basler camera
                "scale_x": 385 / 3840,
                "scale_y": 275 / 2748,
                "px_to_mm_X_Hc_1": 1920 * (385 / 3840),
                "px_to_mm_Y_Hc_1": 1374 * (275 / 2748),
            },
            2: {  # Webcam
                "scale_x": 300 / 4000,  
                "scale_y": 200 / 3000,  
                "px_to_mm_X_Hc_1": 1920 * (300 / 4000),
                "px_to_mm_Y_Hc_1": 1080 * (200 / 3000),
            },
            3: {  # CSI camera
                "scale_x": 480 / 3264,
                "scale_y": 362 / 2464,
                "px_to_mm_X_Hc_1": 1632 * (480 / 3264),
                "px_to_mm_Y_Hc_1": 1232 * (362 / 2464),
            },
        }

    def update_camera_parameters_based_on_z(self, z_value):
            """ 
            Cập nhật thông số camera dựa trên giá trị Z.
            Args:
                z_value (int): Giá trị Z từ phản hồi của Arduino.
            """
            if z_value == 0:
                self.camera_parameters[3] = {
                    "scale_x": 480 / 3264,
                    "scale_y": 362 / 2464,
                    "px_to_mm_X_Hc_1": 1632 * (480 / 3264),
                    "px_to_mm_Y_Hc_1": 1232 * (362 / 2464),
                }
            elif z_value == 80:
                self.camera_parameters[3] = {
                    "scale_x": 295 / 3264,
                    "scale_y": 222 / 2464,
                    "px_to_mm_X_Hc_1": 1632 * (295 / 3264),
                    "px_to_mm_Y_Hc_1": 1232 * (222 / 2464),
                }
            print(f"Camera parameters updated for Z = {z_value}")
    
    #Cài đặt truyền biến
            
    def set_annotated_frame_callback(self, callback):
        self.annotated_frame_callback = callback

    def set_interpolation_mode(self, mode):
        """

        Đặt mode nội suy (interpolation mode).
        Args:
            mode (int): Giá trị mode (1 - tuyến tính, 2 - phi tuyến).
        """
        self.interpolation_mode = mode
        print(f"Interpolation mode set to: {self.interpolation_mode}")

    def set_num_points(self, num_points):
        """
        Thiết lập số lượng điểm nội suy.
        """
        self.num_points = num_points
        print(f"Number of interpolation points set to: {self.num_points}")
    
    def set_step_size(self, step_size):
        """
        Thiết lập giá trị step_size từ giao diện.
        """
        self.step_size = step_size
        print(f"Step size set to: {self.step_size}")  # Debugging

    def set_current_position(self, x, y):
        self.current_position_x = x
        self.current_position_y = y
    

    def initialize_camera(self, mode, scale=1.0, camera_index=0, log_callback=None):
            """
            Đơn giản hóa khởi tạo camera Basler hoặc webcam.

            Args:
                mode (int): Chế độ hoạt động của camera:
                    - 1: Camera Basler.
                    - 2: Webcam (OpenCV).
                    - 3: CSI Camera (GStreamer).
                width (int): Chiều rộng khung hình mong muốn.
                height (int): Chiều cao khung hình mong muốn.
                scale (float): Tỷ lệ thu nhỏ hoặc phóng to cửa sổ hiển thị (1.0 là kích thước gốc).
                camera_index (int): Chỉ số của webcam (áp dụng cho webcam).
            """
            # Kiểm tra nếu mode không được truyền vào
            if log_callback is None:
                log_callback = lambda x: print(x)  # Mặc định in ra console

            if mode is None:
                log_callback("Mode must be specified when initializing the camera.")
                raise ValueError("Mode must be specified when initializing the camera.")

            try:
                self.mode = mode  # Lưu trạng thái mode

                if mode == 1:  # Khởi tạo Camera Basler
                    print("Initializing Basler camera...")
                    log_callback("Initializing Basler camera...")

                    # Kết nối với camera Basler
                    try:
                        self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
                        print("Basler camera connected successfully.")
                        log_callback("Basler camera connected successfully.")
                    except Exception as e:
                        print(f"Error connecting to Basler camera: {e}")
                        log_callback(f"Error connecting to Basler camera: {e}")
                        self.stop_camera()
                        return

                    # Bắt đầu lấy khung hình với cấu hình mặc định
                    try:
                        self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
                        print("Camera started grabbing frames.")
                        log_callback("Camera started grabbing frames.")
                    except Exception as e:
                        print(f"Error starting frame grabbing: {e}")
                        log_callback(f"Error starting frame grabbing: {e}")
                        self.stop_camera()
                        return

                    # Khởi tạo bộ chuyển đổi định dạng
                    try:
                        self.converter = pylon.ImageFormatConverter()
                        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
                        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
                        print("Image format converter initialized successfully.")
                        log_callback("Image format converter initialized successfully.")
                    except Exception as e:
                        print(f"Error initializing image converter: {e}")
                        log_callback(f"Error initializing image converter: {e}")
                        self.stop_camera()
                        return

                elif mode == 2:  # Khởi tạo Webcam
                    print("Initializing webcam...")
                    log_callback("Initializing webcam...")
                    # Mở webcam với camera_index
                    self.camera = cv2.VideoCapture(camera_index)

                    # Kiểm tra xem webcam có hoạt động không
                    if not self.camera.isOpened():
                        print(f"Failed to open webcam with index {camera_index}.")
                        log_callback(f"Failed to open webcam with index {camera_index}.")
                        self.stop_camera()
                        return

                    # Thiết lập kích thước khung hình
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width_video)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height_video_video)
                    print(f"Set webcam resolution to {self.width_video}x{self.height_video_video}.")

                elif mode == 3:  # Khởi tạo CSI Camera
                    print("Initializing CSI Camera (IMX219)...")
                    log_callback("Initializing CSI Camera (IMX219)...")
                    # GStreamer pipeline cho CSI Camera
                    # Đảm bảo rằng kích thước khung hình tương thích với camera
                    gst_pipeline = (
                        f"nvarguscamerasrc sensor-id=0 ! "
                        f"video/x-raw(memory:NVMM), width=(int){3264}, height=(int){2464}, framerate=(fraction)21 ! "
                        f"nvvidconv flip-method=0 ! "
                        f"video/x-raw, width=(int){self.width_video}, height=(int){self.height_video}, format=(string)BGRx ! "
                        f"videoconvert ! "
                        f"video/x-raw, format=(string)BGR ! appsink"
                    )

                    # Mở CSI Camera với GStreamer pipeline
                    self.camera = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

                    # Kiểm tra xem CSI Camera có hoạt động không
                    if not self.camera.isOpened():
                        print("Failed to open CSI Camera.")
                        log_callback("Failed to open CSI Camera.")
                        self.stop_camera()
                        return

                    print(f"CSI Camera initialized with resolution {self.width_video}x{self.height_video}.")
                    log_callback(f"CSI Camera initialized with resolution {self.width_video}x{self.height_video}.")
                    # Hệ số chống méo của camera
                    self.DIM = (3264, 2464)
                    self.K = np.array([[1440.537083032325, 0.0, 1650.7126495134578],
                                    [0.0, 1427.8144289645445, 1292.2500140866257],
                                    [0.0, 0.0, 1.0]])
                    self.D = np.array([[0.03610631228367159], 
                                    [-0.020977866401714916], 
                                    [0.025216689917902522], 
                                    [-0.015219021079518105]])
                    # Tạo map1, map2 một lần
                    if self.map1 is None or self.map2 is None:
                        self.map1, self.map2 = cv2.fisheye.initUndistortRectifyMap(
                            self.K, self.D, np.eye(3), self.K, self.DIM, cv2.CV_16SC2
                        )
                else:
                    raise ValueError("Invalid mode. Use 1 for Basler camera or 2 for webcam.")

                # Thiết lập tỷ lệ hiển thị
                self.scale = max(0.1, min(scale, 1.0))  # Đảm bảo scale trong khoảng (0.1 đến 1.0)
                print(f"Scale factor set to {self.scale}. Display window will be resized.")

            except Exception as e:
                print(f"Error initializing camera: {e}")
                log_callback(f"Error initializing camera: {e}")
                self.stop_camera()

    def undistort_frame(self, frame):
        """
        Undistort a frame using the camera calibration parameters.
        """
        # Chỉ thực hiện remap nếu map1, map2 đã tạo
        if self.map1 is None or self.map2 is None:
            return frame
        undistorted_frame = cv2.remap(
            frame, 
            self.map1, 
            self.map2, 
            interpolation=cv2.INTER_LINEAR, 
            borderMode=cv2.BORDER_CONSTANT
        )
        return undistorted_frame    
    
    def start_camera_stream(self, mode, log_callback=None, frame_callback=None):
        """
        Mở camera stream và điều chỉnh chế độ hoạt động (stream hoặc chụp và xử lý ảnh).
        Args:
            log_callback (callable, optional): Hàm callback để ghi log.
        """

        if log_callback is None:
            log_callback = lambda x: print(x)

        try:
            if not self.camera or not self.converter:
                self.initialize_camera(mode)

            self.running = True  # Đảm bảo vòng lặp được duy trì
            self.Mode = 0  # Bắt đầu ở chế độ stream
            log_callback("Starting camera stream...")

            while self.running:
                try:
                    if self.mode == 1:  # Basler camera
                        if not self.camera.IsGrabbing():
                            break
                        grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

                        if grab_result.GrabSucceeded():
                            # Chuyển đổi khung hình từ camera
                            image = self.converter.Convert(grab_result)
                            frame = image.GetArray()

                            # Gửi khung hình đến giao diện
                            if frame_callback:
                                frame_callback(frame)
                                
                            grab_result.Release()
                        else:
                            grab_result.Release()
                            continue

                    elif self.mode in [2, 3]:  # Webcam or CSI Camera
                        if not self.camera or not self.camera.isOpened():
                            log_callback("Camera is not initialized or has been released.")
                            break

                        ret, frame = self.camera.read()
                        if not ret:
                            log_callback("Failed to grab frame from camera.")
                            break

                        #Chống méo cho CSI Camera
                        if self.mode == 3:
                            frame = self.undistort_frame(frame)

                        if frame_callback:
                            frame_callback(frame)
                    else:
                        raise ValueError("Invalid mode. Use 1 for Basler camera, 2 for webcam, or 3 for CSI Camera.")

                    if isinstance(frame, np.ndarray):
                            if self.Mode == 0:  # Chế độ stream
                                with self.lock:
                                    self.current_frame = frame.copy()
                                annotated_frame = frame.copy()
                                # Kích thước ảnh tương thích với Resolution của các Camera
                                image_height, image_width = frame.shape[:2]
                                # Tính toán trọng tâm của ảnh
                                image_centroid_x = image_width // 2
                                image_centroid_y = image_height // 2
                                # Vẽ đường thẳng ngang (y = image_centroid_y)
                                cv2.line(annotated_frame, (0, image_centroid_y), (image_width, image_centroid_y), (0, 255, 0), 2)  # Màu xanh lá, độ dày 2

                                # Vẽ đường thẳng dọc (x = image_centroid_x)
                                cv2.line(annotated_frame, (image_centroid_x, 0), (image_centroid_x, image_height), (0, 255, 0), 2)  # Màu xanh lá, độ dày 2
                                

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------#

                            elif self.Mode == 1:  # Chế độ chụp và xử lý ảnh
                                save_path = "images/captured_image.jpg"
                                with self.lock:
                                    self.current_frame = frame.copy()

                                # Lưu ảnh gốc
                                cv2.imwrite(save_path, self.current_frame)
                                log_callback(f"Image saved to {save_path}")

                                # Thực hiện xử lý trên ảnh chụp
                                annotated_frame = self.current_frame.copy()
                                results = self.model.predict(self.current_frame, conf=0.5, verbose=False)

                                if results and results[0].masks:
                                    masks = results[0].masks.data
                                    boxes = results[0].boxes.xyxy.cpu().numpy()
                                    classes = results[0].boxes.cls.cpu().numpy()

                                    # Mảng lưu bounding box của Metal và Weld
                                    metal_boxes = []
                                    weld_boxes = []

                                    # Phân loại bounding box theo class
                                    for i, mask_data in enumerate(masks):
                                        class_id = int(classes[i])
                                        box = boxes[i].astype(int)
                                        x1, y1, x2, y2 = box

                                        if class_id == 0:  # Metal
                                            metal_boxes.append((box, mask_data))
                                        elif class_id == 1:  # Weld
                                            weld_boxes.append((box, mask_data))

                                    # Kiểm tra nếu không có tấm thép hoặc mối hàn nào được phát hiện
                                    if not metal_boxes and not weld_boxes:
                                        log_callback("Không phát hiện tấm thép chứa mối hàn")
                                        return  # Thoát khỏi chế độ xử lý

                                    # Kiểm tra mối quan hệ giữa Metal và Weld
                                    valid_metal_boxes = []
                                    for metal_box, metal_mask in metal_boxes:
                                        x1_m, y1_m, x2_m, y2_m = metal_box
                                        metal_valid = False

                                        for weld_box, _ in weld_boxes:
                                            x1_w, y1_w, x2_w, y2_w = weld_box

                                            # Kiểm tra nếu Weld nằm bên trong hoặc chồng lên Metal
                                            if x1_w >= x1_m and y1_w >= y1_m and x2_w <= x2_m and y2_w <= y2_m:
                                                metal_valid = True
                                                break

                                        if metal_valid:
                                            valid_metal_boxes.append((metal_box, metal_mask))

                                    # Áp dụng logic hiện tại cho Metal hợp lệ
                                    corner_metal_points = []        # Mảng lưu 4 điểm gốc của Metal
                                    for valid_metal_box, valid_metal_mask in valid_metal_boxes:
                                        x1, y1, x2, y2 = valid_metal_box
                                        top_left = (x1, y1)
                                        top_right = (x2, y1)
                                        bottom_left = (x1, y2)
                                        bottom_right = (x2, y2)
                                        corner_metal_points.extend([top_left, top_right, bottom_left, bottom_right])
                                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 4)
                                        cv2.putText(annotated_frame, "Metal", (x1, y1 - 20), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)

                                    # Áp dụng logic hiện tại cho Weld
                                    seg_points = []                 # Mảng lưu các điểm tọa độ trên SEG
                                    contours = []                   # Mảng lưu các giá trị đường biên của mối hàn

                                    for weld_box, weld_mask in weld_boxes:
                                        x1, y1, x2, y2 = weld_box
                                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (255, 0, 0), 4)
                                        cv2.putText(annotated_frame, "Weld", (x1, y1 - 20), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 3)

                                        # Xử lý mối hàn và lấy điểm SEG
                                        mask_resized = cv2.resize((weld_mask.cpu().numpy() * 255).astype(np.uint8),
                                                                (self.current_frame.shape[1], self.current_frame.shape[0]), interpolation=cv2.INTER_NEAREST)
                                        contours, _ = cv2.findContours(mask_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                                        for contour in contours:
                                            # Nội suy đường biên để làm mượt
                                            curve = cv2.approxPolyDP(contour, epsilon=5, closed=True)
                                            cv2.drawContours(annotated_frame, [curve], -1, (0, 255, 255), 3)  # Đường SEG màu vàng
                                            for point in contour[::self.step_size]:  # Lấy các điểm cách đều 20 trên đường SEG
                                                seg_points.append(tuple(point[0]))  # Lưu điểm SEG vào mảng
                                                cv2.circle(annotated_frame, tuple(point[0]), 10, (0, 255, 255), -1)

                                # Tính phương trình và tọa độ nội suy
                                equation, interpolated_points = calculate_equation_and_points(
                                        seg_points, 
                                        mode=self.interpolation_mode,  # Truyền mode nội suy
                                        num_points=self.num_points    # Truyền số điểm nội suy
                                    )
                                # Vẽ các điểm nội suy trên ảnh
                                for point in interpolated_points:
                                    cv2.circle(annotated_frame, point, 10, (0, 255, 0), -1)
                                # Vẽ đường quỹ đạo nối các điểm
                                for j in range(len(interpolated_points) - 1):
                                    cv2.line(annotated_frame, interpolated_points[j], interpolated_points[j + 1], (0, 0, 255), 5)
                                # Kích thước ảnh tương thích với Resolution của các Camera
                                image_height, image_width = frame.shape[:2]
                                # Tính toán trọng tâm của ảnh
                                image_centroid_x = image_width // 2
                                image_centroid_y = image_height // 2
                                # Vẽ đường thẳng ngang (y = image_centroid_y)
                                cv2.line(annotated_frame, (0, image_centroid_y), (image_width, image_centroid_y), (0, 255, 0), 2)  # Màu xanh lá, độ dày 2

                                # Vẽ đường thẳng dọc (x = image_centroid_x)
                                cv2.line(annotated_frame, (image_centroid_x, 0), (image_centroid_x, image_height), (0, 255, 0), 2)  # Màu xanh lá, độ dày 2
                                
                                camera_params = self.camera_parameters.get(self.mode, {})
                                Hc_0 = get_camera_transformation_matrices(
                                    camera_params,
                                    self.current_position_x,
                                    self.current_position_y,
                                    log_callback
                                )
#-------------------------------Chuyển tọa độ tâm mối hàn từ hệ px sang tọa độ thực----------------------------------------------------------------------#
                                self.P0_center_metal = calculate_center_of_metal(
                                    corner_metal_points, 
                                    camera_params, 
                                    self.current_position_x,
                                    self.current_position_y,
                                    log_callback
                                    )
#--------------------------------------------Chuyển tọa độ biên mối hàn từ tọa độ px sang tọa độ thực--------------------------------------
                                self.P0_seg_list = calculate_weld_edge_points(
                                    contours, 
                                    camera_params, 
                                    self.current_position_x,
                                    self.current_position_y,
                                    self.step_size, 
                                    log_callback
                                )
#--------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------Chuyển tọa độ nội suy dọc mối hàn từ tọa độ px sang tọa độ thực--------------------------------------
                                self.P0_interpolated_list = calculate_interpolated_points(
                                    interpolated_points,
                                    camera_params,
                                    self.current_position_x,
                                    self.current_position_y,
                                    log_callback
                                )
#-------------------------------------------------------------------------------------------------------
                                # Thêm chữ Mode lên ảnh (góc trên cùng bên phải)
                                mode_text = f"Mode = {self.interpolation_mode}"  # Tùy chỉnh mode
                                font_scale = 1.5
                                font_thickness = 3
                                text_color = (0, 255, 0)
                                cv2.putText(annotated_frame, mode_text, (annotated_frame.shape[1] - 250, 50),
                                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, font_thickness)
                                
                                if hasattr(self, 'annotated_frame_callback') and callable(self.annotated_frame_callback):
                                    self.annotated_frame_callback(annotated_frame)


                                # Tạo tên ảnh theo cấu trúc yymmddhhMM
                                timestamp = datetime.datetime.now().strftime("%y_%m_%d_%H_%M")
                                save_path = f"images/processed_image_{timestamp}.jpg"

                                # Lưu ảnh đã xử lý
                                cv2.imwrite(save_path, annotated_frame)

                                # Gửi thông tin nơi lưu và tên ảnh qua log_callback
                                log_callback(f"Image saved at: {save_path}")
                                log_callback(f"Image name: {save_path.split('/')[-1]}")

                                # # Hiển thị ảnh đã xử lý
                                # cv2.namedWindow("Processed Image", cv2.WINDOW_NORMAL)
                                # cv2.resizeWindow("Processed Image", annotated_frame.shape[1], annotated_frame.shape[0])
                                # cv2.imshow("Processed Image", annotated_frame)

                                # Ghi log các điểm và phương trình nội suy
                                #print("Log Call back:")
                                #print(f"SEG Points: {seg_points}")  # Debug
                                #print(f"Equation: {equation}")
                                #print(f"Interpolated Points: {interpolated_points}")
                                #print("End Call back")
                                log_callback(f"SEG Points: {seg_points}")
                                log_callback(f"Equation: {equation}")
                                log_callback(f"Interpolated Points: {interpolated_points}")
                                #log_callback(f"SEG Points: {seg_points}")

                                # Reset về chế độ stream
                                self.Mode = 0
                    if frame_callback:
                       frame_callback(annotated_frame)
                        
                except Exception as e:
                    log_callback(f"Error during frame processing: {e}")

                finally:
                    if self.mode == 1 and 'grab_result' in locals():
                        grab_result.Release()

            if self.mode == 1:  # Basler camera
                self.camera.StopGrabbing()
            cv2.destroyAllWindows()
            log_callback("Camera stream stopped.")

        except Exception as e:
            log_callback(f"Error during camera stream: {e}")

    def set_mode(self, mode):
        if mode in [0, 1]:
            self.Mode = mode
            print(f"Camera mode set to {mode}")
        else:
            print("Invalid mode. Use 0 (stream) or 1 (capture).")

    def stop_camera(self):
        self.running = False
        if self.camera:
            if self.mode == 1 and hasattr(self.camera, "StopGrabbing"):
                try:
                    if self.camera.IsGrabbing():
                        self.camera.StopGrabbing()
                except Exception as e:
                    print(f"Error stopping camera grabbing: {e}")
            elif self.mode in [2, 3] and hasattr(self.camera, "release"):
                try:
                    self.camera.release()
                except Exception as e:
                    print(f"Error releasing camera: {e}")
            self.camera = None
            print("Camera stopped and closed.")

    