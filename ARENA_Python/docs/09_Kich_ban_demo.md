# Kịch bản demo 8–10 phút

Chuẩn bị bản sao thư mục sạch, chạy `--demo`. Không dùng số liệu thật của sinh viên khi trình diễn công khai. Đóng những tab có dữ liệu riêng trước khi chiếu màn hình.

| Phút | Người | Thao tác và ý nghĩa |
|---|---|---|
| 0–1 | Lộc | Mở tổng quan, nêu đề tài/công nghệ và5 vai trò trong nhóm; đăng nhập admin, mở danh mục/nhật ký |
| 1–3 | Trân | Dùng doitruong1 mở Freshman Open, chọn5 chính+2 dự bị, gửi; chuyển btc duyệt hồ sơ; nói rõ một đội qua nhiều giải |
| 3–5 | Khang | Campus Cup đã có4 đội duyệt và khóa đăng ký. Tạo lịch ngày không trùng giải khác (ví dụ sau3 ngày), Bo3, trongtai. Bắt đầu giải, mở trận bán kết |
| 5–7 | Khang | Bắt đầu trận, nhập2 ván cùng đội thắng, đúng5 người mỗi đội. Trình diễn đội thắng chuyển lên chung kết; có thể dùng số liệu K/D cân bằng đơn giản |
| 7–8 | Tín | Thu nhỏ màn hình để thấy menu mobile, vùng cuộn bảng; giới thiệu lịch tự cập nhật, trang báo cáo và In/Lưu PDF |
| 8–9 | Nghi | Chạy pytest, trình diễn một lỗi dữ liệu có rollback, giới thiệu test form cũ và khóa sửa nguồn |
| 9–10 | Trân/Lộc | Nêu công thức điểm/KDA/thưởng, phạm vi và khác biệt triển khai với Lab; trình bày báo cáo tổng kết |

## Hoàn tất Campus Cup trước buổi bảo vệ dài

Tạo lịch4 đội → bắt đầu giải → bán kết1 thắng2 ván → bán kết2 thắng2 ván → chung kết có đủ2 đội → bắt đầu chung kết → thắng2 ván → quay về giải → nhập căn cứ “Hai đội thua bán kết đồng hạng ba theo điều lệ” → chốt.

Mức thưởng demo: hạng1 3.000.000 đ, hạng2 2.000.000 đ; hạng3 0 đ. Quỹ5.000.000 đ. Sau chốt, bảng chung cuộc có4 đội, không còn sửa kết quả. Không cần chờ đúng giờ dự kiến: thao tác bắt đầu do BTC/trọng tài chủ động.

## Dữ liệu mẫu

Campus Cup: loại trực tiếp, đã khóa đăng ký, chưa có lịch. Student League: vòng tròn4 đội,6 trận, trận đầu có1 ván; lịch mẫu bắt đầu ngày sau thời điểm tạo dữ liệu để người xem thấy lịch sắp tới. Freshman Open: đang mở đăng ký30 ngày kể từ lúc tạo demo.

Đội mẫu có7 người và đang tham gia2 giải, vì vậy thay nhân sự bị khóa là đúng nghiệp vụ. Muốn demo lời mời/chuyển đội trưởng, tạo2 tài khoản mới và một đội mới trước; hoặc dùng test tự động `signup_team_invitation_flow`. Không coi nút bị chặn do đang dự giải là lỗi phần mềm.

Nếu demo đã cũ quá30 ngày, Freshman Open sẽ hết hạn đúng theo ngày đã lưu. Dùng BTC tạo một giải mới hoặc dùng bản sao dự án sạch để nạp demo mới; không chỉnh đồng hồ máy hoặc sửa DB bằng tay.
