/*
   Phien ban 02.12.2024
   Đã điều chỉnh đúng chiều X và Y
*/
#include <Stepper.h>
#define LED 12
int GT;
const int stepsPerRevolution = 200;  // Số bước cho mỗi vòng quay
byte Step = 1, Mode = 0;

// Đối tượng Stepper cho mỗi trục
Stepper stepperY(stepsPerRevolution, 32, 34, 36, 38);
Stepper stepperX(stepsPerRevolution, 22, 24, 26, 28);
Stepper stepperZ(stepsPerRevolution, 42, 44, 46, 48);
//Độ lệch so với Zero
int X_Home = 0;
int Y_Home = 0;
int Z_Home = 0;

// Vị trí hiện tại của từng trục
int Step_currentX = 0;
int Step_currentY = 0;
int Step_currentZ = 0;
int CurrentX = 0;
int CurrentY = 0;
int CurrentZ = 0;

// Các chân công tắc hành trình
const int limitSwitchY = 2;
const int limitSwitchX = 3;
const int limitSwitchZ = 4;

void setup()
{
  Serial.begin(9600);
  stepperX.setSpeed(40);
  stepperY.setSpeed(40);
  stepperZ.setSpeed(40);

  // Thiết lập các chân công tắc hành trình
  pinMode(limitSwitchX, INPUT_PULLUP);
  pinMode(limitSwitchY, INPUT_PULLUP);
  pinMode(limitSwitchZ, INPUT_PULLUP);
  pinMode(LED, OUTPUT);
}
void loop()
{
  if (Serial.available() > 0) {
    if (Mode == 0)
    {
      GT = Serial.read();
      Truyen();
    }
    if (Mode == 1)
    {
      Serial.print("Chuyen ve Mode 1");
      String chuoiToaDo = Serial.readString(); // Đọc chuỗi từ Serial
      chuoiToaDo.trim(); // Loại bỏ khoảng trắng và ký tự thừa
      Serial.print(" Mã Nhận được là: ");
      Serial.println(chuoiToaDo);
      Nhap_XYZ(chuoiToaDo); // Gọi hàm với chuỗi nhận được
      Mode = 0;
    }
  }
}
//------------ chuong trinh
void Nhap_XYZ(String chuoiToaDo) {
  int modeType = 0; // Chế độ K mặc định
  int targetX = 0, targetY = 0, targetZ = 0, targetS = 20;

  // Tách và xác định chế độ K
  if (chuoiToaDo.startsWith("K0")) {
    modeType = 0; // Tọa độ tuyệt đối
    chuoiToaDo = chuoiToaDo.substring(2); // Bỏ "K0"
  } else if (chuoiToaDo.startsWith("K1")) {
    modeType = 1; // Tọa độ tương đối
    chuoiToaDo = chuoiToaDo.substring(2); // Bỏ "K1"
  } else {
    Serial.println("Chế độ không hợp lệ. Mặc định về K0.");
    modeType = 0;
  }

  // Hàm tìm giá trị của từng ký tự trong chuỗi (xử lý cả chữ hoa và chữ thường)
  auto parse_value = [](String str, char keyUpper, char keyLower, int &target, bool isRelative) {
    int keyIndexUpper = str.indexOf(keyUpper);
    int keyIndexLower = str.indexOf(keyLower);

    int keyIndex = (keyIndexUpper >= 0) ? keyIndexUpper : keyIndexLower;

    if (keyIndex >= 0) {
      int startIndex = keyIndex + 1;
      int endIndex = startIndex;
      while (endIndex < str.length() && (isdigit(str[endIndex]) || str[endIndex] == '-')) {
        endIndex++;
      }
      int value = str.substring(startIndex, endIndex).toInt();

      if (isRelative) {
        if (keyIndex == keyIndexUpper) { // Chữ hoa (cộng)
          target += value;
        } else { // Chữ thường (trừ)
          target -= value;
        }
      } else {
        target = value;
      }
    }
  };

  // Lấy giá trị X, Y, Z, S
  parse_value(chuoiToaDo, 'X', 'x', targetX, modeType == 1);
  parse_value(chuoiToaDo, 'Y', 'y', targetY, modeType == 1);
  parse_value(chuoiToaDo, 'Z', 'z', targetZ, modeType == 1);
  parse_value(chuoiToaDo, 'S', 's', targetS, false); // Tốc độ không cần chế độ tương đối

  // In giá trị đã xử lý để kiểm tra
  Serial.println("=== Giá trị đã xử lý ===");
  Serial.print("Chế độ K: ");
  Serial.println(modeType);
  Serial.print("X = ");
  Serial.println(targetX);
  Serial.print("Y = ");
  Serial.println(targetY);
  Serial.print("Z = ");
  Serial.println(targetZ);
  Serial.print("S = ");
  Serial.println(targetS);
  Serial.println("========================");

  // Xử lý theo chế độ K
  switch (modeType) {
    case 0: // Tọa độ tuyệt đối
      Serial.println("Chế độ K0: Tọa độ tuyệt đối.");
      
      break;

    case 1: // Tọa độ tương đối
      Serial.println("Chế độ K1: Tọa độ tương đối.");
      targetX += CurrentX;
      targetY += CurrentY;
      targetZ += CurrentZ;
      break;

    default:
      Serial.println("Chế độ không hợp lệ. Mặc định về K0.");
      return;
  }

  // Hiển thị tọa độ mục tiêu
  Serial.print("Tọa độ mục tiêu: X=");
  Serial.print(targetX);
  Serial.print(" mm, Y=");
  Serial.print(targetY);
  Serial.print(" mm, Z=");
  Serial.print(targetZ);
  Serial.print(" mm, S=");
  Serial.print(targetS);
  Serial.println();

  // Di chuyển đến tọa độ mục tiêu
  moveToPositionXYZ(targetX, targetY, targetZ, targetS);

  // Chuyển về chế độ chờ
  Serial.println("Mode = 0: Trở về trạng thái chờ.");
}

// Điều khiển tọa độ
void moveToPositionXYZ(int targetX_mm, int targetY_mm, int targetZ_mm, int Speed) {
  Serial.print("Tọa độ hiện tại: X=");Serial.print(CurrentX);Serial.print(" mm, Y=");Serial.print(CurrentY);Serial.print(" mm, Z=");
  Serial.print(CurrentZ);
  Serial.println(" mm");
  Serial.print("Mục tiêu X mm: ");
  Serial.print(targetX_mm);
  Serial.print("Mục tiêu Y mm: ");
  Serial.print(targetY_mm);
  // Đổi tọa độ từ mm sang số bước và giới hạn trước khi di chuyển
  int targetStepX = constrain((targetX_mm * 1000 / 200) + (25 * 1000 / 200), 0, 1500); // Giới hạn bước X
  int targetStepY = constrain((targetY_mm * 1000 / 200) + (20 * 1000 / 200), 0, 2000); // Giới hạn bước Y
  int targetStepZ = constrain((targetZ_mm * 1000 / 40) + (20 * 1000 / 40), 0, 2500);  // Giới hạn bước Z
  stepperX.setSpeed(constrain(Speed, 10, 60));
  stepperY.setSpeed(constrain(Speed, 10, 60));
  stepperZ.setSpeed(constrain(Speed, 10, 60));
  // Thông báo tọa độ mục tiêu sau khi giới hạn
  Serial.print("Toa do muc tieu (sau khi gioi han): X=");
  Serial.print(targetStepX * 200 / 1000 - 25); // Chuyển ngược lại sang mm
  Serial.print(" mm, Y=");
  Serial.print(targetStepY * 200 / 1000 - 20); // Chuyển ngược lại sang mm
  Serial.print(" mm, Z=");
  Serial.print(targetStepZ * 40 / 1000 - 20);  // Chuyển ngược lại sang mm
  Serial.println(" mm");

  // Di chuyển từng trục
  while (Step_currentX != targetStepX || Step_currentY != targetStepY || Step_currentZ != targetStepZ) {
    // Điều chỉnh trục X
    if (Step_currentX < targetStepX) {
      stepperX.step(-1);
      Step_currentX++;
    } else if (Step_currentX > targetStepX) {
      stepperX.step(1);
      Step_currentX--;
    }
    // Điều chỉnh trục Y
    if (Step_currentY < targetStepY) {
      stepperY.step(1);
      Step_currentY++;
    } else if (Step_currentY > targetStepY) {
      stepperY.step(-1);
      Step_currentY--;
    }

    // Điều chỉnh trục Z
    if (Step_currentZ < targetStepZ) {
      stepperZ.step(1);
      Step_currentZ++;
    } else if (Step_currentZ > targetStepZ) {
      stepperZ.step(-1);
      Step_currentZ--;
    }

    delay(1); // Giảm tải CPU
  }

  // Cập nhật tọa độ hiện tại
  CurrentX = (Step_currentX * 200 / 1000)  - 25; // Chuyển bước về mm
  CurrentY = (Step_currentY * 200 / 1000) - 20;
  CurrentZ = (Step_currentZ * 40 / 1000) -  20;

// Gửi giá trị hiện tại về Python
  Serial.print("CURRENT_POSITION: X=");
  Serial.print(CurrentX);
  Serial.print(", Y=");
  Serial.print(CurrentY);
  Serial.print(", Z=");
  Serial.print(CurrentZ);
  Serial.print(", S=");
  Serial.print(Speed);
  Serial.println();
}

void Home() {
  // Bắt đầu quá trình đưa về home
  Serial.println("Đang đưa các trục về vị trí Home...");
  while (digitalRead(limitSwitchX) == 0) stepperX.step(1);
  Step_currentX = 0;
  while (digitalRead(limitSwitchY) == 0) stepperY.step(-1);
  Step_currentY = 0;
  while (digitalRead(limitSwitchZ) == 0) stepperZ.step(-1);
  Step_currentZ = 0;
  moveToPositionXYZ(5, 0, 0, 30);
  //moveToPositionXYZ(15, 15, 0, 30);
  //moveToPositionXYZ(15, 15, 10, 30);
}


void Center() {
  moveToPositionXYZ(100, 200, 0, 40);
}


void Truyen() {
  switch (GT) {
    case 'H': Home(); break;
    case 'C': Center(); break;
    case 'h': moveToPositionXYZ(0, 0, 0, 40); break;
    case 'M': Mode = 1; break; // Điều khiển tọa độ
    case 'X': moveToPositionXYZ(CurrentX + 10 , CurrentY , CurrentZ, 40); break;
    case 'x': moveToPositionXYZ(CurrentX - 10 , CurrentY , CurrentZ, 40); break;
    case 'Y': moveToPositionXYZ(CurrentX , CurrentY + 10 , CurrentZ, 40); break;
    case 'y': moveToPositionXYZ(CurrentX , CurrentY - 10 , CurrentZ, 40); break;
    case 'Z': moveToPositionXYZ(CurrentX , CurrentY , CurrentZ + 5, 40); break;
    case 'z': moveToPositionXYZ(CurrentX , CurrentY , CurrentZ - 5, 40); break;
    case 'L': digitalWrite(LED, HIGH); break;
    case 'l': digitalWrite(LED, LOW); break;
    case 'p':
      Serial.println("-Toa do-");
      Serial.println(CurrentX);
      Serial.println(CurrentY);
      Serial.println(CurrentZ);
      break;
    case 'P':
      Serial.println("- So buoc-");
      Serial.println(Step_currentX);
      Serial.println(Step_currentY);
      Serial.println(Step_currentZ);
      break;
    default:
      Serial.println("--=KHL=--");
      break;
  }
}
