# Văn Thị Huyền Trân — tài khoản, đội, đăng ký và báo cáo

MSSV: 50.01.104.165. Source đã tích hợp: `app/auth.py`, `app/team.py`, `app/reports.py`. Phối hợp Tín cho các template tương ứng. Trân cũng tổng hợp phần nghiệp vụ trong báo cáo cuối kỳ; Nghi xác nhận bằng test.

## Cách làm phần tài khoản/đội

1. Đăng ký một tài khoản thử mới. Vai trò luôn là student, không nhận role từ form. Mật khẩu băm scrypt bằng Werkzeug; không lưu mật khẩu rõ.
2. Tạo đội bằng tài khoản mới. Một người khác đăng ký tài khoản; đội trưởng mời bằng MSSV, người nhận đăng nhập để chấp nhận. Không thêm thẳng một người vào đội khi chưa đồng ý.
3. Theo dõi team_locked: nếu đội có hồ sơ pending/approved ở giải chưa kết thúc, chưa thay nhân sự. Đội trưởng chuyển quyền trước khi rời đội. Mỗi sinh viên chỉ có một membership accepted.
4. Đăng ký giải dùng 5 chính và tối đa2 dự bị. Các ID phải thuộc thành viên đã chấp nhận. Hồ sơ tạo rosters giữ chỗ cùng giải; từ chối/rút/chốt giải sẽ giải phóng holding theo từng trường hợp.
5. BTC duyệt hoặc từ chối có lý do; đội trưởng đọc thông báo và có thể nộp lại khi còn mở. Không sửa roster của hồ sơ approved trực tiếp.
6. Đổi Ingame ID bị khóa khi đang có roster holding. Các trang công khai chỉ đưa IGN, không đưa MSSV/họ tên riêng.

## Cách làm báo cáo/thưởng

`standings` là nguồn xếp hạng chung cho UI và CSV. Không viết lại công thức trong template. Điểm tính từ trận đã finished; KDA từ ván đã được lưu, kể cả trận đang diễn ra; ghi đúng khác biệt này khi thuyết minh.

Vòng tròn: điểm → hiệu số ván → ván thắng; bằng cả ba thì đồng hạng. Loại trực tiếp: vô địch1, á quân2, thua bán kết đồng hạng3; không có trận tranh hạng ba. Mỗi đội đồng hạng nhận toàn bộ mức thưởng hạng đó, không tự chia tiền. Hạng không khai báo nhận0.

`finalize` cần mọi trận finished/bye, đủ thứ hạng, lý do khi đồng hạng và tổng thưởng không vượt pool. Tất cả kết quả/thưởng ghi một giao dịch, sau đó khóa giải. Nếu thiếu quỹ, BTC bổ sung quỹ kèm lý do trước khi chốt; không tự giảm mức thưởng đã công bố sau khi giải bắt đầu.

CSV xuất UTF-8 BOM và xử lý ký tự bắt đầu công thức để tên đội không bị Excel thực thi. Không đưa MSSV/tài khoản vào báo cáo công khai. In PDF dùng trang report và print CSS.

## Kiểm tra riêng

```bash
python -m pytest tests -q -k 'login or registration or signup or privacy or budget or finalization or csv'
```

Bàn giao: luồng tài khoản→đội→hồ sơ→duyệt và luồng kết quả→xếp hạng→thưởng→chốt. Giải thích được vì sao phải giữ snapshot roster và vì sao không lấy KDA để quyết định thắng.
