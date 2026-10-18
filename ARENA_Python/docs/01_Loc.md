## Cách học và tiếp tục làm phần này

1. Chạy demo theo README, đăng nhập `admin`. Thêm một tướng thử; khóa/mở một tài khoản thử; xem nhật ký. Không tự khóa tài khoản admin đang dùng.
2. Đọc `create_app`: cấu hình DB/secret → đăng ký blueprint → tải người dùng → CSRF → context/template → xử lý lỗi. Khi thêm blueprint, chỉ đăng ký ở đây một lần.
3. Đọc `schema.sql` theo nhóm: định danh → đội → giải/đội hình → trận/ván → thống kê/nhật ký. Giải thích được vì sao memberships dùng chỉ mục một đội hiện tại và rosters có holding cho hồ sơ đang giữ chỗ.
4. Đọc `db.transaction`: toàn bộ một nghiệp vụ cùng commit hoặc rollback; không commit ở giữa khi tạo nhánh hoặc lưu ván. Nếu thêm bảng, phối hợp Khang/Trân cập nhật service và Nghi thêm ca kiểm thử liên quan.
5. Thử `python run.py --backup backups/demo.sqlite3`, kiểm tra lệnh từ chối ghi đè file đã có. Học quy trình phục hồi trong tài liệu vận hành.
6. Trước bàn giao, chạy toàn bộ test, tạo demo bằng thư mục mới và kiểm tra các tài khoản. Chỉ đóng gói source/docs/tests, không đóng gói DB đang dùng và secret.

## Đầu vào/đầu ra phải giữ

`DATABASE` là đường dẫn tuyệt đối tới SQLite. `create_app` nhận config để Nghi dùng database tạm. `get_db` trả connection theo app context, row_factory=sqlite3.Row. `transaction` giữ quyền ghi bằng BEGIN IMMEDIATE. `audit` nhận người dùng có id. Schema không tự migrate bản cũ.

`admin` có admin/audit; BTC có event/result/audit; referee chỉ result; student chỉ team. Không gộp admin thành người được sửa mọi kết quả. Người đang thuộc đội không được chuyển sang vai trò nhân sự giải ngay.

## Kiểm tra riêng

```bash
python -m pytest tests -q -k 'database_constraints or admin_self_lock or seed_idempotent or private_pages'
```

Sản phẩm trình bày: schema 20 bảng, giải thích chỉ mục/FK, sơ đồ thành phần, khởi tạo/sao lưu, một thao tác quản trị có nhật ký. Nộp cả database schema và source, không chỉ ảnh giao diện.
