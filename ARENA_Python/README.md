# ARENA — Quản lý giải đấu Liên Quân Mobile

Bản triển khai đồ án bằng **Python 3.11 + Flask + SQLite**, giao diện web tiếng Việt. Mã nguồn của cả 5 thành viên đã ghép thành một ứng dụng. Mỗi người làm trên bản sao đầy đủ của thư mục này; không chạy các mô-đun như những chương trình riêng.

## Chạy nhanh

1. Cài Python **3.11**, có `pip` và Python Launcher nếu dùng Windows.
2. Giải nén toàn bộ ZIP vào thư mục có quyền ghi. Không chạy trực tiếp trong ZIP.
3. Windows: nhấp đúp `start_windows.bat`. macOS/Linux: mở terminal tại thư mục dự án và chạy `bash start_mac_linux.sh`.
4. Mở **http://127.0.0.1:5000**. Giữ cửa sổ terminal mở khi dùng. Dừng bằng `Ctrl+C`.

Lần đầu cần Internet để tải thư viện. Những lần sau dữ liệu được giữ trong `instance/arena.sqlite3`. Chế độ `--demo` chỉ nạp khi chưa có tài khoản, không ghi đè dữ liệu hiện có.

### Chạy bằng lệnh trên Windows

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py --demo
```

### Chạy bằng lệnh trên macOS/Linux

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --demo
```

Nếu cổng 5000 đang bận, thêm `--port 5001` rồi mở `http://127.0.0.1:5001`.

## Tài khoản DEMO

Mật khẩu chung: **`Arena@2026`**. Đây là dữ liệu giả để học và trình diễn, không phải tài khoản của các thành viên nhóm.

| Tên đăng nhập | Vai trò | Cách dùng |
|---|---|---|
| `admin` | Quản trị | Tài khoản, khoa/lớp, danh mục tướng, nhật ký |
| `btc` | Ban tổ chức | Tạo giải, duyệt hồ sơ, lịch, kết quả, quỹ và tổng kết |
| `trongtai` | Trọng tài | Nhập kết quả các trận được phân công |
| `doitruong1` … `doitruong4` | Sinh viên/đội trưởng | Hồ sơ, đội hình, đăng ký giải |
| `sv02` … `sv07` | Thành viên đội 1 | Xem đội và hồ sơ cá nhân |

Quản trị và BTC là hai vai trò tách biệt. Muốn điều hành giải phải dùng `btc`, không dùng `admin`. Mọi tài khoản đã đăng nhập đều có mục **Đổi mật khẩu**.

## Có gì trong bản này?

- Đăng ký, đăng nhập, đổi mật khẩu, hồ sơ tuyển thủ; phân quyền phía máy chủ.
- Thành lập đội, lời mời có xác nhận, chuyển đội trưởng, rời đội; khóa nhân sự khi đội đang có hồ sơ giải.
- Đăng ký đúng 5 chính và tối đa 2 dự bị, duyệt/từ chối/rút hồ sơ; không đăng ký trùng tuyển thủ trong cùng giải.
- Loại trực tiếp có miễn vòng và vòng tròn một lượt; từ 2–32 đội; Bo3/Bo5; sửa lịch từng trận, chống trùng đội/trọng tài.
- Nhập 10 người thực tế thi đấu mỗi ván, K/D/A và vàng; kiểm tra ngoại lệ K/D; chống lưu từ trang cũ; chuyển đội thắng lên nhánh kế tiếp.
- Xếp hạng, KDA, thưởng theo hạng, đồng hạng, bổ sung quỹ, chốt giải và khóa kết quả.
- Báo cáo CSV UTF-8 và giao diện in/lưu PDF; nhật ký và thông báo trong ứng dụng.
- Giao diện tối, tìm giải, bố cục thích ứng màn hình nhỏ; lịch/nhánh cập nhật mỗi 8 giây.

## Tài liệu theo phân công

| Thành viên | Trách nhiệm chính | Hướng dẫn |
|---|---|---|
| Nguyễn Tấn Lộc — 50.01.104.084 | Trưởng nhóm, dữ liệu, quản trị, tích hợp | [01_Loc.md](docs/01_Loc.md) |
| Phùng Đức Duy Khang — 50.01.104.071 | Lịch, nhánh, xử lý kết quả | [02_Khang.md](docs/02_Khang.md) |
| Nguyễn Lâm Chấn Nghi — 50.01.104.099 | Phân tích, kiểm thử, vận hành/demo | [03_Nghi.md](docs/03_Nghi.md) |
| Đặng Trung Tín — 50.01.104.161 | Giao diện, trải nghiệm sử dụng | [04_Tin.md](docs/04_Tin.md) |
| Văn Thị Huyền Trân — 50.01.104.165 | Tài khoản, đội, hồ sơ giải, báo cáo | [05_Tran.md](docs/05_Tran.md) |

Đọc tiếp [kiến trúc và ghép code](docs/06_Kien_truc_va_ghep_code.md), [đối chiếu Lab](docs/07_Doi_chieu_Lab.md), [kiểm thử](docs/08_Kiem_thu.md), [kịch bản demo](docs/09_Kich_ban_demo.md), [vận hành](docs/10_Van_hanh.md).

## Chạy kiểm thử

Cài thêm `requirements-dev.txt`, rồi chạy bằng Python trong môi trường ảo:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

Hai lệnh trên giả định đã kích hoạt `.venv`; nếu chưa, thay `python` bằng `.venv\Scripts\python.exe` (Windows) hoặc `.venv/bin/python` (macOS/Linux). Kiểm thử dùng database tạm, không thay dữ liệu bạn đang dùng.

## Phạm vi triển khai

Đây là bản đồ án chạy cục bộ, chưa phải hệ thống triển khai Internet. SQLite thay SQL Server của bản thiết kế trước; Python thay phần minh họa C#. Không chạy script SQL Server của Lab03 vào SQLite. Tất cả khác biệt được ghi trong tài liệu đối chiếu.

Chưa có tải logo, gửi email, quên mật khẩu qua email, kết nối API game, WebSocket, đo tải 10.000 người dùng hoặc bộ cài EXE. Không dùng máy chủ Flask tích hợp để công khai dịch vụ. Dữ liệu mẫu và mật khẩu mẫu chỉ dành cho trình diễn. Khi muốn nhập dữ liệu thật từ đầu, dùng quy trình `--init-admin` trong tài liệu vận hành.
