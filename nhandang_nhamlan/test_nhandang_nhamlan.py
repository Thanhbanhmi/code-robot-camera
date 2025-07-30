import cv2
from ultralytics import YOLO
import numpy as np

# Load model YOLO đã huấn luyện
model = YOLO("best.pt")  # Đổi đường dẫn nếu cần

PLATE_CLASS_ID = 0
WELD_CLASS_ID = 1

# Kiểm tra mối hàn có nằm trong tấm thép không
def is_inside(box_plate, box_weld):
    x1, y1, x2, y2 = box_plate
    wx1, wy1, wx2, wy2 = box_weld
    return wx1 >= x1 and wy1 >= y1 and wx2 <= x2 and wy2 <= y2

def process_image(img_path, save_result=False):
    img = cv2.imread(img_path)
    img_display = img.copy()

    result = model(img)[0]

    plate_boxes = []
    weld_boxes = []

    # Lưu các box và class ban đầu
    for box, cls_id in zip(result.boxes.xyxy, result.boxes.cls):
        x1, y1, x2, y2 = map(int, box.tolist())
        cls_id = int(cls_id.item())
        if cls_id == PLATE_CLASS_ID:
            plate_boxes.append((x1, y1, x2, y2))
            cv2.rectangle(img_display, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(img_display, "Plate", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        elif cls_id == WELD_CLASS_ID:
            weld_boxes.append((x1, y1, x2, y2))
            cv2.rectangle(img_display, (x1, y1), (x2, y2), (255, 0, 255), 2)
            cv2.putText(img_display, "Weld", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)

    # Lọc plate hợp lệ: có weld nằm trong
    valid_plate_boxes = [plate for plate in plate_boxes
                         if any(is_inside(plate, weld) for weld in weld_boxes)]

    # Tạo ảnh sau xử lý
    img_filtered = img.copy()
    for x1, y1, x2, y2 in valid_plate_boxes:
        cv2.rectangle(img_filtered, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(img_filtered, "Plate (with weld)", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # Resize cả hai ảnh về 640x480
    img_display = cv2.resize(img_display, (640, 480))
    img_filtered = cv2.resize(img_filtered, (640, 480))

    # Nối ảnh trái phải
    combined = cv2.hconcat([img_display, img_filtered])

    # Hiển thị
    cv2.imshow("Detection (Left: All, Right: Filtered)", combined)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    if save_result:
        cv2.imwrite("comparison_result.png", combined)

# Gọi hàm
process_image("nhandang_nhamlan/captured_image.jpg")
