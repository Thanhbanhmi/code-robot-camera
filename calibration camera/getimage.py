import cv2
import os

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=3264,
    capture_height=2464,
    display_width=1920,
    display_height=1080,
    framerate=21,
    flip_method=0,
):
    return (
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            sensor_id,
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

def main():
    # Tạo thư mục lưu ảnh nếu chưa tồn tại
    output_dir = 'calib_image_160'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Mở camera CSI
    video_capture = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)

    if not video_capture.isOpened():
        print("Không thể mở camera")
        return

    print("Nhấn 'S' để chụp ảnh, nhấn 'Q' để thoát")

    # Đếm số lượng ảnh đã lưu
    img_count = len([name for name in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, name))])
    
    window_title = "CSI Camera"
    cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)

    while True:
        # Đọc khung hình từ camera
        ret_val, frame = video_capture.read()

        if not ret_val:
            print("Không thể đọc khung hình từ camera")
            break

        # Hiển thị khung hình
        cv2.imshow(window_title, frame)

        # Kiểm tra phím nhấn
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            # Chụp ảnh và lưu vào file
            img_name = os.path.join(output_dir, f'{img_count:03d}.jpg')
            cv2.imwrite(img_name, frame)
            print(f"Ảnh đã được chụp và lưu thành '{img_name}'")
            img_count += 1
        elif key == ord('q'):
            # Thoát khỏi chương trình
            break

    # Giải phóng camera và đóng tất cả các cửa sổ
    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()