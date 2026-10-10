# Đề 9 — OpenAQ PM2.5 Downloader (Công đoạn 1, Input 3)

Công cụ Python 3.10+ lấy dữ liệu PM2.5 từ 4 OpenAQ Location ID: `2161306`, `2161292`, `4946812`, `4946813`. Sử dụng OpenAQ API v3, **không** cần tải bằng nút CSV giới hạn trên Explorer.

## Thiết lập trên Windows (PowerShell)

1. Giải nén, mở PowerShell trong thư mục chứa `download_openaq.py`.
2. Cài thư viện: `py -m pip install -r requirements.txt`
3. Tạo API key ở <https://explore.openaq.org/account>.
4. Thiết lập biến môi trường **trong PowerShell hiện tại**:

   `$env:OPENAQ_API_KEY = "API_KEY_CUA_BAN"`

   Không đưa key vào script, không gửi cho ChatGPT, không commit vào Git.

5. Quét metadata và sensor PM2.5 trước (chưa tải số đo):

   `py download_openaq.py --mode scan`

6. Kiểm tra `OpenAQ_PM25/stations.csv`, `sensors.csv`, `issues.csv`. Nếu hợp lệ, tải hai mùa gặt:

   `py download_openaq.py --mode download`

   Tùy chọn lấy thêm giá trị trung bình ngày OpenAQ để đối chiếu:

   `py download_openaq.py --mode download --include-daily`

## Khoảng thời gian

- 2025-05-01 đến hết 2025-06-30
- 2025-10-01 đến hết 2025-11-30
- Truy vấn theo **UTC**; giữ lại trường `datetime_local` do OpenAQ trả về nếu có. Không tự coi ngày UTC là ngày Việt Nam. Giai đoạn chuẩn hóa sau này sẽ xử lý theo múi giờ Asia/Ho_Chi_Minh.

## Đầu ra

- `stations.csv`: metadata các Location ID.
- `sensors.csv`: PM2.5 sensor IDs được phát hiện.
- `May_Jun_2025/`, `Oct_Nov_2025/`: CSV số đo theo giờ, tách theo Location ID và Sensor ID.
- `manifest.csv`: số bản ghi, số ngày có quan trắc, trạng thái cho từng cặp trạm-cảm biến-mùa.
- `coverage_report.csv`: ngày theo UTC có bao nhiêu bản ghi theo giờ; 0 nghĩa là không nhận được dữ liệu.
- `issues.csv`: các lỗi tìm sensor, xác thực hoặc tải dữ liệu. Trạm không có PM2.5 được ghi vào đây.

## Lưu ý

- Một Location có thể có nhiều cảm biến PM2.5; script lưu riêng để tránh trộn nguồn.
- Số ngày có dữ liệu khác với số ngày **đủ 24 giờ**. Không tự nội suy số liệu thiếu.
- `value` là phép đo theo API, chưa tự động loại ngoại lệ, giá trị âm, hay phân tích chất lượng.
- Endpoint `/hours` trả về dữ liệu trung bình giờ tính sẵn; `--include-daily` lấy `/days` để đối chiếu, không thay thế xử lý trung bình ngày theo giờ Việt Nam.
- Không có key trong file đầu ra, nhưng đường dẫn file và metadata trạm được lưu.
- Đây là mã nguồn đã kiểm tra cú pháp và luồng phân tích với dữ liệu giả lập, **chưa thử kết nối thật với khóa API của bạn**. Khi gặp thay đổi schema cần cung cấp thông báo lỗi (không gửi API key).
