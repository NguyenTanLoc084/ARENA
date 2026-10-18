# Cài đặt, dữ liệu và xử lý sự cố

## Môi trường

Python3.11, pip, trình duyệt hiện đại. Runtime chỉ cần Flask/Werkzeug/tzdata và các phụ thuộc trong requirements. SQLite có sẵn trong Python. Node.js/Playwright chỉ dùng kiểm tra giao diện của nhà phát triển, không cần khi sử dụng phần mềm.

Mở terminal đúng thư mục có run.py. Trên Windows dùng `py -3.11`; nếu không có Python Launcher, dùng đường dẫn chính xác của Python3.11. Không chọn Python khác chỉ vì lệnh `python` trỏ tới bản đó. Khi đổi máy, tạo lại .venv, không sao chép .venv giữa các hệ điều hành.

## Khởi tạo không có dữ liệu mẫu

Dùng một bản giải nén mới chưa chạy demo:

```bash
python run.py --init-admin
python run.py
```

Thay `python` bằng executable trong .venv nếu chưa kích hoạt môi trường. Lệnh đầu hỏi tên và mật khẩu (ẩn khi gõ), từ chối nếu DB đã có tài khoản. Đăng nhập admin, thêm khoa trước, lớp sau và danh mục tướng. Cho người dùng đăng ký. Tài khoản nhân sự BTC/trọng tài có thể đăng ký hồ sơ rồi admin gán organizer/referee trước khi họ tham gia đội. Sau đó BTC tạo giải, người chơi tạo đội và đăng ký.

Dữ liệu mẫu không phải dữ liệu thật. Nếu dùng ngoài buổi học, khởi tạo riêng bằng `--init-admin`; không mở bản demo chứa mật khẩu công khai ra mạng. Mọi người dùng có thể đổi mật khẩu trong menu.

## Sao lưu và phục hồi

```bash
python run.py --backup backups/arena-2026-10-18.sqlite3
```

Lệnh dùng SQLite backup API, sao lưu nhất quán cả khi WAL đang hoạt động. Không copy riêng file DB khi server vẫn ghi. Lệnh không ghi đè file đã tồn tại; đặt tên khác cho bản mới.

Phục hồi thủ công có kiểm soát:

1. Dừng server bằng Ctrl+C, đóng các chương trình đang mở DB.
2. Giữ nguyên toàn bộ thư mục instance hiện tại dưới một tên sao lưu, gồm DB/WAL/SHM/secret nếu có; không xóa bản cũ.
3. Tạo instance mới và copy bản backup cần phục hồi thành `instance/arena.sqlite3`. Không đưa WAL/SHM cũ vào thư mục mới.
4. Chạy `python run.py`, đăng nhập và kiểm tra giải/đội/kết quả. Nếu không giữ secret cũ, phiên đăng nhập cũ sẽ hết hiệu lực; dữ liệu vẫn giữ.

Không đưa file backup/secret lên repo công khai. Schema hiện dùng CREATE IF NOT EXISTS, không có migration tự động; backup không thay thế migration khi nâng cấp cấu trúc.

## Vấn đề thường gặp

| Hiện tượng | Xử lý |
|---|---|
| Không có Flask | Cài requirements bằng đúng Python trong .venv |
| Không có Python3.11 | Cài Python3.11 kèm pip/Launcher, kiểm tra phiên bản rồi tạo lại .venv |
| Address already in use | Dừng bản đang chạy hoặc thêm --port5001 (có khoảng trắng: `--port 5001`) |
| Không mở được trang | Giữ terminal server mở; mở đúng localhost/cổng, không mở HTML từ file |
| Form400 sau đăng xuất/đăng nhập tab khác | Tải lại trang để lấy CSRF/phiên mới |
| Dữ liệu đã thay đổi | Có người/tab khác vừa lưu; tải lại và đối chiếu trước khi nhập tiếp |
| Không mời/rời đội được | Đội đang có hồ sơ chưa kết thúc; kiểm tra khóa đội hình |
| Không xếp lịch được | Duyệt hết pending, tối thiểu2 đội, khóa đăng ký, chọn giờ sau đóng và không trùng giải khác |
| Không chốt được | Kiểm tra trận còn thiếu, đồng hạng cần lý do và tổng thưởng tính cho từng đội |
| Khóa đăng nhập429 | Đợi5 phút sau nhiều lần sai; kiểm tra đúng tài khoản/mật khẩu |
| Tạo demo không làm mới dữ liệu | Đây là chủ ý chống ghi đè. Muốn demo mới, dùng bản sao dự án sạch |
| CSS/JS không hiện | Chạy server và kiểm tra đường dẫn static; không dùng HTML tải riêng |

## Phạm vi vận hành

Mặc định chỉ lắng nghe127.0.0.1. Flask server tích hợp dùng học/demo. Triển khai công khai cần WSGI production, HTTPS, bí mật cấu hình riêng, COOKIE_SECURE=1, giám sát/sao lưu, kiểm tra bảo mật và tải. Bản này chưa triển khai hoặc kiểm chứng những hạng mục đó.

Giới hạn đăng nhập là theo IP+tên tài khoản, không phải giải pháp chống tấn công phân tán. Đổi mật khẩu xóa phiên hiện tại, chưa thu hồi mọi cookie ở thiết bị khác. Chưa có quên mật khẩu qua email; quản trị có thể khóa tài khoản khi cần và lập quy trình hỗ trợ riêng.
