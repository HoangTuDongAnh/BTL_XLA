import unicodedata
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from .core import PERIODS,calendar,save_csv,save_json


def hanoi_polygon(provinces):
    col=next((c for c in ['NAME_1','province_name','province','name'] if c in provinces.columns),None)
    if col is None:raise ValueError('No province name field')
    def ascii_name(v):
        s=unicodedata.normalize('NFKD',str(v))
        return ''.join(c.lower() for c in s if c.isascii() and c.isalpha())
    hits=provinces[provinces[col].map(ascii_name).eq('hanoi')]
    if len(hits)!=1:raise ValueError(f'Cannot uniquely identify Hanoi polygon from {col}: {provinces[col].tolist()}')
    return hits

def build_fire(s3,out):
    path=s3/'01_Cropland_Overlay'/'viirs_cropland_overlay.csv'
    if not path.is_file():raise FileNotFoundError(path)
    df=pd.read_csv(path,low_memory=False)
    needed={'date_local','period','land_class','longitude','latitude'}
    if not needed.issubset(df.columns):raise ValueError(f'Overlay missing columns: {needed-set(df.columns)}')
    if len(df)!=1068:raise ValueError(f'Expected 1068 VIIRS observations from validated Stage3, got {len(df)}')
    if df[['date_local','period']].isna().any().any():raise ValueError('VIIRS missing date/period')
    if df.duplicated().any():raise ValueError('VIIRS duplicate complete rows; review Stage3 output')
    geo=gpd.GeoDataFrame(df,geometry=gpd.points_from_xy(df.longitude,df.latitude),crs='EPSG:4326')
    boundary=s3.parent/'02_Data_Preprocessing'/'04_Spatial'/'provinces.geojson'
    # Province labels might be inherited from the FIRMS preprocessing.
    # For Hanoi vs surrounding, prefer province polygon test (not string aliases).
    provinces=gpd.read_file(boundary).to_crs('EPSG:4326')
    hanoi=hanoi_polygon(provinces)
    hgeo=hanoi.geometry.union_all()
    geo['is_hanoi']=geo.geometry.intersects(hgeo)
    crop=geo[geo.land_class.eq('Cropland')].copy()
    counts=crop.groupby(['period','date_local'],as_index=False).agg(fire_rrd=('land_class','size'),fire_hanoi=('is_hanoi','sum'))
    counts['fire_surrounding']=counts.fire_rrd-counts.fire_hanoi
    result=calendar().merge(counts,left_on=['period','date'],right_on=['period','date_local'],how='left').drop(columns=['date_local'])
    for column in ['fire_rrd','fire_hanoi','fire_surrounding']:
        result[column]=result[column].fillna(0).astype(int)
    save_csv(result,out/'01_Daily_Dataset'/'fire_daily_timeseries.csv')
    save_json({'input_rows':len(df),'cropland_points':len(crop),'days':len(result),'fire_total':int(result.fire_rrd.sum()),'note':'0 indicates no FIRMS Cropland detection in supplied archive, not absence of burning'},out/'06_Quality_Reports'/'fire_audit.json')
    return result


def build_pm(base,out,min_hours=18):
    path=base/'03_PM25'/'pm25_daily.csv'
    if not path.is_file():raise FileNotFoundError(path)
    df=pd.read_csv(path,low_memory=False)
    expected={'period','date_local','location_id','sensor_id','pm25_mean','n_valid_hours','usable_daily'}
    if not expected.issubset(df.columns):raise ValueError(f'PM25 missing columns: {expected-set(df.columns)}')
    df['pm25_mean']=pd.to_numeric(df.pm25_mean,errors='coerce')
    df['n_valid_hours']=pd.to_numeric(df.n_valid_hours,errors='coerce')
    yes=df.usable_daily.astype(str).str.lower().isin(['true','1','yes'])
    good=df[yes&(df.n_valid_hours>=min_hours)&df.pm25_mean.ge(0)].copy()
    if good.duplicated(['sensor_id','date_local']).any():raise ValueError('Duplicate PM25 sensor/date')
    perloc=good.groupby(['period','date_local','location_id'],as_index=False).agg(pm25_mean=('pm25_mean','mean'),n_sensors=('sensor_id','nunique'))
    perloc.rename(columns={'date_local':'date'},inplace=True)
    daily=perloc.groupby(['period','date'],as_index=False).agg(pm25_hanoi=('pm25_mean','mean'),pm25_station_count=('location_id','nunique'))
    daily=calendar().merge(daily,on=['period','date'],how='left')
    daily['pm25_station_count']=daily.pm25_station_count.fillna(0).astype(int)
    save_csv(perloc,out/'01_Daily_Dataset'/'pm25_daily_station.csv')
    save_csv(daily,out/'01_Daily_Dataset'/'pm25_daily_hanoi.csv')
    save_json({'raw_day_sensor_rows':len(df),'valid_day_sensor_rows':len(good),'valid_day_location_rows':len(perloc),'minimum_distinct_hours':min_hours,'days_with_any_station':int(daily.pm25_hanoi.notna().sum()),'warning':'Mean of available locations; geographic representativeness not established'},out/'06_Quality_Reports'/'pm25_audit.json')
    return daily,perloc


def build_aod(base,s3,out,min_pixels=5):
    boundary=base/'04_Spatial'/'provinces.geojson'
    provinces=gpd.read_file(boundary)
    hanoi=hanoi_polygon(provinces)
    paths=sorted((base/'02_AOD'/'Daily').glob('AOD_055_????-??-??.tif'))
    if len(paths)!=122:raise RuntimeError(f'Expected 122 AOD daily rasters, got {len(paths)}')
    rows=[];mask_cache={}
    for path in paths:
        day=path.stem.replace('AOD_055_','')
        with rasterio.open(path) as src:
            key=(str(src.crs),tuple(src.transform),src.shape)
            if key not in mask_cache:
                geom=hanoi.to_crs(src.crs).geometry
                mask_cache[key]=geometry_mask(geom,out_shape=src.shape,transform=src.transform,invert=True,all_touched=False)
            inside=mask_cache[key]
            total=int(inside.sum())
            if total==0:raise ValueError('Hanoi boundary covers no AOD pixel')
            data=src.read(1,masked=True).astype('float32').filled(np.nan)
            valid=inside&np.isfinite(data)
            count=int(valid.sum());coverage=100*count/total
            source_mean=float(np.mean(data[valid])) if count>=min_pixels else np.nan
        estimate_path=s3/'05_AOD_Interpolation'/f'AOD_temporal_{day}.tif'
        provenance_path=s3/'05_AOD_Interpolation'/f'provenance_{day}.tif'
        estimate_mean=np.nan;estimate_count=0
        if estimate_path.is_file() and provenance_path.is_file():
            with rasterio.open(estimate_path) as es, rasterio.open(provenance_path) as ps:
                if es.shape!=inside.shape or ps.shape!=inside.shape or es.transform!=src_transform_from_key(key):
                    raise ValueError(f'Interpolation grid mismatch: {day}')
                filled=es.read(1,masked=True).astype('float32').filled(np.nan)
                provenance=ps.read(1)
                if np.any(inside&valid&(provenance!=1)):raise ValueError(f'Original pixels not preserved in provenance for {day}')
                if np.any(inside&(provenance==2)&valid):raise ValueError(f'Estimated pixels overwrite original pixels for {day}')
                combined=inside&np.isfinite(filled)&np.isin(provenance,[1,2])
                estimate_count=int((inside&(provenance==2)).sum())
                if combined.sum()>=min_pixels:estimate_mean=float(np.mean(filled[combined]))
        rows.append({'date':day,'aod_original_hanoi':source_mean,'aod_filled_hanoi':estimate_mean,'aod_coverage_pct':coverage,'aod_valid_pixels':count,'aod_hanoi_pixels':total,'aod_interpolated_pixels':estimate_count,'aod_meets_min_pixels':count>=min_pixels})
    outdf=calendar().merge(pd.DataFrame(rows),on='date',how='left')
    if outdf.aod_valid_pixels.isna().any():raise ValueError('Missing AOD nominal days')
    save_csv(outdf,out/'01_Daily_Dataset'/'aod_daily_hanoi.csv')
    save_json({'days':len(outdf),'days_with_original_value':int(outdf.aod_original_hanoi.notna().sum()),'days_with_filled_value':int(outdf.aod_filled_hanoi.notna().sum()),'min_source_pixels':min_pixels,'date_note':'NASA nominal UTC filename day, not a pixel-level timezone conversion','coverage_note':'Denominator is geographic grid cells with centers inside Hanoi; not valid satellite retrieval count'},out/'06_Quality_Reports'/'aod_audit.json')
    return outdf

def src_transform_from_key(key):
    from affine import Affine
    return Affine(*key[1][:6])


def build(base,s3,out,min_hours=18,min_pixels=5):
    fire=build_fire(s3,out)
    pm,stations=build_pm(base,out,min_hours)
    aod=build_aod(base,s3,out,min_pixels)
    combined=fire.merge(pm,on=['period','date']).merge(aod.drop(columns=['period']),on='date',validate='one_to_one')
    if len(combined)!=122 or combined.duplicated(['period','date']).any():raise ValueError('Merged daily dataset is not exactly 122 unique days')
    save_csv(combined,out/'01_Daily_Dataset'/'daily_analysis_dataset.csv')
    save_json({'daily_rows':len(combined),'fire_total':int(combined.fire_rrd.sum()),'days_pm25':int(combined.pm25_hanoi.notna().sum()),'days_aod_original':int(combined.aod_original_hanoi.notna().sum()),'days_three_sources':int((combined.pm25_hanoi.notna()&combined.aod_original_hanoi.notna()).sum())},out/'06_Quality_Reports'/'input_audit.json')
    return combined,stations
