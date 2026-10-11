# DE 9 - KIEM THU TONG THE CONG DOAN 2

Ket luan: **PASS_WITH_WARNINGS**

PASS=31 / WARN=1 / FAIL=0

## Chi tiet
- **PASS** Input DATARAW exists: E:\01_UNI\XLA\DATARAW
- **PASS** Stage2 output exists: E:\01_UNI\XLA\02_Data_Preprocessing
- **PASS** AOD COMPLETED 488/488: {'state': 'COMPLETED', 'successful_files': 488, 'failed_files': 0, 'days_processed': 122}
- **PASS** AOD daily 122 dates exactly: rows=122, missing=[], extra=[]
- **PASS** AOD daily no failed HDF: days=122
- **PASS** AOD coverage 0..100: range=0.0..99.181
- **WARN** AOD days with any valid pixels: zero-coverage days=37
- **PASS** AOD manifest 488 successful HDF: rows=488; failed=0
- **PASS** AOD manifest 4 HDF per date: dates=122, unique (day,tile)=488
- **PASS** AOD GeoTIFF 122: found=122
- **PASS** AOD observation-count TIFF 122: found=122
- **PASS** AOD raster metadata AOD_055_2025-05-01.tif: CRS=EPSG:4326 shape=174x279, res=(0.01, 0.01)
- **PASS** AOD physical plausibility AOD_055_2025-05-01.tif: count=67 min=0.0 max=0.2460000067949295
- **PASS** AOD count matches shape AOD_055_2025-05-01.tif: count shape=(174, 279)
- **PASS** AOD raster metadata AOD_055_2025-10-01.tif: CRS=EPSG:4326 shape=174x279, res=(0.01, 0.01)
- **PASS** AOD physical plausibility AOD_055_2025-10-01.tif: count=2183 min=0.0 max=0.326555073261261
- **PASS** AOD count matches shape AOD_055_2025-10-01.tif: count shape=(174, 279)
- **PASS** AOD raster metadata AOD_055_2025-11-30.tif: CRS=EPSG:4326 shape=174x279, res=(0.01, 0.01)
- **PASS** AOD physical plausibility AOD_055_2025-11-30.tif: count=6490 min=0.014953062869608402 max=0.6800000667572021
- **PASS** AOD count matches shape AOD_055_2025-11-30.tif: count shape=(174, 279)
- **PASS** VIIRS season output 2: viirs_May_Jun_2025.csv,viirs_Oct_Nov_2025.csv
- **PASS** VIIRS not accidentally appended: output rows=1068; previous run first reported 1068
- **PASS** VIIRS exact duplicate rows by source/key: duplicate rows=0
- **PASS** VIIRS time and period consistent: bad local time=0; mismatch period=0
- **PASS** PM25 output matches previous run: hourly=5844, daily=255, usable=241
- **PASS** PM25 unique sensor+UTC hour: rows=5844, duplicates=0
- **PASS** PM25 values numeric and nonnegative: hourly rows=5844
- **PASS** PM25 usable threshold >=18 hours: daily rows=255
- **PASS** Spatial 3 WorldCover tiles: tiles=3
- **PASS** Spatial 3 cropped GeoTIFF: cropped rasters=3
- **PASS** Spatial 11 provinces and region union: provinces=11, region=1
- **PASS** Spatial geometries valid: 11 province geometries & union

## Gioi han nghiem thu
- Báo cáo stage2_run_report.json thường chỉ chứa module chạy cuối; không dùng làm bằng chứng đã chạy đủ 4 module.
- VIIRS CSV được ghi append bởi phiên bản src/viirs.py cũ: không chạy lại VIIRS trước khi sửa tính idempotent.
- PM2.5 ngưỡng 18 giờ/ngày là quyết định phương pháp, cần ghi trong báo cáo; các ngoại lệ >500 µg/m³ được cảnh báo chứ chưa loại.
- Ngày AOD là ngày UTC danh định; không suy diễn thời gian quan trắc từng pixel đã được chuyển UTC+7.
- WorldCover 2021 là đại diện loại đất cho năm 2025; VIIRS chưa phải đốt rơm rạ trước overlay Cropland ở Công đoạn 3.
