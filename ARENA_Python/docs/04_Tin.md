## Cách triển khai tiếp

1. Chạy ứng dụng, xem trang tổng quan ở màn hình rộng rồi thu nhỏ. Đọc `base.html`: sidebar/topbar, tài khoản, breadcrumb, flash, main và footer. Mọi trang kế thừa base để cùng một hệ màu/khoảng cách.
2. Đọc CSS từ biến màu đến thành phần `.panel`, `.btn`, `.badge`, `.table-scroll`, `.bracket`, responsive và print. Khi đổi màu, sửa token dùng chung trước; không chèn style inline vì CSP chặn inline.
3. Mở lần lượt trang giải, trận, đăng ký đội hình, quản trị. Nội dung nhiều cột đặt trong vùng cuộn bảng; không làm toàn bộ viewport cuộn ngang. Nhãn và aria-label phải xác định đúng input.
4. Sửa form phải giữ `method=post`, `csrf_field()`, `name`, action `url_for`. Các button như decision/action có name/value là dữ liệu nghiệp vụ; không disable trước khi trình duyệt tạo dữ liệu gửi.
5. `app.js` chỉ hỗ trợ UX, không thay kiểm tra server. Chọn chính/dự bị tự bỏ lựa chọn trùng trong trình duyệt, nhưng server vẫn kiểm tra lại. Sau lỗi có thể quay lại để sửa; không tự gửi POST lần nữa.
6. Polling gọi API trạng thái8 giây rồi cập nhật riêng `#live-region` khi có thay đổi. Không thay cả trang vì có thể xóa nội dung BTC đang nhập. Bảng xếp hạng/trang trận chưa tự đồng bộ; người dùng tải lại.
7. Trang report dùng print CSS để ẩn menu/nút và chuyển màu dễ in. Nút In/Lưu PDF mở hộp thoại trình duyệt; hướng dẫn chọn Save as PDF, không đổi nút thành tải file PDF giả.

## Phối hợp

Trân quyết định tên trường auth/team/report, Khang quyết định lịch/result. Tín nhận context mới từ họ, không truy vấn SQL trong template. Lộc quyết định CSP và routes chung. Nghi kiểm tra luồng với chuột/bàn phím và kích thước màn hình.

## Tự kiểm tra

- Các link chính đúng route, không có `href="#"` cho chức năng chưa triển khai.
- Đăng nhập/đăng xuất, nút duyệt/từ chối gửi đúng value; button gửi lần hai bị chặn.
- Menu có aria-expanded; input có label; focus nhìn thấy; thông báo đọc được.
- Màn hình390 px và1440 px: không cắt nút chính, bảng vẫn cuộn trong panel.
- Không đưa đường dẫn DB, khóa, traceback hoặc chi tiết triển khai vào thông báo cho người dùng.

Chạy smoke template: `python -m pytest tests -q -k all_pages`. Bài bảo vệ nên trình diễn trang tổng quan, nhánh, bảng nhập10 người và báo cáo in.
