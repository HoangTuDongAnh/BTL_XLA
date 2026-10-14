import pandas as pd
import numpy as np
import rasterio
from .core import save_csv,save_json,weekly_key

def run(base,out):
    src=base/'01_VIIRS';rasters=sorted((base/'04_Spatial').glob('*_Map_region.tif'))
    if len(rasters)!=3:raise RuntimeError(f'Cần 3 WorldCover Map_region.tif, hiện có {len(rasters)}')
    names=('viirs_May_Jun_2025.csv','viirs_Oct_Nov_2025.csv')
    csvs=[src/name for name in names]
    missing=[name for name,path in zip(names,csvs) if not path.is_file()]
    if missing:raise FileNotFoundError(f'Thiếu CSV VIIRS đã chuẩn hóa: {missing}; thư mục: {src}')
    ds=[rasterio.open(x) for x in rasters]
    try:
        frames=[]
        for f in csvs:
            df=pd.read_csv(f,low_memory=False);period=f.stem.removeprefix('viirs_')
            if 'date_local' not in df or not {'longitude','latitude'}.issubset(df):raise ValueError('VIIRS thiếu date_local/longitude/latitude')
            df['period']=period
            frames.append(df)
        df=pd.concat(frames,ignore_index=True)
        land=np.full(len(df),-1,dtype=np.int16);hits=np.zeros(len(df),dtype=np.int8)
        lon=pd.to_numeric(df.longitude,errors='coerce').to_numpy();lat=pd.to_numeric(df.latitude,errors='coerce').to_numpy()
        valid=np.isfinite(lon)&np.isfinite(lat)
        for source in ds:
            if source.crs.to_epsg()!=4326:raise ValueError(f'WorldCover CRS phải EPSG:4326: {source.name}')
            left,bottom,right,top=source.bounds
            ids=np.flatnonzero(valid&(lon>=left)&(lon<right)&(lat>bottom)&(lat<=top))
            if len(ids)==0:continue
            vals=list(source.sample(zip(lon[ids],lat[ids]),masked=True))
            for idx, val in zip(ids,vals):
                if np.ma.is_masked(val[0]):continue
                v=int(val[0]);
                if v==0:continue
                if hits[idx]:
                    if land[idx]!=v:raise RuntimeError(f'WorldCover tiles disagree at point {idx}')
                    continue
                land[idx]=v;hits[idx]=1
        df['worldcover_code']=pd.Series(land).replace(-1,pd.NA).astype('Int64')
        df['land_class']=np.select([land==40,land>=0],['Cropland','Non-Cropland'],default='NoData_or_Outside')
        weeks=df.apply(lambda row:weekly_key(row['date_local'],row['period']),axis=1)
        df['week_id']=[v[0] if v else '' for v in weeks]
        target=out/'01_Cropland_Overlay';save_csv(target/'viirs_cropland_overlay.csv',df)
        summary=df.groupby(['period','land_class'],dropna=False).size().reset_index(name='detections');save_csv(target/'overlay_summary.csv',summary)
        metadata={'total':len(df),'cropland':int((land==40).sum()),'non_cropland':int(((land>=0)&(land!=40)).sum()),'unknown':int((land<0).sum()),'input_csvs':[p.name for p in csvs],'land_rasters':[p.name for p in rasters],'worldcover_year':2021,'viirs_year':2025,'note':'Cropland hotspot is not proof of rice-straw burning.'}
        save_json(target/'overlay_status.json',metadata)
        return metadata
    finally:
        for source in ds:source.close()
