"""Stage 5 research demo. Launch: python -m streamlit run app/streamlit_app.py"""
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'05_Final_Evaluation'
S3=ROOT/'03_Image_Processing'
st.set_page_config(page_title='De 9 | Air Pollution Analysis',page_icon='🌾',layout='wide')

@st.cache_data(show_spinner=False)
def read_csv(path):return pd.read_csv(path)

def load(rel):
    path=OUT/rel
    if not path.is_file():st.error(f'Missing {path}. Run run_stage5.py first.');st.stop()
    return read_csv(path)

def export(df,filename):
    st.download_button('Tải CSV',df.to_csv(index=False).encode('utf-8-sig'),file_name=filename,mime='text/csv')

st.sidebar.title('Đề 9 · ĐBSH')
page=st.sidebar.radio('Trang', ['Tổng quan','Điểm nóng VIIRS','AOD','Tương quan và độ trễ','Kiểm chứng và QA'])
st.sidebar.caption('VIIRS điểm nóng trên Cropland ≠ bằng chứng xác định đốt rơm rạ. Tương quan ≠ nhân quả.')

daily=load('03_Final_Dataset/final_daily_dataset.csv')
lag=load('03_Final_Dataset/final_lag_results.csv')
season=st.sidebar.selectbox('Mùa nghiên cứu',['Tất cả','May_Jun_2025','Oct_Nov_2025'])
sub=daily if season=='Tất cả' else daily[daily.period==season]

if page=='Tổng quan':
    st.title('Liên hệ VIIRS · AOD · PM2.5 tại Hà Nội')
    a,b,c,d=st.columns(4)
    a.metric('Ngày nghiên cứu',len(sub));b.metric('Điểm nóng Cropland',int(sub.fire_rrd.sum()))
    c.metric('Ngày có PM2.5',int(sub.pm25_hanoi.notna().sum()));d.metric('Ngày có AOD gốc',int(sub.aod_original_hanoi.notna().sum()))
    chart=sub[['date','fire_rrd','pm25_hanoi','aod_original_hanoi']].set_index('date')
    st.line_chart(chart[['pm25_hanoi','aod_original_hanoi']]);st.line_chart(chart[['fire_rrd']]);export(sub,'daily_filtered.csv')
    st.info('Chuỗi được tính từ hai mùa riêng; khoảng trống tháng 7–9 không phải dữ liệu bị thiếu.')

elif page=='Điểm nóng VIIRS':
    st.title('VIIRS và đất nông nghiệp')
    st.write('Đây là các lượt phát hiện trên lớp Cropland của WorldCover 2021, không phải xác nhận đốt rơm rạ năm 2025.')
    st.bar_chart(sub.set_index('date')[['fire_rrd','fire_hanoi','fire_surrounding']]);export(sub[['period','date','fire_rrd','fire_hanoi','fire_surrounding']],'fire_daily.csv')
    fire=load('03_Final_Dataset/final_fire_statistics.csv');fire=fire if season=='Tất cả' else fire[fire.period==season]
    provinces=sorted(fire.province.dropna().unique().tolist());province=st.selectbox('Tỉnh', ['Tất cả',*provinces])
    if province!='Tất cả':fire=fire[fire.province==province]
    st.dataframe(fire,use_container_width=True)
    # Reference maps from Stage3 (no fabricated map data).
    example=S3/'06_Maps'/'fire_density_example.png'
    if example.is_file():st.image(str(example),caption='Bản đồ mật độ minh họa từ raster Công đoạn 3 (ví dụ một tuần, không đại diện mọi tuần)')

elif page=='AOD':
    st.title('AOD · dữ liệu gốc và nội suy')
    a,b=st.columns(2)
    a.metric('Ngày có AOD gốc',int(sub.aod_original_hanoi.notna().sum()))
    b.metric('Ngày có AOD nội suy/điền',int(sub.aod_filled_hanoi.notna().sum()))
    chart=sub.set_index('date')[['aod_original_hanoi','aod_filled_hanoi']];st.line_chart(chart)
    st.area_chart(sub.set_index('date')[['aod_coverage_pct']]);export(sub,'aod_daily.csv')
    metrics=load('02_AOD_Evaluation/aod_block_holdout_summary.csv')
    st.subheader('Kiểm tra AOD bằng khối pixel bị che');st.dataframe(metrics,use_container_width=True)
    st.warning('Không dùng AOD nội suy làm dữ liệu chính để kết luận tương quan. Bài test che khối có điều kiện quan trắc thuận lợi hơn khoảng thiếu do mây kéo dài.')

elif page=='Tương quan và độ trễ':
    st.title('Pearson · Spearman · Lag 0–3 ngày')
    names=sorted(lag.comparison.unique());name=st.selectbox('Cặp biến',names)
    series=lag[lag.comparison==name]
    selected_seasons=['May_Jun_2025','Oct_Nov_2025'] if season=='Tất cả' else [season]
    series=series[series.season.isin(selected_seasons)]
    method=st.radio('Chỉ số',['pearson_r','spearman_rho'],horizontal=True)
    pivot=series.pivot(index='lag_days',columns='season',values=method)
    st.line_chart(pivot);st.dataframe(series,use_container_width=True);export(series,'correlation_selected.csv')
    st.caption('p-value thông thường chưa điều chỉnh cho tự tương quan. Kết quả BH của Công đoạn 4 không phải chứng minh nhân quả.')

else:
    st.title('Đánh giá độ tin cậy và QA')
    bs=load('01_Robustness/bootstrap_ci.csv');sh=load('01_Robustness/circular_shift_tests.csv')
    if season!='Tất cả':bs=bs[bs.season==season];sh=sh[sh.season==season]
    st.subheader('Block Bootstrap – khoảng tin cậy 95%');st.dataframe(bs,use_container_width=True);export(bs,'bootstrap_ci.csv')
    st.subheader('Circular shift – kiểm tra dịch chuỗi trong từng mùa');st.dataframe(sh,use_container_width=True)
    st.caption('Bootstrap trên các cặp ngày đã ghép có thể nén những ngày AOD bị thiếu; không xem CI này là phép kiểm chứng tuyệt đối.')
    v=OUT/'05_Quality_Reports'/'stage5_validation.json'
    if v.is_file():
        import json
        obj=json.loads(v.read_text(encoding='utf-8'))
        st.subheader(f"Validation: {obj.get('status')}");st.json(obj)
