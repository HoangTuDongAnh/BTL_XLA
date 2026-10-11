import json, csv, re
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

PERIODS={'May_Jun_2025':('2025-05-01','2025-06-30'),'Oct_Nov_2025':('2025-10-01','2025-11-30')}

def context(root):
    root=Path(root).resolve(); raw=root/'DATARAW'; out=root/'02_Data_Preprocessing'
    groups={'viirs':'01_VIIRS_Fire','aod':'02_MODIS_MAIAC_AOD','pm25':'03_OpenAQ_PM25','worldcover':'04_ESA_WorldCover','boundary':'05_GADM_Boundary'}
    if not raw.is_dir(): raise FileNotFoundError(f'Không tìm thấy {raw}')
    out.mkdir(parents=True,exist_ok=True)
    return root,raw,out,{k:raw/v for k,v in groups.items()}

def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def write_csv(path,rows,columns=None):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(rows,pd.DataFrame): rows.to_csv(p,index=False,encoding='utf-8-sig');return
    rows=list(rows); columns=columns or (list(rows[0]) if rows else ['status'])
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(rows)

def period_of(dt):
    for k,(start,end) in PERIODS.items():
        if pd.Timestamp(start)<=pd.Timestamp(dt).normalize()<=pd.Timestamp(end):return k
    return None
