"""Interpretation of the existing final research outputs; no new analysis pipeline."""
import streamlit as st


def render_conclusions(load, season, seasons):
    st.caption('Tổng kết cố định cho cả hai mùa năm 2025. Bộ lọc mùa chỉ áp dụng cho bảng bằng chứng bên dưới.')
    with st.container(border=True):
        st.subheader('Điều rút ra từ nghiên cứu')
        st.markdown('**Điểm nóng trên đất nông nghiệp và PM2.5 Hà Nội có mối liên hệ '
                    'thay đổi theo mùa, nổi bật hơn trong tháng 10–11/2025.** '
                    'Kết quả gợi ý nên theo dõi đồng thời hai chuỗi trong mùa này, '
                    'nhưng chưa xác định được phần PM2.5 do đốt nông nghiệp gây ra.')

    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader('01 · Tín hiệu khác nhau giữa hai mùa')
        st.markdown('**Tháng 10–11:** ở lag 2 ngày, Pearson r = **0,619**, '
                    'Spearman ρ = **0,440**, với **58 cặp ngày**. '
                    'p sau FDR lần lượt khoảng 0,00000691 và 0,00471. '
                    'Đây là lag có |Pearson r| lớn nhất trong bốn lag đã khảo sát của cặp VIIRS–PM2.5 toàn vùng.')
        st.markdown('**Tháng 5–6:** Pearson r chỉ từ **−0,114 đến −0,069** ở lag 0–3; '
                    'các khoảng tin cậy Bootstrap đều chứa 0. '
                    'Chưa có bằng chứng rõ về liên hệ trong cửa sổ này; không đồng nghĩa với việc không có tác động.')
        st.caption('Ý nghĩa: cần phân tích theo mùa; một hệ số gộp có thể che khuất sự khác biệt giữa hai giai đoạn.')
    with right, st.container(border=True):
        st.subheader('02 · Kiểm chứng ủng hộ, nhưng còn bất định')
        st.markdown('Với tháng 10–11, lag 2: khoảng tin cậy Bootstrap 95% của Pearson '
                    'là **[0,102; 0,709]**; Circular Shift có p ≈ **0,0204** '
                    'trên 48 phép dịch. Hai kiểm tra bổ sung ủng hộ tín hiệu cùng chiều đã quan sát.')
        st.markdown('Khoảng tin cậy còn rộng. Lag được chọn sau khi xem kết quả; '
                    'Bootstrap và Circular Shift chưa điều chỉnh familywise cho việc chọn nhiều lag. '
                    '**Không diễn giải lag 2 ngày thành thời gian khói di chuyển tới Hà Nội.**')
        st.caption('Ý nghĩa: đây là tín hiệu đáng kiểm tra tiếp, chưa phải mô hình dự báo hay bằng chứng nhân quả.')

    with st.container(border=True):
        st.subheader('03 · AOD bổ sung bối cảnh, chưa khép kín được mối liên hệ')
        st.write('Chỉ 52/122 ngày có AOD gốc, trong khi PM2.5 có 115/122 ngày. '
                 'Các liên hệ liên quan đến AOD thay đổi theo mùa và lag; một số khoảng Bootstrap '
                 'không chứa 0 nhưng kiểm tra dịch chuỗi không đồng thuận ở mức 0,05. '
                 'Chưa có bằng chứng nhất quán để khẳng định chuỗi điểm nóng → AOD → PM2.5.')
        st.write('Trong thử nghiệm che khối trên 6 ngày, 151 pixel: nội suy đối xứng có '
                 'MAE = 0,0944 và RMSE = 0,1342, cao hơn baseline ngày trước '
                 '(MAE = 0,0559; RMSE = 0,1016). Bias gần 0 hơn không đồng nghĩa với sai số nhỏ hơn. '
                 'Không xem nội suy là cải thiện độ chính xác trong thử nghiệm này; '
                 'phân tích chính tiếp tục dùng AOD gốc.')

    st.subheader('Ý nghĩa thực tiễn và hướng tiếp theo')
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown('**Có thể sử dụng kết quả để**')
        st.markdown('- Ưu tiên kiểm tra các đợt điểm nóng và PM2.5 cùng tăng trong tháng 10–11.\n'
                    '- Kết hợp vệ tinh với quan trắc mặt đất để chọn thời điểm, khu vực cần khảo sát.\n'
                    '- Xác định khoảng thiếu dữ liệu và thiết kế nghiên cứu kiểm chứng tiếp theo.')
    with right, st.container(border=True):
        st.markdown('**Để đi đến kết luận về nguồn gây ô nhiễm**')
        st.markdown('- Bổ sung gió, mưa, độ ẩm và chiều cao lớp biên để kiểm soát ảnh hưởng khí tượng.\n'
                    '- Đối chiếu thực địa/lịch mùa vụ để xác nhận hoạt động đốt; xem xét các nguồn phát thải khác.\n'
                    '- Mở rộng nhiều năm, kiểm định trên dữ liệu độc lập và phân tích vận chuyển khối khí.')
    st.caption('Giới hạn phạm vi: hai mùa năm 2025; Cropland từ WorldCover 2021; '
               'AOD theo ngày UTC danh nghĩa khác với ngày UTC+7 của VIIRS/PM2.5. '
               'Lượt điểm nóng không phải số vụ đốt hay diện tích bị đốt. '
               'Chưa thể định lượng tỷ lệ đóng góp của đốt rơm rạ vào PM2.5 Hà Nội.')

    with st.expander('Đối chiếu số liệu và nguồn kết luận'):
        st.caption('Bảng VIIRS trên Cropland toàn vùng – PM2.5 · ' + seasons[season])
        lag = load('03_Final_Dataset/final_lag_results.csv',
                   ['comparison', 'season', 'lag_days', 'n_pairs', 'pearson_r', 'spearman_rho',
                    'pearson_p_fdr_bh', 'spearman_p_fdr_bh'])
        selected = ['May_Jun_2025', 'Oct_Nov_2025'] if season == 'Tất cả' else [season]
        evidence = lag[(lag.comparison == 'fire_pm25') & lag.season.isin(selected)]
        st.dataframe(evidence[['season', 'lag_days', 'n_pairs', 'pearson_r', 'spearman_rho',
                               'pearson_p_fdr_bh', 'spearman_p_fdr_bh']], hide_index=True, width='stretch')
        st.markdown('Nguồn: các kết quả đã xuất tại **05_Final_Evaluation** — '
                    '`final_lag_results.csv`, `final_quality_summary.json`, `bootstrap_ci.csv`, '
                    '`circular_shift_tests.csv`, `lag_stability.csv` và `aod_block_holdout_summary.csv`. '
                    'Xem bảng kiểm chứng ở tab **Kiểm chứng và QA**; tải báo cáo tổng kết '
                    'ở **Khái niệm & phương pháp → Tài liệu nghiên cứu**.')
