from pathlib import Path
import pandas as pd
import geopandas as gpd
from .common import write_csv,write_json,period_of

def run(groups,out):
    src=groups['viirs']; target=out/'01_VIIRS';target.mkdir(parents=True,exist_ok=True)
    polygon=groups['boundary']/'red_river_delta_11_provinces.geojson'
    if not polygon.exists():raise FileNotFoundError(polygon)
    bounds=gpd.read_file(polygon).to_crs(4326); bounds=bounds.reset_index(drop=True)
    # Avoid overlapping administrative polygons causing duplicate joins.
    geom_union=bounds.geometry.union_all() if hasattr(bounds.geometry,'union_all') else bounds.unary_union
    boundary=gpd.GeoDataFrame(geometry=[geom_union],crs='EPSG:4326')
    files=sorted(src.rglob('*.csv')); summary=[];reject=[];counts=[]
    if not files: raise RuntimeError('Không có CSV VIIRS')
    output_files={}
    for file in files:
        for chunkno,df in enumerate(pd.read_csv(file,chunksize=150000,low_memory=False)):
            total=len(df)
            for col in ('latitude','longitude','acq_date'):
                if col not in df:raise ValueError(f'{file.name} thiếu {col}')
            lat=pd.to_numeric(df.latitude,errors='coerce');lon=pd.to_numeric(df.longitude,errors='coerce')
            utc_date=pd.to_datetime(df.acq_date,errors='coerce')
            tstr=df['acq_time'].fillna(0).astype(str).str.replace(r'\..*$','',regex=True).str.zfill(4).str[-4:]
            dt=pd.to_datetime(utc_date.dt.strftime('%Y-%m-%d')+' '+tstr.str[:2]+':'+tstr.str[2:],utc=True,errors='coerce')
            good=lat.between(-90,90)&lon.between(-180,180)&dt.notna()
            reject.append({'file':file.name,'chunk':chunkno,'input':total,'invalid_core':int((~good).sum())})
            if not good.any():continue
            sub=df.loc[good].copy();sub['longitude']=lon[good];sub['latitude']=lat[good]
            sub['datetime_utc']=dt[good].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            local=dt[good].dt.tz_convert('Asia/Ho_Chi_Minh')
            sub['datetime_local']=local.dt.strftime('%Y-%m-%dT%H:%M:%S%z')
            sub['date_local']=local.dt.strftime('%Y-%m-%d')
            sub['source_file']=file.name
            # BBOX first for efficient point-in-polygon.
            west,south,east,north=geom_union.bounds
            crop=sub.longitude.between(west,east)&sub.latitude.between(south,north)
            sub=sub.loc[crop].copy()
            if sub.empty:continue
            point=gpd.GeoSeries(gpd.points_from_xy(sub.longitude,sub.latitude),index=sub.index,crs=4326)
            inside=point.intersects(geom_union);sub=sub.loc[inside].copy()
            if sub.empty:continue
            # Per province is optional label; union is authoritative for inclusion.
            points=gpd.GeoDataFrame(sub,geometry=gpd.points_from_xy(sub.longitude,sub.latitude),crs=4326)
            province_col=next((c for c in ['NAME_1','province','name'] if c in bounds.columns),None)
            if province_col:
                labelled=gpd.sjoin(points,bounds[[province_col,'geometry']],how='left',predicate='intersects')
                labelled=labelled.loc[~labelled.index.duplicated(keep='first')].sort_index()
                sub['province']=labelled.reindex(sub.index)[province_col].values
            sub['period']=sub['date_local'].map(lambda d:period_of(d))
            for period,piece in sub.groupby('period',dropna=False):
                if period is None or pd.isna(period):continue
                path=target/f'viirs_{period}.csv';header=not path.exists()
                piece.to_csv(path,index=False,mode='a',header=header,encoding='utf-8-sig')
                counts.append({'file':file.name,'period':period,'records':len(piece)})
            summary.append({'file':file.name,'chunk':chunkno,'bbox_records':int(crop.sum()),'inside_provinces':len(sub)})
    write_csv(target/'viirs_quality.csv',reject)
    write_csv(target/'viirs_chunk_summary.csv',summary)
    write_csv(target/'viirs_counts.csv',counts)
    write_json(target/'README_metadata.json',{'type_note':'FIRMS type=0 không đồng nghĩa đốt rơm rạ','observations_note':'Không gộp các quan trắc từ các vệ tinh thành sự kiện cháy','time_note':'Lọc mùa theo ngày địa phương; các bản ghi gần biên UTC có thể chuyển mùa'})
    return {'input_files':len(files),'records_in_region':sum(x['inside_provinces'] for x in summary),'by_period':counts}
