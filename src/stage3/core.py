from pathlib import Path
import json, csv
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

PERIODS={'May_Jun_2025':('2025-05-01','2025-06-30'),'Oct_Nov_2025':('2025-10-01','2025-11-30')}

def project(root):
    root=Path(root).resolve(); base=root/'02_Data_Preprocessing';out=root/'03_Image_Processing'
    if not base.exists():raise FileNotFoundError(f'Không có output Công đoạn 2: {base}')
    out.mkdir(parents=True,exist_ok=True)
    return base,out

def save_json(path, obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def save_csv(path,df):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(path,index=False,encoding='utf-8-sig')

def weekly_key(d,period):
    start=pd.Timestamp(PERIODS[period][0]);day=pd.Timestamp(str(d)[:10]);
    if day<start or day>pd.Timestamp(PERIODS[period][1]):return None
    k=(day-start).days//7
    return f'{period}_W{k+1:02d}',k,start+pd.Timedelta(days=k*7)

def tiff(path,arr,transform,crs,nodata, dtype=None):
    arr=np.asarray(arr);dtype=dtype or str(arr.dtype)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with rasterio.open(path,'w',driver='GTiff',width=arr.shape[1],height=arr.shape[0],count=1,crs=crs,transform=transform,dtype=dtype,nodata=nodata,compress='deflate',predictor=3 if np.dtype(dtype).kind=='f' else 2,tiled=True,blockxsize=256,blockysize=256) as dst:dst.write(arr.astype(dtype),1)

def aod_files(base):
    folder=base/'02_AOD'/'Daily'
    files=sorted(folder.glob('AOD_055_????-??-??.tif'))
    if not files:raise FileNotFoundError(f'Không thấy GeoTIFF AOD: {folder}')
    return files
