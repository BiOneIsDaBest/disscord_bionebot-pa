# disscord_bionebot-pa

# BiOneBot - Hệ Thống Chấm Công Tự Động Cho HVQG

BiOneBot là một hệ thống chấm công tự động được thiết kế dành riêng cho các đơn vị đào tạo trong môi trường Roleplay ( server GTA5VN - S1 Los Santos ) (như học viện cảnh sát, bảo an, nhân sự...). Bot được xây dựng bằng Python và tích hợp với Discord để theo dõi giờ làm việc, thống kê, và báo cáo minh bạch, rõ ràng.

---

## 📌 Tính Năng Nổi Bật

- `pa!onduty` / `pa!offduty`: Bắt đầu và kết thúc phiên làm việc (có đính kèm ảnh minh chứng).
- `pa!update`: Cập nhật biển số xe trong ca làm việc.
- `pa!myinfo`: Xem chi tiết thời gian làm việc cá nhân, tuần/tháng và theo từng ngày.
- `pa!checktime`: Kiểm tra thời gian làm việc của người khác hoặc cả phòng ban.
- `pa!checkduty`: Xem ai đang làm việc (đang ONDUTY).
- `teachpanel`: Giao diện ghi nhận tiết dạy cho giảng viên/trợ giảng, báo cáo lương kèm thống kê.
- Thông báo tự động nhắc nhở người ONDUTY lúc 23:00 và 23:45.
- Nhắc nhở người vượt quá 4 tiếng làm việc (đủ chỉ tiêu ngày).
- Hệ thống ghi nhận thời gian bằng ảnh, thời gian và loại công việc.

---

## 🛠️ Cài Đặt

### 1. Clone Project
```bash
git clone https://github.com/your-username/bionebot.git
cd bionebot
```

### 2. Cài Thư Viện
```bash
pip install -r requirements.txt
```

### 3. Cấu Hình `.env`

### 4. Chạy Bot
```bash
python main.py
```

> ⚠ Bot sử dụng file SQLite (`data.sqlite`) để lưu thông tin. Không xóa file này trừ khi muốn reset toàn bộ dữ liệu.

---

## 📄 Bản Quyền

**Bản quyền thuộc BiOneIsDaBest**  
Liên hệ: [Discord: BiOneIsDaBest](https://discord.com/users/1146990393167200276)

> Nếu bạn **mượn để sử dụng hoặc test**, **vui lòng ghi rõ nguồn** như sau:

```
Bot gốc được phát triển bởi BiOneIsDaBest - discord.com/users/1146990393167200276
```

---

## ❤️ Đóng Góp

Dự án vẫn đang được phát triển. Nếu bạn muốn đóng góp tính năng hoặc báo lỗi, cứ thoải mái mở pull request hoặc gửi phản hồi qua Discord.
