# Báo cáo kiểm thử bản bàn giao

Ngày chạy: 18/10/2026. Runtime kiểm chứng: **CPython3.11.17**, Flask3.1.2, Werkzeug3.1.9, SQLite qua Python, pytest8.4.2; môi trường Linux. Các phiên bản phụ thuộc đã ghim trong requirements. Không suy diễn kết quả này thành đã chạy mọi hệ điều hành.

## Kiểm thử tự động Python

Lệnh: `python -m pytest tests -q`.

Kết quả: **50 passed**. Dữ liệu được tạo trong database tạm độc lập cho từng test. Các lần kiểm tra lỗi nghiệp vụ xác nhận không để lại bản ghi/phiên bản nửa chừng.

| Rủi ro/yêu cầu | Bằng chứng trong tests/test_application.py | Kết quả |
|---|---|---|
| Template/routes theo từng vai trò | all_pages;5 nhóm vai trò, nhiều URL mỗi nhóm | Đạt |
| Truy cập riêng tư, CSRF, quyền | private_pages_require_login, csrf_and_role | Đạt |
| Đăng nhập thật, giới hạn thử sai | real_login_and_lockout | Đạt |
| Đổi mật khẩu cho admin; kết thúc phiên hiện tại | password_all_roles | Đạt |
| Khởi tạo admin dữ liệu trống | clean_admin_initialization | Đạt |
| Không công khai định danh riêng | public_privacy | Đạt |
| Nạp demo không ghi đè | seed_idempotent | Đạt |
| Mỗi cặp vòng tròn đúng1 lần với2/3/4/5/16/31/32 đội | round_robin_every_pair_once | Đạt |
| Lịch trùng giải khác rollback cả vòng/trận | schedule_conflict_atomic | Đạt |
| Sửa lịch trùng | edit_schedule_conflict | Đạt |
| Loại trực tiếp3 đội có miễn vòng;4 đội Bo5; hoàn tất thưởng | knockout_to_final_prizes_and_release | Đạt |
| Thiếu/trùng người, sai roster/tướng, âm KDA, lệch K/D, nhảy ván, sai thắng/thời lượng | invalid_result_rolls_back;9 trường hợp | Đạt |
| Form cũ không ghi đè; KDA không lỗi chia0 | stale_update_and_zero_deaths | Đạt |
| Trọng tài đúng phân công; ngoại lệ chỉ BTC | referee_assignment_and_exception | Đạt |
| Vòng sau đã bắt đầu thì khóa sửa nguồn | source_locked_after_next_starts | Đạt |
| Sửa nguồn xóa/chuyển đội ở nhánh sau đúng | edit_completed_source_recalculates_next | Đạt |
| Gửi, duyệt, rút và giải phóng roster | registration_review_withdraw | Đạt |
| Sai5 chính/dự bị/thành viên | invalid_registration;4 trường hợp | Đạt |
| Đăng ký không tự nâng quyền; lời mời/chấp nhận/quyền đội trưởng | signup_team_invitation_flow | Đạt |
| Bảo vệ admin; quỹ chỉ được tăng | admin_self_lock_and_budget | Đạt |
| Vòng tròn chốt; quỹ thiếu rollback toàn bộ | roundrobin_budget_atomic_finalization | Đạt |
| Chỉ mục một đội, giữ chỗ cùng giải và FK | database_constraints | Đạt |
| Giờ Việt Nam/UTC; chống công thức CSV | time_and_csv | Đạt |

Một test có thể được chạy nhiều lần với dữ liệu tham số; tổng50 là số trường hợp pytest báo, không phải50 chức năng độc lập hoặc độ bao phủ100%.

## Kiểm tra trình duyệt

Đã dùng Chromium headless qua Playwright, chạy ứng dụng Flask thật với Python3.11, không chỉ giả lập HTML. Script tái chạy ở `tests/browser_smoke.cjs`, dùng database tạm rồi dọn sau khi kết thúc.

Đã kiểm chứng:

- Đăng nhập qua form thật; tìm kiếm giải chỉ còn card phù hợp.
- Chọn chính/dự bị loại trừ nhau; gửi hồ sơ bằng nút thật; BTC bấm “Duyệt hồ sơ” và nhận thông báo thành công. Kiểm tra này bảo đảm JS khóa nút không làm mất name/value của quyết định.
- Nhập ván thứ2 bằng form; trận Bo3 hoàn tất và không còn form nhập ván mới.
- Các trang tổng quan, giải, trận, báo cáo, đổi mật khẩu trả200; không tràn ngang toàn trang ở1440 px và390 px. Bảng dài có vùng cuộn riêng.
- Menu mobile cập nhật aria-expanded, polling báo đã đồng bộ, không phát sinh pageerror JavaScript.
- Đã xem ảnh nội bộ của trang tổng quan desktop/mobile và trang nhập ván để kiểm tra chữ tiếng Việt, bố cục, tương phản và bảng nhập. Ảnh kiểm tra không nằm trong gói giao.

Lệnh tùy chọn để thành viên có Node.js kiểm tra lại:

```bash
npm install --no-save playwright@1.62.1
npx playwright install chromium
node tests/browser_smoke.cjs
```

Trước đó kích hoạt .venv để `python` là3.11; hoặc đặt biến `PYTHON` bằng đường dẫn executable. Script dùng cổng5012 mặc định; biến `TEST_PORT` đổi cổng khi cần. Node.js không phải phụ thuộc chạy phần mềm. Môi trường kiểm chứng dùng bản Chromium phù hợp môi trường headless và đường dẫn executable cấu hình riêng; các assertion trong script giữ nguyên.

## Giới hạn bằng chứng

Chưa chạy batch Windows trên máy Windows thật, chưa kiểm tra Safari/Firefox, chưa đo tải lớn hoặc điều kiện mạng chậm, chưa kiểm thử thanh toán vì ứng dụng chỉ quản lý mức thưởng, không chuyển tiền. Chưa có bài kiểm thử cạnh tranh nhiều tiến trình thực tế; hiện kiểm chứng ràng buộc UNIQUE, rollback và form version cũ. Bản này không được mô tả là không thể có lỗi hoặc đã đạt10.000 người dùng.
