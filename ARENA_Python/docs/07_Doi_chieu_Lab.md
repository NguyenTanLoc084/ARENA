# Đối chiếu bản Python với Lab03/Lab04

Bản Python kế thừa nghiệp vụ đã thiết kế trong bộ Lab cho đề tài Liên Quân. Đây là một phương án triển khai cụ thể, không phải bản dịch nguyên xi script SQL Server. Khi đưa vào báo cáo cuối kỳ, thêm mục “Điều chỉnh công nghệ triển khai” và dùng đúng bảng dưới đây để các chương nhất quán.

## Ánh xạ dữ liệu

| Thiết kế Lab03 | Bản Python/SQLite |
|---|---|
| KHOA | colleges |
| LOP | classes |
| SINH_VIEN | students; id nội bộ, code là MSSV duy nhất |
| VAI_TRO | users.role với CHECK cố định 4 vai trò |
| TAI_KHOAN | users |
| CHUC_NANG + PHAN_QUYEN | role_permissions; quyền cố định trong seed.PERMISSIONS |
| DOI_TUYEN | teams; captain_id trực tiếp đến students |
| THANH_VIEN_DOI | memberships |
| GIAI_DAU | events |
| DANG_KY | entries |
| DOI_HINH_GIAI | rosters |
| VONG_DAU | rounds |
| TRAN_DAU | matches; next_id/next_slot liên kết nhánh |
| TUONG | heroes |
| VAN_DAU | games |
| CHI_SO_VAN | stats |
| MUC_THUONG | prizes |
| KET_QUA_GIAI | final_results |
| NHAT_KY | audit |
| THONG_BAO | notifications |
| Bổ sung triển khai | login_limits chống thử đăng nhập liên tiếp |

Lab03 có 21 bảng khái niệm/quan hệ được mô tả; schema chạy có 20 bảng do gộp danh mục vai trò/chức năng và bổ sung login_limits. Khóa nội bộ dùng INTEGER PRIMARY KEY; tên tiếng Anh không thay đổi ý nghĩa nghiệp vụ. UNIQUE và FK nằm trong schema; quy tắc đủ 5 người, đúng đội, vòng đời, tổng thưởng và chuỗi ván nằm trong service có giao dịch.

Không dùng stored procedure/trigger SQL Server của Lab03 trong bản này. Đặt kiểm tra liên bảng tại service để tập trung rollback và thông báo lỗi. SQLite không tự bảo đảm mọi luật khi người ngoài sửa DB trực tiếp; nhóm phải cập nhật dữ liệu qua ứng dụng.

## Ánh xạ giao diện/xử lý Lab04

| Nhóm màn hình | Route/template chạy |
|---|---|
| Đăng nhập/đăng ký | /login, /register |
| Hồ sơ/đổi mật khẩu | /profile, /password |
| Đội và lời mời | /my-team, team.html |
| Danh sách giải | /, home.html |
| Tạo giải | /events/new |
| Đăng ký đội hình | /events/id/register |
| Duyệt, lịch, nhánh, thưởng | /events/id |
| Chi tiết trận/nhập ván/KDA | /matches/id |
| Báo cáo/xuất file | /events/id/report, /events/id/report.csv |
| Quản trị | /admin |
| Nhật ký/thông báo | /audit, /notifications |

C#/.NET trong phần minh họa thiết kế được thay bằng Python 3.11/Flask; đối tượng dữ liệu biểu diễn bằng SQLite Row và dict; không triển khai ORM hoặc desktop GUI. Sơ đồ xử lý giữ các bước xác thực → kiểm tra quyền → kiểm tra nghiệp vụ → giao dịch → phản hồi.

## Những điểm cần ghi đúng trong báo cáo bảo vệ

- Cập nhật lịch/nhánh bằng polling 8 giây; không phải WebSocket/SignalR. Trang kết quả trận và báo cáo cần tải lại để xem số mới. Không hứa realtime tức thời.
- Hỗ trợ loại trực tiếp và vòng tròn một lượt 2–32 đội, không có nhánh thua, chia bảng rồi playoff hoặc đấu lại xử lý hòa. Vòng tròn bằng cả điểm/hiệu số/số ván thắng thì đồng hạng; loại trực tiếp không tổ chức tranh hạng ba, hai đội thua bán kết cùng hạng ba.
- Avatar đội dùng chữ viết tắt, chưa có tải logo. Chỉ số nhập thủ công sau đối soát, không liên thông game. Không kiểm tra cấm/chọn tướng theo luật giải chuyên nghiệp.
- Không có chỉnh điểm thắng/thua trên UI: dùng 3/0. Không tùy chỉnh vai trò bằng giao diện; admin gán một trong bốn vai trò có sẵn.
- CSV chứa bảng xếp hạng; bảng KDA nằm trong báo cáo xem/in. PDF được lưu qua hộp thoại in của trình duyệt, không dùng máy chủ tạo PDF.
- Chưa có email/SMS hoặc khôi phục mật khẩu tự động. Thông báo nội bộ cho lời mời và duyệt hồ sơ. Hướng dẫn vận hành có khởi tạo admin riêng.
- Chưa đo tải 10.000 người dùng, chưa kiểm toán an ninh chuyên nghiệp. Bản chạy local dùng SQLite và máy chủ Flask phục vụ trình diễn, không dùng số lượng người dùng trong yêu cầu phi chức năng làm kết quả đã đạt.
- Không cung cấp thao tác xóa giải/đội có lịch sử hoặc mở lại giải đã chốt; tránh phá liên kết. Khi thử lại demo, dùng bản sao thư mục dự án sạch, không xóa dữ liệu đang cần.

Nếu môn học bắt buộc SQL Server hoặc một chức năng chưa có ở trên, nhóm phải thống nhất điều chỉnh với giảng viên; tài liệu này không ngầm coi công nghệ khác là tương đương hoàn toàn.
