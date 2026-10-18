# Phùng Đức Duy Khang — lịch, nhánh và kết quả

MSSV: 50.01.104.071. Source đã tích hợp: `app/tournament.py`, `app/matches.py`. Tín sở hữu `event.html`/`match.html`; khi thay dữ liệu context hoặc tên form, Khang và Tín cập nhật cùng một nhánh công việc.

## Cách thực hiện

1. Đăng nhập `btc`, mở Campus Cup, tạo lịch ở ngày chưa trùng Student League, chọn trọng tài. Bắt đầu giải rồi mở trận đầu và bấm Bắt đầu trận đấu.
2. Đọc `round_robin`: giữ một đội cố định, xoay phần còn lại, thêm None nếu lẻ. Mỗi cặp gặp đúng một lần; một đội không gặp hai đối thủ cùng lượt.
3. Đọc `create_schedule`: kiểm tra hồ sơ → xáo trộn → tạo vòng/trận → nối next_id/next_slot → xử lý miễn vòng. Với 3 đội, có 1 trận thật và 1 miễn vòng ở vòng đầu; không có trận None–None được coi là miễn vòng.
4. Nhập ván: chọn thắng, thời lượng giây, 5 người mỗi đội, tướng và K/D/A. Chọn dự bị phải bỏ một người chính. Vàng có thể để trống. Dữ liệu thử 0/0/0 được chấp nhận khi hai phía khớp; để trình diễn thật nên nhập dữ liệu nhất quán có ý nghĩa.
5. Đọc `save_game`: xác thực người ghi → version → trạng thái → roster → KDA → chuỗi thắng → cập nhật game/stats/match/nhánh → audit. Không viết một endpoint khác cập nhật riêng tỷ số; tỷ số luôn tính từ games.
6. Thử sửa ván đã lưu khi vòng sau chưa bắt đầu: đổi thắng có thể đưa trận về live và bỏ đội khỏi ô kế tiếp. Khi vòng sau đã bắt đầu, phải chặn sửa nguồn.
7. Khi sửa thuật toán, giữ transaction ở route và service nhận db; không dùng dữ liệu global để lưu nhánh. Tất cả trạng thái phải tồn tại trong SQLite để khởi động lại không mất kết quả.

## Hợp đồng

- `create_schedule(db,user,eid,best_of,start,referee)`: start UTC dạng phút, Bo 3/5, tối đa32 đội, 2 h/trận; lỗi ném BusinessError, không có lịch dở dang.
- `save_game(...,rows,exception)`: xem chính xác cấu trúc rows trong tài liệu kiến trúc. `version` lấy từ trang đang mở, không tự tăng ở trình duyệt. Hàm trả game ID; không trả tỷ số nhập tay.
- Thắng Bo3 cần2, Bo5 cần3. Phải đủ 10 người, không ván dư sau khi đã thắng. K/D chênh lệch chỉ BTC xác nhận với lý do ≥5 ký tự; trọng tài không được bỏ qua.
- Kiểm tra trùng lịch so theo khoảng `[starts,ends)`, đội/trọng tài có thể hoạt động nhiều giải nhưng không cùng giờ. Các đội chưa biết ở vòng sau được kiểm tra lại khi chuyển người thắng.

## Kiểm tra riêng

```bash
python -m pytest tests -q -k 'round_robin or knockout or schedule or result or stale or source or referee'
```

Sản phẩm bảo vệ: demo3 đội có miễn vòng, Bo5, một lỗi form cũ, một lỗi K/D, sửa nguồn trước/sau khi vòng sau bắt đầu. Giải thích được tại sao không suy ra thắng từ Kills.
