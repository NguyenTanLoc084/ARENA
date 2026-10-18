# Nguyễn Lâm Chấn Nghi — phân tích, kiểm thử, vận hành/demo

MSSV: 50.01.104.099. Phần code của Nghi là `tests/conftest.py`, `tests/test_application.py`; phần tài liệu gồm đối chiếu Lab, báo cáo kiểm thử, kịch bản demo và vận hành. Đây là phần kỹ thuật có mã chạy độc lập với dữ liệu demo thật của nhóm, không chỉ viết báo cáo.

## Cách làm

1. Cài requirements-dev bằng Python3.11. Chạy `python -m pytest tests -q`. Đọc lỗi đầu tiên, tái hiện bằng tài khoản và dữ liệu tương ứng; không xóa assertion để làm test xanh.
2. Đọc fixture: session tạo database mẫu một lần, mỗi test sao chép sang thư mục tạm. Nhờ vậy test độc lập và không làm mất dữ liệu của nhóm.
3. Nối yêu cầu với kiểm thử: 5 chính/2 dự bị → invalid_registration; không ghi đè → stale_update; nguyên tử → schedule_conflict_atomic/result rollback; miễn vòng và thưởng → knockout_to_final; quyền → csrf_and_role/referee; dữ liệu cá nhân → public_privacy.
4. Khi nhận tính năng mới, mô tả đầu vào, tiền điều kiện, thao tác, kết quả, tác động DB. Viết một ca đúng và các ca sai có rủi ro thật; không chỉ kiểm tra hàm trả đúng kiểu.
5. Chạy demo theo tài liệu 09 trên thư mục bản phát hành mới; kiểm tra đóng/mở chương trình vẫn giữ dữ liệu. Mở hai cửa sổ cùng ván để kiểm tra form cũ.
6. Kiểm tra UI desktop/mobile, nhập sai, nút quay lại, cuộn bảng, menu, print. Ghi đúng những môi trường đã chạy; Windows batch được cung cấp nhưng kiểm tra Python trong môi trường Linux không chứng minh đã chạy Windows.

## Mẫu báo lỗi

Mã yêu cầu; phiên bản source; hệ điều hành/Python; vai trò; tiền điều kiện; bước tái hiện; mong đợi; thực tế; thông báo/trạng thái HTTP; ảnh hoặc log đã bỏ dữ liệu riêng; mức độ; người sửa; kết quả test lại. Lỗi nghiệp vụ rollback phải kiểm tra cả dữ liệu sau lỗi, không chỉ nhìn thông báo đỏ.

## Lệnh kiểm tra

```bash
python -m pytest tests -q
python -m compileall -q app run.py tests
python run.py --backup backups/truoc-demo.sqlite3
```

Test service kiểm chứng nguyên tắc nghiệp vụ, Flask test client kiểm tra render/form/quyền. Kiểm tra trình duyệt bổ sung JS, luồng bấm nút và responsive; không thể thay bằng chỉ test HTTP.

Sản phẩm bàn giao: ma trận yêu cầu–test, kết quả chạy thật, lỗi còn biết, kịch bản8–10 phút, checklist cài đặt. Không ghi “100% không lỗi”, “đạt10.000 người dùng” khi chưa đo.
