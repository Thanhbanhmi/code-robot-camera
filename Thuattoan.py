import numpy as np
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
import cv2

def process_frame(frame, seg_point_count=20, regression_point_count=10, conf_threshold=0.7):
    try:
        # Dummy YOLO predictions (replace this with actual YOLO predictions)
        # For example: results = model.predict(frame, conf=conf_threshold)
        results = []  # Replace with YOLO detection results

        annotated_frame = frame.copy()
        seg_points = []
        regression_points = []
        regression_equation = "No valid regression"

        # Example object processing (replace this with actual logic)
        for result in results:
            # Extract mask, box, and class ID
            mask = result["mask"]
            box = result["box"]
            class_id = result["class_id"]

            if class_id == 1:  # Example for weld points
                contour, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                points = calculate_equally_spaced_points(contour, seg_point_count)
                seg_points.extend(points)

                # Fit polynomial regression (if points are sufficient)
                if len(points) >= 3:
                    regression_points, regression_equation = fit_regression(points)

        return annotated_frame, seg_points, regression_points, regression_equation

    except Exception as e:
        print(f"Error during frame processing: {e}")
        return frame, [], [], "Error in processing"

def calculate_equally_spaced_points(contour, seg_point_count):
    points = []
    if len(contour) >= seg_point_count:
        total_length = cv2.arcLength(contour, True)
        spacing = total_length / seg_point_count
        for i in range(0, len(contour), int(spacing)):
            point = contour[i][0]
            if len(point) == 2:
                points.append((int(point[0]), int(point[1])))
    else:
        for c in contour:
            if len(c[0]) == 2:
                points.append((int(c[0][0]), int(c[0][1])))
    return points

def fit_regression(points):
    X = np.array([p[0] for p in points]).reshape(-1, 1)
    Y = np.array([p[1] for p in points])

    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)
    model = LinearRegression().fit(X_poly, Y)

    regression_points = [(int(x), int(model.predict(poly.transform([[x]]))[0])) for x in X.flatten()]
    equation = f"y = {model.coef_[2]:.2f}x^2 + {model.coef_[1]:.2f}x + {model.intercept_:.2f}"

    return regression_points, equation

def calculate_equation_and_points(seg_points, mode=1, num_points=10):
    """
    Tính phương trình nội suy và trả về tọa độ dọc theo phương trình.

    Args:
        seg_points (list of tuple): Mảng tọa độ SEG.
        mode (int): Chế độ nội suy (1 = Tuyến tính, 2 = Phi tuyến).
        num_points (int): Số lượng điểm trả về (mặc định là 10).

    Returns:
        str: Phương trình nội suy.
        list of tuple: Các tọa độ dọc theo phương trình.
    """
    if len(seg_points) < 2:
        return "Insufficient points", []

    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures

    seg_points = np.array(seg_points)
    x = seg_points[:, 0]
    y = seg_points[:, 1]

    if mode == 1:  # Nội suy tuyến tính
        # Mô hình x=f(y)
        model_x = LinearRegression()
        model_x.fit(y.reshape(-1, 1), x)
        var_x = np.var(model_x.predict(y.reshape(-1, 1)) - x)

        # Mô hình y=f(x)
        model_y = LinearRegression()
        model_y.fit(x.reshape(-1, 1), y)
        var_y = np.var(model_y.predict(x.reshape(-1, 1)) - y)

        if var_x < var_y:
            # Chọn x=f(y)
            y_new = np.linspace(y.min(), y.max(), num_points)
            x_new = model_x.predict(y_new.reshape(-1, 1))
            equation = f"x = {model_x.coef_[0]:.3f}y + {model_x.intercept_:.3f}"
            points = [(int(x_val), int(y_val)) for x_val, y_val in zip(x_new, y_new)]
        else:
            # Chọn y=f(x)
            x_new = np.linspace(x.min(), x.max(), num_points)
            y_new = model_y.predict(x_new.reshape(-1, 1))
            equation = f"y = {model_y.coef_[0]:.3f}x + {model_y.intercept_:.3f}"
            points = [(int(x_val), int(y_val)) for x_val, y_val in zip(x_new, y_new)]

    elif mode == 2:  # Nội suy phi tuyến (đa thức bậc 2)
        poly = PolynomialFeatures(degree=2)

        # Mô hình x=f(y)
        y_poly = poly.fit_transform(y.reshape(-1, 1))
        model_x = LinearRegression()
        model_x.fit(y_poly, x)
        var_x = np.var(model_x.predict(y_poly) - x)

        # Mô hình y=f(x)
        x_poly = poly.fit_transform(x.reshape(-1, 1))
        model_y = LinearRegression()
        model_y.fit(x_poly, y)
        var_y = np.var(model_y.predict(x_poly) - y)

        if var_x < var_y:
            # Chọn x=f(y)
            y_new = np.linspace(y.min(), y.max(), num_points)
            y_poly_new = poly.transform(y_new.reshape(-1, 1))
            x_new = model_x.predict(y_poly_new)
            equation = f"x = {model_x.coef_[0]:.3f}y^2 + {model_x.coef_[1]:.3f}y + {model_x.intercept_:.3f}"
            points = [(int(x_val), int(y_val)) for x_val, y_val in zip(x_new, y_new)]
        else:
            # Chọn y=f(x)
            x_new = np.linspace(x.min(), x.max(), num_points)
            x_poly_new = poly.transform(x_new.reshape(-1, 1))
            y_new = model_y.predict(x_poly_new)
            equation = f"y = {model_y.coef_[0]:.3f}x^2 + {model_y.coef_[1]:.3f}x + {model_y.intercept_:.3f}"
            points = [(int(x_val), int(y_val)) for x_val, y_val in zip(x_new, y_new)]

    else:
        return "Invalid mode", []

    return equation, points

def get_camera_transformation_matrices(camera_params, numeric_current_x, numeric_current_y, log_callback):
    """
    Tạo các ma trận chuyển đổi Hc_1 và H1_0 dựa trên thông số camera.

    Args:
        camera_params (dict): Thông số camera (scale_x, scale_y, px_to_mm_X_Hc_1, px_to_mm_Y_Hc_1).
        log_callback (callable): Hàm callback để ghi log.

    Returns:
        tuple: Ma trận Hc_1 và H1_0.
    """
    scale_x = camera_params.get("scale_x", 1)
    scale_y = camera_params.get("scale_y", 1)
    px_to_mm_X_Hc_1 = camera_params.get("px_to_mm_X_Hc_1", 0)
    px_to_mm_Y_Hc_1 = camera_params.get("px_to_mm_Y_Hc_1", 0)

    # Ma trận đồng nhất Hc1
    Hc_1 = np.array([[1, 0, 0, -px_to_mm_X_Hc_1],
                     [0, -1, 0, px_to_mm_Y_Hc_1],
                     [0, 0, 1, 0],
                     [0, 0, 0, 1]])
    
    # Ma trận đồng nhất H1_0
    H1_0 = np.array([[1, 0, 0, numeric_current_x],  # Tọa độ trung tâm theo trục x
                     [0, 1, 0, -numeric_current_y],  # Tọa độ trung tâm theo trục y
                     [0, 0, 1, 0],
                     [0, 0, 0, 1]])

    # Tính ma trận Hc_0
    Hc_0 = np.dot(Hc_1, H1_0)

    return Hc_0

def calculate_center_of_metal(corner_metal_points, camera_params, numeric_current_x, numeric_current_y, log_callback):
    """
    Tính toán tọa độ tâm của tấm thép và ma trận chuyển đổi.
    
    Args:
        corner_metal_points (list): Danh sách 4 điểm góc của tấm thép.
        camera_params (dict): Thông số camera (scale_x, scale_y, px_to_mm_X_Hc_1, px_to_mm_Y_Hc_1).
        log_callback (callable): Hàm callback để ghi log.

    Returns:
        np.ndarray: Tọa độ P0_center_metal (4x1 matrix).
    """
    # Tính toán Hc_0 từ camera_params
    Hc_0 = get_camera_transformation_matrices(
        camera_params, 
        numeric_current_x,
        numeric_current_y,
        log_callback)

    # Tính trọng tâm tấm thép
    centroid_x, centroid_y = 0, 0
    if len(corner_metal_points) == 4:
        centroid_x = int(sum([p[0] for p in corner_metal_points]) / 4)
        centroid_y = int(sum([p[1] for p in corner_metal_points]) / 4)

    # Chuyển đổi tọa độ trọng tâm miếng thép từ pixel sang mm
    scale_x = camera_params.get("scale_x", 1)
    scale_y = camera_params.get("scale_y", 1)
    Xc = centroid_x * scale_x
    Yc = centroid_y * scale_y

    # Tọa độ tâm tấm thép trong hệ tọa độ mới
    Pc0 = np.array([[Xc],
                    [Yc],
                    [0],
                    [1]])
    P0_center_metal = np.dot(Hc_0, Pc0)

    # Ghi log kết quả, chỉ lấy giá trị x và y
    x = P0_center_metal[0][0]
    y = P0_center_metal[1][0]
    log_callback(f"P0_metal: ({x:.2f}, {y:.2f})")

    return P0_center_metal

def calculate_weld_edge_points(contours, camera_params, numeric_current_x, numeric_current_y, step_size, log_callback):
    """
    Tính toán tọa độ P0 của các điểm biên mối hàn.

    Args:
        contours (list): Danh sách các đường biên mối hàn (contours).
        camera_params (dict): Thông số camera (scale_x, scale_y, px_to_mm_X_Hc_1, px_to_mm_Y_Hc_1).
        step_size (int): Khoảng cách giữa các điểm trên đường biên.
        log_callback (callable): Hàm callback để ghi log.

    Returns:
        list: Danh sách tọa độ P0 của các điểm biên mối hàn.
    """
    # Tính toán Hc_0 từ camera_params
    Hc_0 = get_camera_transformation_matrices(
        camera_params, 
        numeric_current_x,
        numeric_current_y,
        log_callback)

    scale_x = camera_params.get("scale_x", 1)
    scale_y = camera_params.get("scale_y", 1)

    # Tính toán tọa độ P0 cho từng điểm trên đường biên
    P0_seg_list = []
    for contour in contours:
        for point in contour[::step_size]:
            seg_x, seg_y = point[0]
            Xc_seg = seg_x * scale_x
            Yc_seg = seg_y * scale_y
            Pc0_seg = [[Xc_seg],
                       [Yc_seg],
                       [0],
                       [1]]
            # Tính tọa độ P0 từ tọa độ Pc0
            P0_seg = np.dot(Hc_0, Pc0_seg)  # Nhân ma trận Hc0 với Pc0
            P0_seg = np.ceil(P0_seg)  # Làm tròn lên các giá trị
            P0_seg_list.append(P0_seg)

    # Ghi log kết quả
    for idx, P0_seg in enumerate(P0_seg_list):
        x, y = P0_seg[0][0], P0_seg[1][0]  # Lấy x và y từ ma trận
        log_callback(f"P0 for SEG point {idx + 1}: ({x}, {y})")
        print(f"P0 for SEG point {idx + 1}: ({x}, {y})")

    return P0_seg_list

import numpy as np

def calculate_interpolated_points(interpolated_points, camera_params, numeric_current_x, numeric_current_y, log_callback):
    """
    Tính toán tọa độ P0 của các điểm nội suy dọc mối hàn.

    Args:
        interpolated_points (list): Danh sách các điểm nội suy (x, y).
        camera_params (dict): Thông số camera (scale_x, scale_y).
        log_callback (callable): Hàm callback để ghi log.

    Returns:
        list: Danh sách tọa độ P0 của các điểm nội suy.
    """
    # Tính toán Hc_0 từ camera_params
    Hc_0 = get_camera_transformation_matrices(
        camera_params, 
        numeric_current_x,
        numeric_current_y,
        log_callback)

    scale_x = camera_params.get("scale_x", 1)
    scale_y = camera_params.get("scale_y", 1)

    P0_interpolated_list = []
    for point in interpolated_points:
        interpolated_x, interpolated_y = point
        Xc_interpolated = interpolated_x * scale_x
        Yc_interpolated = interpolated_y * scale_y
        Pc0_interpolated = [[Xc_interpolated],
                            [Yc_interpolated],
                            [0],
                            [1]]
        # Tính tọa độ P0 từ tọa độ Pc0
        P0_interpolated = np.dot(Hc_0, Pc0_interpolated)  # Nhân ma trận Hc0 với Pc0
        P0_interpolated = np.ceil(P0_interpolated)  # Làm tròn lên các giá trị
        P0_interpolated_list.append(P0_interpolated)

    # Ghi log kết quả
    for idx, P0_interpolated in enumerate(P0_interpolated_list):
        x, y = int(P0_interpolated[0][0]), int(P0_interpolated[1][0])
        log_callback(f"P0 for Interpolated point {idx + 1}: ({x}, {y})")
        print(f"P0 for Interpolated point {idx + 1}: ({x}, {y})")
    return P0_interpolated_list