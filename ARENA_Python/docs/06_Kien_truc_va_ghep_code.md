# Kiến trúc và quy ước tích hợp

## Một ứng dụng, một database

Trình duyệt gửi biểu mẫu đến Flask. Blueprint xác thực, chuyển dữ liệu đầu vào sang kiểu phù hợp, kiểm tra quyền và gọi service trong giao dịch. Service cập nhật SQLite; template Jinja hiển thị kết quả. CSS/JS dùng chung, không có bước build frontend và không cần Node.js để chạy ứng dụng.

| Lớp | File | Hợp đồng |
|---|---|---|
| Khởi tạo | `app/__init__.py`, `run.py` | `create_app(config=None)` trả Flask app; cấu hình `DATABASE`, `SECRET_KEY` |
| Dữ liệu | `app/db.py`, `schema.sql` | `get_db()` trả connection theo request; `query(sql,args,one)` trả Row/danh sách Row |
| Quyền/kiểu | `app/common.py` | `permission`, `student`, `captain`, `integer`, `require`, `BusinessError` |
| Đăng nhập | `app/auth.py` | `g.user` là Row người dùng hoạt động hoặc None; session chỉ giữ uid và CSRF |
| Đội/hồ sơ | `app/team.py` | `submit_entry(db,user,eid,tid,starters,reserves)` trả entry ID |
| Lịch | `app/tournament.py` | `create_schedule(db,user,eid,best_of,start,referee)` tạo lịch, không tự commit |
| Kết quả | `app/matches.py` | `save_game(db,user,mid,version,number,winner,duration,rows,exception='')` trả game ID |
| Báo cáo | `app/reports.py` | `standings(eid)`, `kda(eid)`, `finalize(db,user,eid,reason)` |
| Quản trị | `app/admin.py` | Phân quyền, danh mục, nhật ký, thông báo |
| Hiển thị | `app/templates/`, `app/static/` | Jinja dùng `url_for`; JS tăng trải nghiệm; máy chủ vẫn kiểm tra nghiệp vụ |

`rows` của `save_game` là danh sách đúng 10 dict, mỗi dict có `student_id`, `team_id`, `hero_id`, `kills`, `deaths`, `assists`, `gold` (None hoặc số nguyên). Mỗi đội đúng 5 tuyển thủ, thuộc danh sách đã duyệt. Không lấy tổng Kills làm căn cứ quyết định đội thắng: BTC/trọng tài chọn thắng theo kết quả trận thực tế.

## Quy ước bắt buộc khi sửa

1. Route nhận dữ liệu không tin cậy: kiểm tra quyền, ID, kiểu, giới hạn. Không dùng ID đội từ form thay kiểm tra đội trưởng.
2. Mọi nhóm ghi liên quan dùng `with transaction() as db:`. Service không gọi commit, không mở giao dịch lồng nhau. `BEGIN IMMEDIATE` và chỉ mục UNIQUE phối hợp chống ghi đồng thời.
3. Không đổi tên trường form, endpoint, tham số service hoặc cột DB mà không cập nhật tất cả chỗ dùng và kiểm thử.
4. SQL dùng tham số `?`. Đoạn ghép cột `team_a`/`team_b` chỉ lấy từ `next_slot` đã có CHECK trong DB; không nhận tên cột trực tiếp từ form.
5. Mọi POST có `csrf_field()`. GET không thay đổi dữ liệu. `g.user` luôn được tải lại để tài khoản bị khóa mất quyền ở request kế tiếp.
6. Ngày giờ lưu UTC dạng `YYYY-MM-DDTHH:MM`. Biểu mẫu và màn hình là giờ Việt Nam. Dùng `local_to_utc`, `localinput`, `timevn`; không cộng 7 giờ thủ công.
7. Tiền dùng số nguyên VND, không float. KDA `(tổng K+tổng A)/max(1,tổng D)`. Điểm vòng tròn: thắng trận 3, thua 0; xét tiếp hiệu số ván và số ván thắng; bằng cả ba thì đồng hạng.
8. Trận Bo3 thắng 2 ván, Bo5 thắng 3. Không có ván sau khi đã đủ số thắng. Sửa trận nguồn bị chặn khi trận kế tiếp đã bắt đầu. `version` phát hiện form cũ và trả 400, không tự ghi đè.
9. Lịch mặc định ngẫu nhiên, tuần tự 2 giờ/trận. Đây là thời lượng dự kiến để kiểm tra trùng lịch, không phải đồng hồ tự điều khiển trận. BTC bấm bắt đầu chủ động.
10. Trang công khai không hiển thị MSSV, họ tên thật hoặc Ingame ID định danh. Danh sách có IGN và tên đội. Không ghi mật khẩu vào nhật ký.

## Trạng thái

Giải: `draft → open → locked → live → finished`. Chỉ `finalize` được chốt `finished`. Không có thao tác mở lại giải đã chốt.

Hồ sơ: gửi `pending`, BTC duyệt `approved` hoặc `rejected`; đội trưởng có thể `withdrawn` trước khi xếp lịch. Chỉ rejected/withdrawn được nộp lại khi giải còn mở. Lịch chỉ tạo khi không còn pending.

Trận: `scheduled → live → finished`; `bye` cho suất miễn vòng, không có ván hoặc KDA. Sửa ván đã kết thúc có thể đưa trận về live nếu chưa đủ thắng, đồng thời xóa suất đội thắng tạm ở trận kế tiếp.

## Quyền ứng dụng

| Hành động | Admin | BTC | Trọng tài | Sinh viên | Khách |
|---|---|---|---|---|---|
| Xem lịch/báo cáo công khai | Có | Có | Có | Có | Có |
| Quản trị tài khoản/danh mục | Có | Không | Không | Không | Không |
| Tạo giải, duyệt hồ sơ, lịch, thưởng | Không | Có | Không | Không | Không |
| Kết quả | Không | Tất cả trận | Trận được phân công | Không | Không |
| Ngoại lệ K/D | Không | Có lý do | Không | Không | Không |
| Đội/đăng ký | Không | Không | Không | Theo quyền thành viên/đội trưởng | Không |
| Nhật ký | Có | Có | Không | Không | Không |

## Ghép công việc của 5 người

Bộ mã giao đã tích hợp. Khi tiếp tục phát triển: Lộc tạo nhánh chính; mỗi người tạo nhánh riêng từ cùng phiên bản. Cùng dùng Python 3.11 và requirements. Trân/Khang sửa service; Tín sở hữu template và CSS/JS; những thay đổi template của backend cần phối hợp với Tín. Nghi chạy kiểm thử và kịch bản demo; Lộc review và merge lần lượt.

Không gửi database, `.venv`, `instance/secret.key`, cache, tài khoản thật hoặc log chứa dữ liệu thật qua Git. Không ghi đè toàn bộ thư mục của người khác. Trước merge chạy `python -m pytest tests -q`; sau merge Lộc chạy lại. Chỉ sửa schema bằng một thay đổi phối hợp; `CREATE TABLE IF NOT EXISTS` không tự nâng cấp database cũ. Với bản nâng cấp schema, phải sao lưu và viết migration riêng trước khi chạy trên dữ liệu đang dùng.

HTTP: 400 là lỗi biểu mẫu/nghiệp vụ hoặc CSRF; 401 chưa đăng nhập; 403 không quyền; 404 không tồn tại; 409 vi phạm UNIQUE/FK; 429 bị giới hạn đăng nhập; 500 lỗi bất ngờ. Lỗi nghiệp vụ rollback toàn bộ thay đổi trong giao dịch.
