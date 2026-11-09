"""Read-only research dashboard. Run: python -m streamlit run app/streamlit_app.py."""
from html import escape
from functools import partial
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '05_Final_Evaluation'
SEASONS = {'Tất cả': 'Hai mùa · 2025', 'May_Jun_2025': 'Tháng 5–6/2025',
           'Oct_Nov_2025': 'Tháng 10–11/2025', 'all': 'Gộp hai mùa'}
PAIRS = {'fire_pm25': 'VIIRS – PM2.5', 'fire_aod': 'VIIRS – AOD gốc',
         'aod_pm25': 'AOD gốc – PM2.5', 'fire_pm25_hanoi': 'VIIRS Hà Nội – PM2.5',
         'fire_pm25_surrounding': 'VIIRS lân cận – PM2.5'}
LABELS = {'fire_rrd': 'Cropland · toàn vùng', 'fire_hanoi': 'Cropland · Hà Nội',
          'fire_surrounding': 'Cropland · lân cận', 'pm25_hanoi': 'PM2.5 Hà Nội',
          'aod_original_hanoi': 'AOD gốc', 'aod_filled_hanoi': 'AOD sau điền/nội suy',
          'aod_coverage_pct': 'Độ phủ AOD'}
NAVY, TEAL, ORANGE = '#17324d', '#087f8c', '#df7334'
st.set_page_config(page_title='Điểm nóng nông nghiệp & PM2.5 Hà Nội', layout='wide')
st.markdown('''<style>
[data-testid="stMainBlockContainer"] {max-width:1500px;padding-top:4rem;}
[data-testid="stSidebar"] {border-right:1px solid #dce5ec;}
[data-testid="stMetric"] {background:white;border:1px solid #dce5ec;
 border-radius:8px;padding:16px;min-height:115px;}
[data-testid="stMetricLabel"] {min-height:40px;align-items:flex-start;}
[data-testid="stMetricLabel"] p {white-space:normal;overflow:visible;text-overflow:clip;line-height:1.4;}
[data-testid="stMetricValue"] {color:#17324d;font-variant-numeric:tabular-nums;}
.research-header {background:#fff;border:1px solid #d7e2ea;border-radius:10px;padding:24px;margin:0 0 20px;}
.research-purpose {margin-top:16px;padding:12px 16px;border-left:3px solid #087f8c;background:#f0f7f8;color:#40576b;font-size:14px;line-height:1.6;}
[class*="st-key-chart_header_"] {min-height:58px;}
.research-purpose strong {color:#17324d;}
[class*="st-key-chart_panel_"], .st-key-map_panel {background:#fff;border-color:#d7e2ea;border-radius:10px;}
[class*="st-key-chart_panel_"] .chart-heading, .st-key-map_panel .chart-heading {font-size:18px;font-weight:650;color:#17324d;line-height:1.4;margin:0;}
.research-header h1 {color:#17324d;font-size:clamp(1.7rem,2.4vw,2.4rem);font-weight:650;line-height:1.3;margin:0 0 12px;}
.research-header p {color:#526578;max-width:950px;margin:0;line-height:1.7;font-size:16px;}
.research-brand {font-size:21px;font-weight:650;color:#17324d;line-height:1.35;margin:0 0 8px;}
.research-region {font-size:13px;color:#607487;margin:0 0 28px;line-height:1.6;}
.st-key-research_nav {gap:6px;}
.st-key-research_nav button {justify-content:flex-start;text-align:left;min-height:46px;
 border-radius:6px;padding:10px 14px;box-shadow:none;}
.st-key-research_nav button > div {width:100%;justify-content:flex-start;}
.st-key-research_nav button > div > span {justify-content:flex-start;}
.st-key-research_nav button[kind="secondary"] {background:transparent;border-color:transparent;color:#40576b;}
.st-key-research_nav button[kind="secondary"]:hover {background:#e2ebef;color:#17324d;}
.st-key-research_nav button[kind="primary"] {background:#dcecee;color:#115963;border:1px solid #b8d7da;}
.st-key-research_nav button:focus-visible {outline:2px solid #087f8c;outline-offset:2px;}
@media(max-width:700px) {[data-testid="stMainBlockContainer"] {padding-top:4rem;} .research-header {padding-bottom:20px;}}
</style>''', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def read_csv(path, modified):
    return pd.read_csv(path)


def load(relative, columns=(), root=OUT):
    """A missing optional source only disables its own section."""
    path = root / relative
    try:
        frame = read_csv(str(path), path.stat().st_mtime_ns)
        missing = set(columns) - set(frame.columns)
        if missing:
            raise ValueError('Thiếu cột: ' + ', '.join(sorted(missing)))
        return frame
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        st.warning(f'Không thể hiển thị nguồn {path.relative_to(ROOT)}: {exc}')
        return pd.DataFrame(columns=columns)


def export(frame, name):
    st.download_button('Tải CSV', frame.to_csv(index=False).encode('utf-8-sig'),
                       file_name=name, mime='text/csv', key=name, disabled=frame.empty)


def table(frame):
    st.dataframe(frame, width='stretch', hide_index=True)


def filtered(frame, season, column='period'):
    return frame if season == 'Tất cả' else frame[frame[column] == season]


PAGE_PURPOSE = {
    'Kết luận & ý nghĩa': 'Chốt các phát hiện chính, mức độ chắc chắn và giá trị sử dụng của nghiên cứu; phân biệt điều đã quan sát được với điều cần kiểm chứng thêm.',
    'Điểm nóng nông nghiệp và PM2.5 Hà Nội': 'Nắm quy mô dữ liệu và quan sát thời điểm điểm nóng, PM2.5 cùng tăng hoặc giảm trước khi xem phân tích chi tiết.',
    'Điểm nóng & lớp phủ đất': 'Xác định điểm nóng tập trung ở đâu, vào tuần nào và bao nhiêu lượt nằm trên đất trồng trọt. Dùng bộ lọc để đi từ toàn vùng đến từng tỉnh.',
    'AOD · quan trắc & độ phủ': 'Đánh giá mức đầy đủ của quan trắc vệ tinh và phần dữ liệu được bổ sung bằng nội suy, để biết kết quả AOD có thể được diễn giải đến đâu.',
    'Tương quan và độ trễ': 'Kiểm tra chiều và mức độ liên hệ giữa các biến khi lệch nhau 0–3 ngày. Đọc hệ số cùng số cặp ngày, p-value và FDR.',
    'Kiểm chứng & chất lượng dữ liệu': 'Xem kết quả có ổn định qua các phép kiểm chứng hay không và nhận diện các cảnh báo cần cân nhắc trước khi kết luận.',
    'Khái niệm & phương pháp': 'Tra cứu ý nghĩa các biến, cách phân tích và giới hạn nghiên cứu. Bắt đầu từ khái niệm, sau đó xem phương pháp hoặc tải báo cáo gốc.',
}


def hero(title, description):
    purpose = PAGE_PURPOSE.get(title, '')
    guide = f'<div class="research-purpose"><strong>Mục đích.</strong> {escape(purpose)}</div>' if purpose else ''
    st.markdown(f'<header class="research-header"><h1>{escape(title)}</h1>'
                f'<p>{escape(description)}</p>{guide}</header>', unsafe_allow_html=True)


def kpis(items):
    for col, (label, value, help_text) in zip(st.columns(len(items)), items):
        col.metric(label, value, help=help_text)


def number(value):
    return f'{int(value):,}'.replace(',', '.')


def styled_chart(chart):
    return (chart.configure(background='#ffffff').configure_axis(labelColor='#526578', titleColor=NAVY,
                                 gridColor='#e5edf3', labelFontSize=12)
            .configure_legend(title=None, orient='bottom', labelLimit=300)
            .configure_view(strokeWidth=0))


@st.dialog('Chi tiết biểu đồ', width='large')
def chart_details(chart, title, data, explanation, scope, source):
    st.subheader(title)
    st.caption(scope)
    st.altair_chart(styled_chart(chart.properties(height=420)), width='stretch')
    st.markdown('**Cách đọc biểu đồ**')
    st.write(explanation)
    st.caption(f'Nguồn: {source}')
    with st.expander('Dữ liệu của biểu đồ', expanded=True):
        table(data)
        st.download_button('Tải dữ liệu biểu đồ', data.to_csv(index=False).encode('utf-8-sig'),
                           file_name='chart_data.csv', mime='text/csv', key='chart_detail_download')


def show_chart(chart, title, data, explanation, scope, source):
    with st.container(border=True, key='chart_panel_' + title):
        with st.container(horizontal=True, wrap=False, vertical_alignment='center', gap='small', key='chart_header_' + title):
            st.markdown(f'<h3 class="chart-heading">{escape(title)}</h3>', unsafe_allow_html=True, width='stretch')
            opened = st.button('Xem chi tiết', icon=':material/open_in_full:',
                               key='detail_' + title, type='secondary', width='content')
        st.caption(scope)
        st.altair_chart(styled_chart(chart), width='stretch')
    if opened:
        chart_details(chart, title, data, explanation, scope, source)


def timeline(frame, fields, title, unit, colors=None):
    if frame.empty:
        st.info('Không có dữ liệu trong phạm vi đã chọn.')
        return
    data = frame[['date', 'period', *fields]].melt(['date', 'period'], var_name='series', value_name='value')
    data['series'] = data.series.map(LABELS)
    data['Mùa'] = data.period.map(SEASONS)
    chart = alt.Chart(data).mark_line(point=True, strokeWidth=2, invalid='break-paths-show-domains').encode(
        x=alt.X('date:T', title='Ngày', axis=alt.Axis(format='%d/%m')),
        y=alt.Y('value:Q', title=unit, scale=alt.Scale(zero=False)),
        color=alt.Color('series:N', scale=alt.Scale(range=colors or [TEAL, ORANGE, NAVY]), title=None),
        detail='period:N', tooltip=[alt.Tooltip('date:T', title='Ngày', format='%d/%m/%Y'),
                                   'Mùa:N', alt.Tooltip('series:N', title='Chuỗi'),
                                   alt.Tooltip('value:Q', title=unit, format='.3f')]).properties(height=235)
    show_chart(chart, title, frame[['period', 'date', *fields]],
               f'Trục ngang là ngày quan trắc; trục dọc là {unit}. Mỗi đường biểu diễn một chuỗi trong chú giải. '
               'Khoảng trống không được thay bằng 0. Hai mùa được vẽ riêng, không nối qua tháng 7–9. '
               + ('Chuỗi sau điền/nội suy giữ lại giá trị gốc và bổ sung một số ngày; không dùng thay chuỗi AOD gốc để kết luận tương quan.'
                  if 'aod_filled_hanoi' in fields else 'Các chuỗi ngày chưa dịch độ trễ.'),
               SEASONS[season] + ' · Hà Nội' if all(not field.startswith('fire') for field in fields)
               else SEASONS[season] + ' · ' + (LABELS[fields[0]] if len(fields) == 1 else 'Cropland · toàn vùng, Hà Nội và lân cận'),
               'Bộ dữ liệu ngày cuối cùng · Công đoạn 5')


def holdout():
    st.subheader('Kiểm tra AOD bằng che khối pixel')
    metrics = load('02_AOD_Evaluation/aod_block_holdout_summary.csv',
                   ['method', 'days', 'tested_pixels', 'mae', 'rmse', 'bias'])
    if not metrics.empty:
        display = metrics.copy()
        display['method'] = display.method.replace({'previous_day_baseline': 'Baseline · ngày trước',
                                                    'temporal_symmetric_1day': 'Nội suy · đối xứng 1 ngày'})
        table(display)
        plot = display.melt('method', ['mae', 'rmse'], var_name='Chỉ số', value_name='Sai số')
        show_chart(alt.Chart(plot).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X('method:N', title=None, axis=alt.Axis(labelAngle=0)), xOffset='Chỉ số:N',
            y=alt.Y('Sai số:Q', title='Sai số AOD'),
            color=alt.Color('Chỉ số:N', scale=alt.Scale(range=[TEAL, ORANGE])),
            tooltip=['method', 'Chỉ số', alt.Tooltip('Sai số:Q', format='.4f')]).properties(height=210),
                   'Sai số AOD: nội suy và baseline', display,
                   'MAE là sai số tuyệt đối trung bình; RMSE nhạy hơn với sai số lớn. Giá trị thấp hơn tốt hơn. '
                   'Chỉ so sánh trên các pixel được che khối có quan trắc ở ngày trước và ngày sau; kết quả không đại diện khoảng mây kéo dài.',
                   'Toàn bộ tập kiểm chứng · không áp dụng bộ lọc mùa', 'AOD block holdout · Công đoạn 5')
    st.caption('MAE: sai số tuyệt đối trung bình. RMSE: nhạy hơn với sai số lớn. Cả hai càng thấp càng tốt; '
               'bias cho biết xu hướng lệch. Kết quả này áp dụng toàn bộ tập kiểm chứng, không theo bộ lọc mùa.')


def overview(sub, season):
    hero('Điểm nóng nông nghiệp và PM2.5 Hà Nội',
         'Phân tích mối liên hệ giữa điểm nóng trên đất nông nghiệp tại Đồng bằng sông Hồng và '
         'PM2.5 Hà Nội bằng VIIRS, MAIAC AOD và dữ liệu quan trắc.')
    fire = filtered(load('03_Final_Dataset/final_fire_statistics.csv',
                         ['period', 'detections', 'land_class']), season)
    kpis([('Lượt VIIRS', number(fire.detections.sum()) if not fire.empty else '—', 'Tất cả lớp phủ đất trong mùa đã chọn.'),
          ('Trên Cropland', number(sub.fire_rrd.sum()) if not sub.empty else '—', 'Lượt phát hiện, không phải số đám cháy duy nhất.'),
          ('Ngày nghiên cứu', number(len(sub)), 'Số ngày thuộc hai cửa sổ nghiên cứu.'),
          ('Ngày có PM2.5', number(sub.pm25_hanoi.notna().sum()), 'Ngày có PM2.5 Hà Nội hợp lệ.'),
          ('Ngày có AOD gốc', number(sub.aod_original_hanoi.notna().sum()), 'Ngày có AOD gốc tại Hà Nội.')])
    left, right = st.columns(2)
    with left:
        timeline(sub, ['pm25_hanoi'], 'PM2.5 tại Hà Nội', 'PM2.5 (µg/m³)')
    with right:
        timeline(sub, ['fire_rrd'], 'Điểm nóng trên Cropland', 'Lượt phát hiện', [ORANGE])

    with st.expander('Xem dữ liệu ngày và tải xuống'):
        table(sub)
        export(sub, 'daily_filtered.csv')


def fires(sub, season):
    hero('Điểm nóng & lớp phủ đất',
         'Lượt phát hiện VIIRS đối chiếu lớp Cropland của WorldCover 2021, theo mùa, tỉnh và tuần.')
    all_fire = load('03_Final_Dataset/final_fire_statistics.csv',
                    ['period', 'week_id', 'province', 'land_class', 'detections'])
    fire = filtered(all_fire, season)
    a, b = st.columns(2)
    province = a.selectbox('Tỉnh', ['Tất cả', *sorted(fire.province.dropna().unique())])
    if province != 'Tất cả':
        fire = fire[fire.province == province]
    week = b.selectbox('Tuần', ['Tất cả', *sorted(fire.week_id.dropna().unique())])
    if week != 'Tất cả':
        fire = fire[fire.week_id == week]
    total = fire.detections.sum()
    crop = fire.loc[fire.land_class == 'Cropland', 'detections'].sum()
    kpis([('Lượt VIIRS', number(total), 'Theo mùa, tỉnh và tuần đã chọn.'),
          ('Trên Cropland', number(crop), 'Theo toàn bộ bộ lọc.'),
          ('Tỷ lệ Cropland', f'{crop / total:.1%}' if total else '—', 'Cropland / tất cả lượt phát hiện.')])
    points = filtered(load('03_Image_Processing/01_Cropland_Overlay/viirs_cropland_overlay.csv',
                           ['latitude', 'longitude', 'period', 'province', 'week_id', 'land_class'], root=ROOT), season)
    if province != 'Tất cả':
        points = points[points.province == province]
    if week != 'Tất cả':
        points = points[points.week_id == week]
    points = points.copy()
    for coordinate in ['latitude', 'longitude']:
        points[coordinate] = pd.to_numeric(points[coordinate], errors='coerce')
    points = points.dropna(subset=['latitude', 'longitude'])
    with st.container(border=True, key='map_panel'):
        st.markdown('<h3 class="chart-heading">Bản đồ phân bố điểm nóng</h3>', unsafe_allow_html=True)
        st.caption(f'{SEASONS[season]} · Tỉnh: {province} · Tuần: {week}')
        if not points.empty:
            points['color'] = points.land_class.map({'Cropland': ORANGE, 'Non-Cropland': '#71869a'}).fillna('#71869a')
            st.map(points, latitude='latitude', longitude='longitude', color='color', size=65, height=360)
            st.caption('Cam: Cropland · Xám: lớp phủ khác. Tọa độ thật từ kết quả chồng phủ Công đoạn 3; áp dụng mùa, tỉnh và tuần đã chọn. Các lượt trùng vị trí có thể chồng lên nhau.')
        else:
            st.info('Không có tọa độ hợp lệ cho phạm vi đã chọn.')
    if fire.empty:
        st.info('Không có lượt phát hiện trong phạm vi đã chọn.')
    else:
        stats = fire.groupby(['province', 'land_class'], as_index=False).detections.sum()
        show_chart(alt.Chart(stats).mark_bar().encode(
            y=alt.Y('province:N', title=None, sort='-x'), x=alt.X('detections:Q', title='Lượt phát hiện'),
            color=alt.Color('land_class:N', title=None, scale=alt.Scale(domain=['Cropland', 'Non-Cropland'], range=[ORANGE, '#9caebc'])),
            tooltip=['province', 'land_class', 'detections']).properties(height=300),
                   'Phân bố lượt phát hiện theo tỉnh', stats,
                   'Chiều dài cột là tổng lượt phát hiện. Cam là Cropland, xám là các lớp phủ khác. '
                   'Một khu vực có thể được vệ tinh ghi nhận nhiều lần; số lượt không phải số đám cháy duy nhất.',
                   f'{SEASONS[season]} · Tỉnh: {province} · Tuần: {week}', 'Thống kê VIIRS cuối cùng · Công đoạn 5')
        table(stats)
    with st.expander('Bảng chi tiết theo mùa, tuần, tỉnh và lớp phủ'):
        table(fire)
    export(fire, 'fire_statistics_filtered.csv')
    comparison = all_fire.groupby(['period', 'land_class'], as_index=False).detections.sum()
    comparison['Mùa'] = comparison.period.map(SEASONS)
    show_chart(alt.Chart(comparison).mark_bar().encode(
        x=alt.X('Mùa:N', title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y('detections:Q', title='Lượt phát hiện'),
        xOffset='land_class:N', color=alt.Color('land_class:N', scale=alt.Scale(domain=['Cropland', 'Non-Cropland'], range=[ORANGE, '#9caebc'])),
        tooltip=['Mùa', 'land_class', 'detections']).properties(height=230),
               'So sánh điểm nóng giữa hai mùa', comparison,
               'So sánh số lượt VIIRS theo lớp phủ đất ở hai cửa sổ nghiên cứu. '
               'Đây là lượt quan trắc, không phải diện tích bị đốt hay số vụ cháy.',
               'Cả hai mùa · mọi tỉnh và tuần', 'Thống kê VIIRS cuối cùng · Công đoạn 5')
    with st.expander('Chuỗi ngày Cropland · toàn vùng theo mùa'):
        st.caption('Chuỗi ngày chỉ áp dụng bộ lọc mùa; dữ liệu tổng hợp ngày không có chiều tỉnh/tuần.')
        timeline(sub, ['fire_rrd', 'fire_hanoi', 'fire_surrounding'], 'Lượt phát hiện mỗi ngày', 'Lượt phát hiện', [ORANGE, TEAL, NAVY])
        export(sub[['period', 'date', 'fire_rrd', 'fire_hanoi', 'fire_surrounding']], 'fire_daily.csv')
    example = ROOT / '03_Image_Processing/06_Maps/fire_density_example.png'
    if example.is_file():
        with st.expander('Bản đồ tham chiếu · Công đoạn 3'):
            st.image(str(example), caption='Ví dụ một tuần đã xuất; không phản ánh bộ lọc hiện tại.')



def aod(sub):
    hero('AOD · quan trắc & độ phủ',
         'AOD 550 nm tại Hà Nội từ MODIS MAIAC. Phân biệt dữ liệu gốc với chuỗi sau điền/nội suy.')
    n = len(sub)
    valid = sub.aod_original_hanoi.notna().sum()
    coverage = sub.aod_coverage_pct.mean()
    kpis([('Ngày có AOD gốc', f'{valid} / {n}', 'Ngày có giá trị AOD gốc tại Hà Nội.'),
          ('Tỷ lệ ngày hợp lệ', f'{valid/n:.1%}' if n else '—', 'Số ngày có AOD gốc / ngày nghiên cứu.'),
          ('Độ phủ pixel TB', f'{coverage:.1f}%' if pd.notna(coverage) else '—', 'Trung bình cột aod_coverage_pct theo mùa.'),
          ('Ngày sau điền/nội suy', number(sub.aod_filled_hanoi.notna().sum()), 'Bao gồm cả giá trị gốc được giữ lại.')])
    st.warning('AOD nội suy không dùng làm dữ liệu chính để kết luận tương quan. Giá trị thiếu được giữ nguyên, không chuyển thành AOD = 0.')
    timeline(sub, ['aod_original_hanoi', 'aod_filled_hanoi'], 'Quan trắc gốc và sau điền/nội suy', 'AOD (không đơn vị)')
    timeline(sub, ['aod_coverage_pct'], 'Độ phủ pixel theo ngày', 'Độ phủ (%)')
    holdout()
    st.caption('Thử nghiệm che khối có điều kiện quan trắc thuận lợi hơn khoảng thiếu do mây kéo dài.')
    with st.expander('Dữ liệu ngày và tải xuống'):
        table(sub)
        export(sub, 'aod_daily.csv')


def correlations(sub, season):
    hero('Tương quan và độ trễ',
         'So sánh mối liên hệ giữa các chuỗi quan trắc ở độ trễ từ 0 đến 3 ngày.')
    lag = load('03_Final_Dataset/final_lag_results.csv',
               ['comparison', 'season', 'lag_days', 'pearson_r', 'spearman_rho', 'n_pairs', 'pearson_p',
                'spearman_p', 'pearson_p_fdr_bh', 'spearman_p_fdr_bh', 'x', 'y'])
    if lag.empty:
        return
    left, right = st.columns([2, 1])
    name = left.selectbox('Cặp biến', lag.comparison.unique(), format_func=lambda x: PAIRS.get(x, x))
    method = right.radio('Phương pháp', ['pearson_r', 'spearman_rho'],
                         format_func=lambda x: 'Pearson' if x == 'pearson_r' else 'Spearman', horizontal=True)
    selected = ['May_Jun_2025', 'Oct_Nov_2025'] if season == 'Tất cả' else [season]
    series = lag[(lag.comparison == name) & lag.season.isin(selected)].copy()
    series['Mùa'] = series.season.map(SEASONS)
    p = 'pearson_p' if method == 'pearson_r' else 'spearman_p'
    highlight = lag[(lag.comparison == 'fire_pm25') & (lag.season == 'Oct_Nov_2025') & (lag.lag_days == 2)]
    if not highlight.empty:
        row = highlight.iloc[0]
        st.info(f'Kết quả tham chiếu · VIIRS–PM2.5 · tháng 10–11/2025 · lag 2 ngày: '
                f'Pearson r = {row.pearson_r:.4f}, n = {int(row.n_pairs)} cặp ngày. '
                'Đây là tương quan, không phải bằng chứng nhân quả; khung này không thay đổi theo bộ lọc.')
    chart = alt.Chart(series).mark_line(point=alt.OverlayMarkDef(size=85), strokeWidth=3).encode(
        x=alt.X('lag_days:Q', title='Độ trễ (ngày)', axis=alt.Axis(values=[0, 1, 2, 3])),
        y=alt.Y(f'{method}:Q', title='Hệ số tương quan', scale=alt.Scale(domain=[-1, 1])),
        color=alt.Color('Mùa:N', scale=alt.Scale(range=[TEAL, ORANGE])),
        tooltip=['Mùa', alt.Tooltip('lag_days:Q', title='Lag'), alt.Tooltip(f'{method}:Q', title='Hệ số', format='.4f'),
                 alt.Tooltip('n_pairs:Q', title='Số cặp'), alt.Tooltip(f'{p}:Q', title='p-value', format='.3g'),
                 alt.Tooltip(f'{p}_fdr_bh:Q', title='p điều chỉnh BH', format='.3g')]).properties(height=310)
    zero = alt.Chart(pd.DataFrame({'zero': [0]})).mark_rule(color='#9caebc', strokeDash=[4, 4]).encode(y='zero:Q')
    show_chart(chart + zero, 'Hệ số tương quan theo độ trễ', series.drop(columns='Mùa'),
               'Hệ số gần +1 biểu thị mối liên hệ cùng chiều, gần −1 biểu thị ngược chiều. '
               'Số cặp ngày có thể khác nhau giữa các lag. Đọc đồng thời hệ số, n_pairs và p-value điều chỉnh FDR. '
               'Lag tốt nhất được chọn sau khi xem kết quả; tương quan không chứng minh nhân quả.',
               f'{PAIRS.get(name, name)} · {SEASONS[season]} · ' + ('Pearson' if method == 'pearson_r' else 'Spearman'),
               'Kết quả tương quan và độ trễ cuối cùng · Công đoạn 5')
    st.caption('FDR (Benjamini–Hochberg) điều chỉnh p-value khi thực hiện nhiều phép kiểm định. '
               'p-value thông thường chưa điều chỉnh tự tương quan; xem thêm Bootstrap và Circular Shift ở trang QA.')
    table(series[['Mùa', 'lag_days', 'n_pairs', method, p, p + '_fdr_bh']])
    with st.expander('Toàn bộ cột kết quả và tải CSV'):
        table(series.drop(columns='Mùa'))
        export(series.drop(columns='Mùa'), 'correlation_selected.csv')
    st.subheader('Bối cảnh chuỗi quan trắc · chưa dịch lag')
    st.caption('Các chuỗi dưới đây giúp quan sát thời điểm và khoảng thiếu; không phải các cặp mẫu dùng tính hệ số theo lag.')
    if not series.empty:
        a, b = st.columns(2)
        for container, field in [(a, series.iloc[0].x), (b, series.iloc[0].y)]:
            with container:
                unit = 'Lượt phát hiện' if field.startswith('fire') else ('PM2.5 (µg/m³)' if field.startswith('pm25') else 'AOD (không đơn vị)')
                timeline(sub, [field], LABELS.get(field, field), unit)


def qa(season):
    hero('Kiểm chứng & chất lượng dữ liệu',
         'Theo dõi chất lượng dữ liệu và mức bất định của kết quả phân tích.')
    reports = [('02_Data_Preprocessing/05_Quality_Reports/stage2_validation.json', '02 · Tiền xử lý'),
               ('03_Image_Processing/07_Quality_Reports/stage3_validation.json', '03 · Xử lý ảnh'),
               ('04_Correlation_Analysis/06_Quality_Reports/stage4_validation.json', '04 · Tương quan'),
               ('05_Final_Evaluation/05_Quality_Reports/stage5_validation.json', '05 · Đánh giá')]
    rows, checks = [], []
    for relative, label in reports:
        try:
            obj = json.loads((ROOT / relative).read_text(encoding='utf-8'))
            counts = obj.get('counts', obj.get('test_counts', {}))
            rows.append({'Công đoạn': label, 'Trạng thái': obj.get('status', obj.get('validation_status', 'Không rõ')),
                         **{s: counts.get(s, 0) for s in ['PASS', 'WARN', 'FAIL']}})
            checks.extend({'Công đoạn': label, **item} for item in obj.get('checks', obj.get('tests', [])))
        except (OSError, ValueError, TypeError) as exc:
            st.warning(f'Không đọc được báo cáo {relative}: {exc}')
            rows.append({'Công đoạn': label, 'Trạng thái': 'Không có báo cáo', 'PASS': None, 'WARN': None, 'FAIL': None})
    st.subheader('Trạng thái validation · toàn bộ dữ liệu')
    table(pd.DataFrame(rows))
    st.caption('Công đoạn 1: không có báo cáo validation riêng trong các nguồn dashboard đang sử dụng.')
    details = pd.DataFrame(checks)
    if not details.empty:
        issues = details[details.status != 'PASS']
        if not issues.empty:
            st.warning('Có kiểm tra cần chú ý. Nội dung thực tế từ báo cáo:')
            table(issues)
        with st.expander('Tất cả kiểm tra chi tiết'):
            table(details)
    st.subheader('Độ tin cậy của tương quan')
    bs = filtered(load('01_Robustness/bootstrap_ci.csv', ['season', 'comparison', 'lag_days', 'pearson_r',
                       'ci_95_low', 'ci_95_high', 'n_pairs']), season, 'season')
    sh = filtered(load('01_Robustness/circular_shift_tests.csv', ['season', 'comparison', 'lag_days',
                       'r_calendar', 'shift_p_two_sided', 'null_shifts']), season, 'season')
    st.caption('Bộ lọc mùa áp dụng cho hai bảng độ tin cậy bên dưới. Validation và AOD holdout dùng toàn bộ tập kiểm chứng.')
    tabs = st.tabs(['Block Bootstrap', 'Circular Shift', 'AOD block holdout'])
    with tabs[0], st.container(border=True):
        st.write('Khoảng tin cậy 95% mô tả mức bất định của hệ số khi lấy mẫu lại theo khối. Khoảng chứa 0 cho thấy dấu tương quan chưa rõ ràng.')
        table(bs)
        export(bs, 'bootstrap_ci.csv')
        st.caption('Bootstrap trên cặp ngày đã ghép có thể nén các ngày AOD bị thiếu; CI không phải kiểm chứng tuyệt đối.')
    with tabs[1], st.container(border=True):
        st.write('Dịch vòng chuỗi trong từng mùa để so sánh tương quan quan sát với các cách căn thời gian khác. '
                 'shift_p_two_sided nhỏ cho thấy hệ số quan sát ít gặp trong các phép dịch đã thử; không chứng minh nhân quả.')
        table(sh)
        export(sh, 'circular_shift_tests.csv')
    with tabs[2], st.container(border=True):
        holdout()


PAGES = [
    ('Tổng quan', 'space_dashboard'),
    ('Điểm nóng VIIRS', 'local_fire_department'),
    ('AOD', 'layers'),
    ('Tương quan và độ trễ', 'query_stats'),
    ('Kiểm chứng và QA', 'fact_check'),
    ('Kết luận', 'summarize'),
    ('Khái niệm & phương pháp', 'menu_book'),
]
def render_page(page):
    if page == 'Kết luận':
        from conclusions import render_conclusions
        hero('Kết luận & ý nghĩa', 'Từ kết quả quan trắc đến những điều có thể rút ra về điểm nóng nông nghiệp và PM2.5 Hà Nội.')
        render_conclusions(load, season, SEASONS)
    elif page == 'Khái niệm & phương pháp':
        from methods import render_methods
        hero('Khái niệm & phương pháp', 'Hướng dẫn đọc dữ liệu, hiểu các phép phân tích và giới hạn của nghiên cứu.')
        render_methods(ROOT)
    elif page == 'Kiểm chứng và QA':
        qa(season)
    else:
        daily = load('03_Final_Dataset/final_daily_dataset.csv',
                     ['period', 'date', 'fire_rrd', 'fire_hanoi', 'fire_surrounding', 'pm25_hanoi',
                      'aod_original_hanoi', 'aod_filled_hanoi', 'aod_coverage_pct'])
        sub = filtered(daily, season)
        if page == 'Tổng quan':
            overview(sub, season)
        elif page == 'Điểm nóng VIIRS':
            fires(sub, season)
        elif page == 'AOD':
            aod(sub)
        else:
            correlations(sub, season)


PAGE_OBJECTS = {name: st.Page(partial(render_page, name), title=name, url_path=slug, default=i == 0)
                for i, ((name, _), slug) in enumerate(zip(PAGES,
                    ['overview', 'viirs', 'aod', 'correlation', 'quality', 'conclusions', 'methods']))}
current_page = st.navigation(list(PAGE_OBJECTS.values()), position='hidden')


def navigate(name):
    st.switch_page(PAGE_OBJECTS[name])


with st.sidebar:
    st.markdown('<div class="research-brand">Điểm nóng nông nghiệp<br>& PM2.5 Hà Nội</div>'
                '<p class="research-region">Đồng bằng sông Hồng<br>VIIRS · MAIAC AOD · Quan trắc</p>', unsafe_allow_html=True)
    with st.container(key='research_nav'):
        for name, icon in PAGES:
            if st.button(name, key='nav_' + name, icon=f':material/{icon}:', width='stretch',
                         type='primary' if current_page.title == name else 'secondary'):
                navigate(name)
    st.divider()
    season = st.selectbox('Mùa nghiên cứu', ['Tất cả', 'May_Jun_2025', 'Oct_Nov_2025'], format_func=lambda x: SEASONS[x])
    st.caption('11 tỉnh ĐBSH theo ranh giới lịch sử. PM2.5 và AOD tại Hà Nội.')
current_page.run()
