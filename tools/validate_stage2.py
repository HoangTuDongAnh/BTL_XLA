"""Read-only independent QA for De9 Stage 2. Python 3.11+; pandas, rasterio, geopandas available."""
from pathlib import Path
import argparse, csv, json, math, re
from collections import Counter
from datetime import date, timedelta


def iso_days(a,b):
    a=date.fromisoformat(a);b=date.fromisoformat(b)
    while a<=b:
        yield a.isoformat();a+=timedelta(days=1)

EXPECTED=set(iso_days('2025-05-01','2025-06-30'))|set(iso_days('2025-10-01','2025-11-30'))

class Audit:
    def __init__(self): self.tests=[];self.metrics={};self.warnings=[]
    def check(self, name, good, detail, level='error'):
        self.tests.append({'test':name,'status':'PASS' if good else ('WARN' if level=='warning' else 'FAIL'),'detail':str(detail)})
    def warn(self,x):self.warnings.append(str(x))

def rows(path):
    with path.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def to_float(x):
    try:return float(x)
    except (TypeError,ValueError):return math.nan

def find(folder,pattern):return sorted(folder.glob(pattern))

def main():
    p=argparse.ArgumentParser();p.add_argument('--project-root',default='.');a=p.parse_args()
    root=Path(a.project_root).resolve();out=root/'02_Data_Preprocessing';raw=root/'DATARAW';aud=Audit()
    destination=out/'05_Quality_Reports';destination.mkdir(parents=True,exist_ok=True)
    aud.check('Input DATARAW exists',raw.is_dir(),raw)
    aud.check('Stage2 output exists',out.is_dir(),out)
    # AOD file-level completeness and per-day rasters
    ap=out/'02_AOD';statusfile=ap/'aod_status.json'
    status={}
    if statusfile.exists():
        try:status=json.loads(statusfile.read_text(encoding='utf-8'))
        except Exception as e:aud.check('AOD status JSON',False,e)
    aud.check('AOD COMPLETED 488/488',status.get('state')=='COMPLETED' and status.get('successful_files')==488 and status.get('failed_files')==0 and status.get('days_processed')==122,str({k:status.get(k) for k in ['state','successful_files','failed_files','days_processed']}))
    aud.metrics['aod_run_status']=status
    daily_path=ap/'aod_daily_quality.csv';daily=rows(daily_path) if daily_path.exists() else []
    dates=[r.get('date_utc') for r in daily]; c=Counter(dates)
    aud.check('AOD daily 122 dates exactly',set(dates)==EXPECTED and len(dates)==122 and all(n==1 for n in c.values()),f'rows={len(dates)}, missing={sorted(EXPECTED-set(dates))[:8]}, extra={sorted(set(dates)-EXPECTED)[:8]}')
    aud.check('AOD daily no failed HDF',len(daily)==122 and all(int(r.get('failed_files',-1))==0 for r in daily),f'days={len(daily)}')
    coverage=[to_float(r.get('coverage_pct')) for r in daily]
    if daily:
        aud.check('AOD coverage 0..100',all(math.isfinite(x) and 0<=x<=100 for x in coverage),'range=%s..%s'%(min(coverage),max(coverage)))
        aud.metrics['aod_coverage_pct']={'minimum':round(min(coverage),3),'mean':round(sum(coverage)/len(coverage),3),'maximum':round(max(coverage),3),'days_with_zero_valid_pixels':sum(x==0 for x in coverage),'days_lt_10pct':sum(x<10 for x in coverage)}
        zeros=sum(x==0 for x in coverage)
        aud.check('AOD days with any valid pixels',zeros==0,f'zero-coverage days={zeros}',level='warning')
    manifest=ap/'aod_file_manifest.csv';fm=rows(manifest) if manifest.exists() else []
    aud.check('AOD manifest 488 successful HDF',len(fm)==488 and all(r.get('status')=='ok' for r in fm),f'rows={len(fm)}; failed={sum(r.get("status")!="ok" for r in fm)}')
    aud.check('AOD manifest 4 HDF per date',len(fm)==488 and len(set((r['date'],r['tile']) for r in fm))==488 and all(n==4 for n in Counter(r.get('date') for r in fm).values()),'dates=%d, unique (day,tile)=%d'%(len(set(r.get('date') for r in fm)),len(set((r.get('date'),r.get('tile')) for r in fm))))
    rasters=find(ap/'Daily','AOD_055_*.tif');counts=find(ap/'Daily','obs_count_*.tif')
    aud.check('AOD GeoTIFF 122',len(rasters)==122 and {f.stem.removeprefix('AOD_055_') for f in rasters}==EXPECTED,f'found={len(rasters)}')
    aud.check('AOD observation-count TIFF 122',len(counts)==122 and {f.stem.removeprefix('obs_count_') for f in counts}==EXPECTED,f'found={len(counts)}')
    # raster sample checks: first, mid, last; test affine / crs / means and nonzero pixel count
    try:
        import rasterio,numpy as np
        sample_indices=sorted(set([0,len(rasters)//2,len(rasters)-1])) if rasters else []
        for i in sample_indices:
            f=rasters[i];count_path=ap/'Daily'/('obs_count_'+f.stem.removeprefix('AOD_055_')+'.tif')
            with rasterio.open(f) as ds:
                goodmeta=(ds.crs is not None and ds.crs.to_epsg()==4326 and ds.count==1 and ds.res[0]>0 and ds.res[1]>0)
                aud.check('AOD raster metadata '+f.name,goodmeta,f'CRS={ds.crs} shape={ds.height}x{ds.width}, res={ds.res}')
                arr=ds.read(1,masked=True); vals=np.asarray(arr.compressed())
                finite=vals[np.isfinite(vals)]
                mean=float(finite.mean()) if len(finite) else None
                aud.metrics.setdefault('aod_sample_tiffs',[]).append({'filename':f.name,'valid_pixels':len(finite),'mean':mean,'min':float(finite.min()) if len(finite) else None,'max':float(finite.max()) if len(finite) else None})
                aud.check('AOD physical plausibility '+f.name,not len(finite) or (np.isfinite(finite).all() and float(finite.min())>=-0.101 and float(finite.max())<=6.001),f'count={len(finite)} min={float(finite.min()) if len(finite) else "none"} max={float(finite.max()) if len(finite) else "none"}',level='warning')
                if count_path.exists():
                    with rasterio.open(count_path) as csrc:
                        aud.check('AOD count matches shape '+f.name,ds.shape==csrc.shape and ds.crs==csrc.crs and ds.transform==csrc.transform,f'count shape={csrc.shape}')
    except ImportError as e:aud.check('Raster library import',False,e)
    except Exception as e:aud.check('AOD raster read sample',False,f'{type(e).__name__}: {e}')
    # VIIRS: counts and duplicates; beware append-on-rerun
    vp=out/'01_VIIRS';viirs_files=find(vp,'viirs_*_2025.csv')
    aud.check('VIIRS season output 2',len(viirs_files)==2,','.join(x.name for x in viirs_files))
    total_v=0;dup=0;bad_times=0;period_bad=0;byperiod={}
    try:
        import pandas as pd
        for f in viirs_files:
            df=pd.read_csv(f,low_memory=False);total_v+=len(df);byperiod[f.stem]=len(df)
            key=[x for x in ['source_file','latitude','longitude','acq_date','acq_time','satellite','instrument','frp'] if x in df]
            if key:dup+=int(df.duplicated(subset=key).sum())
            if 'datetime_local' in df:bad_times+=int(pd.to_datetime(df['datetime_local'],errors='coerce',utc=True).isna().sum())
            if 'period' in df:period_bad+=int((df['period']!=f.stem.removeprefix('viirs_')).sum())
        aud.metrics['viirs']={'rows':total_v,'per_period':byperiod,'duplicate_source_observations':dup}
        aud.check('VIIRS not accidentally appended',total_v==1068,f'output rows={total_v}; previous run first reported 1068',level='warning')
        aud.check('VIIRS exact duplicate rows by source/key',dup==0,f'duplicate rows={dup}',level='warning')
        aud.check('VIIRS time and period consistent',bad_times==0 and period_bad==0,f'bad local time={bad_times}; mismatch period={period_bad}')
    except Exception as e:aud.check('VIIRS parse',False,f'{type(e).__name__}: {e}')
    # PM25 audit
    pp=out/'03_PM25';ph=pp/'pm25_hourly.csv';pdfile=pp/'pm25_daily.csv';hour=rows(ph) if ph.exists() else [];days=rows(pdfile) if pdfile.exists() else []
    usable=sum(str(x.get('usable_daily','')).lower()=='true' for x in days)
    aud.metrics['pm25']={'hourly_rows':len(hour),'daily_rows':len(days),'usable_daily_rows':usable}
    aud.check('PM25 output matches previous run',len(hour)==5844 and len(days)==255 and usable==241,f'hourly={len(hour)}, daily={len(days)}, usable={usable}',level='warning')
    times=[(r.get('sensor_id'),r.get('time_utc')) for r in hour]
    aud.check('PM25 unique sensor+UTC hour',len(times)==len(set(times)),f'rows={len(times)}, duplicates={len(times)-len(set(times))}')
    aud.check('PM25 values numeric and nonnegative',all(math.isfinite(to_float(x.get('value_ugm3'))) and to_float(x.get('value_ugm3'))>=0 for x in hour),f'hourly rows={len(hour)}')
    aud.check('PM25 usable threshold >=18 hours',all((str(x.get('usable_daily','')).lower()=='true')==(int(x.get('n_valid_hours','0'))>=18) for x in days),f'daily rows={len(days)}')
    # Spatial
    sp=out/'04_Spatial';geo=sp/'provinces.geojson';region=sp/'region.geojson';world=rows(sp/'worldcover_quality.csv') if (sp/'worldcover_quality.csv').exists() else []
    aud.check('Spatial 3 WorldCover tiles',len(world)==3 and all(int(r.get('pixels_in_roi','0'))>0 for r in world),f'tiles={len(world)}')
    cropped=find(sp,'*_Map_region.tif');aud.check('Spatial 3 cropped GeoTIFF',len(cropped)==3,f'cropped rasters={len(cropped)}')
    try:
        import geopandas as gpd
        provinces=gpd.read_file(geo);rg=gpd.read_file(region)
        aud.check('Spatial 11 provinces and region union',len(provinces)==11 and len(rg)==1,f'provinces={len(provinces)}, region={len(rg)}')
        aud.check('Spatial geometries valid',bool(provinces.geometry.is_valid.all()) and bool(rg.geometry.is_valid.all()),'11 province geometries & union')
    except Exception as e:aud.check('Spatial geometry load',False,f'{type(e).__name__}: {e}')
    # Cross stage status: stage2_run_report often last run is only AOD - not complete all
    aud.warn('Báo cáo stage2_run_report.json thường chỉ chứa module chạy cuối; không dùng làm bằng chứng đã chạy đủ 4 module.')
    aud.warn('VIIRS CSV được ghi append bởi phiên bản src/viirs.py cũ: không chạy lại VIIRS trước khi sửa tính idempotent.')
    aud.warn('PM2.5 ngưỡng 18 giờ/ngày là quyết định phương pháp, cần ghi trong báo cáo; các ngoại lệ >500 µg/m³ được cảnh báo chứ chưa loại.')
    aud.warn('Ngày AOD là ngày UTC danh định; không suy diễn thời gian quan trắc từng pixel đã được chuyển UTC+7.')
    aud.warn('WorldCover 2021 là đại diện loại đất cho năm 2025; VIIRS chưa phải đốt rơm rạ trước overlay Cropland ở Công đoạn 3.')
    status_counts=Counter(t['status'] for t in aud.tests)
    report={'project':str(root),'validation_status':'FAIL' if status_counts['FAIL'] else ('PASS_WITH_WARNINGS' if status_counts['WARN'] else 'PASS'),'test_counts':dict(status_counts),'tests':aud.tests,'metrics':aud.metrics,'scientific_notes':aud.warnings}
    (destination/'stage2_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    with (destination/'stage2_validation_checks.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=['test','status','detail']);w.writeheader();w.writerows(aud.tests)
    md=['# DE 9 - KIEM THU TONG THE CONG DOAN 2','','Ket luan: **'+report['validation_status']+'**','',f"PASS={status_counts['PASS']} / WARN={status_counts['WARN']} / FAIL={status_counts['FAIL']}",'','## Chi tiet']
    md.extend(f"- **{x['status']}** {x['test']}: {x['detail']}" for x in aud.tests)
    md+=['','## Gioi han nghiem thu'];md.extend(f'- {x}' for x in aud.warnings)
    (destination/'stage2_validation_summary.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print('Validation:',report['validation_status']);print('PASS:',status_counts['PASS'],'WARN:',status_counts['WARN'],'FAIL:',status_counts['FAIL']);print('Report:',destination/'stage2_validation.json')
    if status_counts['FAIL']:return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
