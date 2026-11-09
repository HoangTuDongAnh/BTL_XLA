"""Research glossary and methodology, grounded in the exported QA reports."""
import streamlit as st


def render_methods(root):
    definitions, workflow, limits, sources = st.tabs([
        'Dữ liệu & khái niệm', 'Phương pháp', 'Cách diễn giải', 'Tài liệu nghiên cứu'])
    with definitions, st.container(border=True):
        st.subheader('Ba chuỗi quan trắc, ba ý nghĩa khác nhau')
        st.markdown('''
**VIIRS — lượt phát hiện điểm nóng**  
Điểm nóng là vị trí vệ tinh ghi nhận tín hiệu nhiệt. Dashboard đếm lượt phát hiện;
những lượt ở gần nhau hoặc cùng vị trí có thể thuộc cùng một sự kiện.

**Cropland — đất trồng trọt**  
Điểm nóng được chồng phủ với lớp Cropland của ESA WorldCover 2021.
Đây là cách chọn điểm nóng trên đất nông nghiệp, **chưa đủ để xác nhận đốt rơm rạ**.
Lớp phủ năm 2021 cũng không phản ánh đầy đủ mọi thay đổi sử dụng đất đến năm 2025.

**PM2.5 — bụi mịn trong không khí gần mặt đất**  
Nồng độ được trình bày bằng µg/m³ từ dữ liệu quan trắc OpenAQ.
Công đoạn tiền xử lý dùng ngưỡng ít nhất 18 giờ hợp lệ để xét dữ liệu ngày của trạm.

**AOD — độ dày quang học aerosol**  
AOD 550 nm từ MODIS MAIAC mô tả mức suy giảm ánh sáng do aerosol trong cột khí quyển;
đây là đại lượng không có đơn vị, không phải nồng độ PM2.5 tại mặt đất.
Vì vậy, dashboard dùng trục riêng cho AOD và PM2.5.
''')
        st.subheader('Hiểu đúng dữ liệu thiếu')
        st.markdown('''
- **AOD gốc:** giá trị từ quan trắc vệ tinh sau kiểm tra dữ liệu. Phân tích chính sử dụng chuỗi này.
- **AOD sau điền/nội suy:** giữ quan trắc gốc và bổ sung một phần khoảng thiếu theo quy tắc của pipeline.
- **Độ phủ AOD:** tỷ lệ ô lưới có dữ liệu trên tổng số ô có tâm nằm trong ranh giới Hà Nội;
  không phải tỷ lệ ngày hợp lệ và cũng không phải số lượt truy hồi vệ tinh.
- **NoData:** không có quan trắc hợp lệ, không mang nghĩa AOD bằng 0.
- **Hai mùa nghiên cứu:** tháng 5–6 và tháng 10–11/2025. Tháng 7–9 nằm ngoài phạm vi nghiên cứu.
''')
    with workflow, st.container(border=True):
        st.subheader('Quy trình nghiên cứu')
        st.markdown('''
1. **Thu thập:** VIIRS FIRMS, MODIS MAIAC, OpenAQ, WorldCover và ranh giới GADM.
2. **Tiền xử lý:** chuẩn hóa không gian, thời gian; kiểm tra điểm nóng, AOD và dữ liệu trạm.
3. **Xử lý ảnh:** chồng phủ Cropland, raster mật độ điểm nóng 1 km, tổng hợp AOD theo tuần và nội suy có kiểm soát.
4. **Phân tích:** đối chiếu chuỗi ngày bằng Pearson, Spearman và độ trễ 0–3 ngày; đánh giá độ nhạy.
5. **Kiểm chứng:** lấy mẫu lại theo khối, dịch vòng chuỗi và kiểm tra nội suy bằng che khối pixel.
''')
        st.subheader('Tương quan và độ trễ')
        st.markdown('''
**Pearson r** đo mối liên hệ tuyến tính. **Spearman ρ** đo mối liên hệ đơn điệu dựa trên thứ hạng,
giúp đối chiếu kết quả khi quan hệ không tuyến tính hoặc có giá trị cực đoan.
Hai hệ số nằm trong khoảng −1 đến +1; dấu cho biết chiều liên hệ, độ lớn cho biết mức độ liên hệ tương ứng.

**Lag 0–3 ngày** so sánh các chuỗi ở những độ lệch thời gian khác nhau.
Đây không phải phép đo thời gian di chuyển của khói. Luôn đọc kèm **n_pairs** — số cặp ngày hợp lệ thực sự được dùng.

**p-value** đánh giá mức độ tương thích với giả thuyết không có liên hệ theo mô hình kiểm định;
không phải xác suất giả thuyết đúng. **FDR Benjamini–Hochberg** điều chỉnh cho nhiều phép thử.
Trong nghiên cứu này, họ kiểm định gồm các cặp biến × mùa × lag của phân tích chính,
điều chỉnh riêng cho Pearson và Spearman.
''')
        st.subheader('Ba cách kiểm chứng bổ sung')
        with st.expander('Block Bootstrap · khoảng tin cậy 95%', expanded=True):
            st.write('Lấy mẫu lại theo các khối cặp quan trắc để đánh giá bất định của hệ số. '
                     'Thiết lập đã xuất sử dụng 1.200 lần lặp, khối 7 hàng đã ghép. '
                     'Khoảng tin cậy chứa 0 cho thấy dấu tương quan chưa rõ ràng. '
                     'Ghép các ngày hợp lệ có thể nén khoảng thời gian bị thiếu, đặc biệt với AOD.')
        with st.expander('Circular Shift · kiểm tra dịch chuỗi'):
            st.write('Dịch vòng chuỗi theo lịch đầy đủ trong từng mùa, loại các dịch chuyển gần, rồi so sánh '
                     'với hệ số quan sát. shift_p_two_sided là p-value hai phía từ các phép dịch đã thử. '
                     'Các phép dịch không độc lập; đây là kiểm tra thăm dò, không phải bằng chứng nhân quả.')
        with st.expander('AOD block holdout · kiểm tra nội suy'):
            st.write('Che các khối không gian 8 × 8 pixel trong một ngày có dữ liệu, dùng ngày trước và ngày sau '
                     'để kiểm tra phương pháp nội suy, rồi so với baseline ngày trước. '
                     'Báo cáo đánh giá 6 ngày đáp ứng điều kiện quan trắc. '
                     'MAE đo sai số tuyệt đối trung bình, RMSE nhạy với sai số lớn, bias thể hiện xu hướng lệch. '
                     'MAE và RMSE thấp hơn là tốt hơn; bias gần 0 cho thấy ít lệch trung bình.')
    with limits, st.container(border=True):
        st.subheader('Kết quả cho phép nói điều gì?')
        st.markdown('''
**Một mối liên hệ quan sát được, không phải kết luận nguyên nhân.**  
Tương quan giữa lượt VIIRS trên Cropland và PM2.5 không xác nhận nguồn phát thải là đốt rơm rạ.
Khí tượng, các nguồn phát thải khác và sai khác thời gian quan trắc có thể ảnh hưởng kết quả.

**Đọc hệ số cùng số mẫu và độ bất định.**  
Không chọn kết luận chỉ từ hệ số lớn nhất. So sánh Pearson với Spearman, kiểm tra số cặp,
p-value đã điều chỉnh, khoảng tin cậy Bootstrap và Circular Shift.
Lag nổi bật được chọn sau khi xem kết quả; Bootstrap/Circular Shift chưa có điều chỉnh familywise
cho việc lựa chọn nhiều lag.

**Ngày AOD và ngày quan trắc mặt đất không hoàn toàn đồng nhất.**  
AOD dùng ngày UTC danh định trong tên sản phẩm NASA. VIIRS và PM2.5 dùng ngày địa phương;
không suy diễn rằng thời điểm của từng pixel AOD đã được chuyển sang UTC+7.

**Nội suy không tạo ra quan trắc vệ tinh mới.**  
Thử nghiệm che khối chỉ áp dụng nơi ngày mục tiêu và cả hai ngày lân cận có dữ liệu.
Nó không mô phỏng đầy đủ mây kéo dài, không phải kiểm chứng nội suy không gian,
và các pixel trong cùng khối có phụ thuộc không gian.

**PASS của QA nói về kiểm tra kỹ thuật.**  
PASS không chứng minh giả thuyết nghiên cứu. WARN cần được đọc cùng nội dung cảnh báo;
FAIL chỉ ra kiểm tra chưa đạt. Trang Kiểm chứng hiển thị trực tiếp trạng thái đã xuất.
''')
    with sources, st.container(border=True):
        st.subheader('Nguồn dữ liệu')
        st.markdown('''
| Nguồn | Vai trò trong nghiên cứu |
|---|---|
| NASA VIIRS FIRMS | Lượt phát hiện điểm nóng |
| MODIS MAIAC MCD19A2 | AOD 550 nm |
| OpenAQ | Nồng độ PM2.5 quan trắc |
| ESA WorldCover 2021 | Phân loại lớp phủ, xác định Cropland |
| GADM | Ranh giới vùng nghiên cứu và các tỉnh |
''')
        st.subheader('Báo cáo để đọc thêm')
        reports = [
            ('De9_Bao_cao_tong_hop_5_cong_doan.pdf', 'Báo cáo tổng hợp 5 công đoạn'),
            ('04_Correlation_Analysis/De9_Cong_doan_4_Bao_cao_tong_ket.pdf', 'Báo cáo phân tích tương quan'),
            ('05_Final_Evaluation/De9_Cong_doan_5_Bao_cao_tong_ket.pdf', 'Báo cáo kiểm chứng và đánh giá'),
        ]
        for relative, title in reports:
            try:
                data = (root / relative).read_bytes()
                st.download_button(title, data, file_name=(root / relative).name,
                                   mime='application/pdf', key='report_' + relative, icon=':material/download:')
            except OSError:
                st.caption(f'{title}: chưa có tệp để tải.')
        with st.expander('Căn cứ biên soạn phần giải thích'):
            st.write('Nội dung phương pháp được đối chiếu với các báo cáo QA đã xuất trong dự án:')
            st.markdown('''
- Công đoạn 2: `stage2_validation_summary.md` — quy tắc dữ liệu ngày, thời gian và WorldCover.
- Công đoạn 4: `aod_audit.json`, `correlation_audit.json` — độ phủ, ngày AOD và họ kiểm định FDR.
- Công đoạn 5: `robustness_audit.json`, `aod_block_audit.json` — thiết lập Bootstrap, Circular Shift và che khối.
''')
