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
        points = [contour[i][0] for i in range(0, len(contour), int(spacing))]
    else:
        points = [c[0] for c in contour]
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
