from pathlib import Path
import json
import pandas as pd

PERIODS = {'May_Jun_2025': ('2025-05-01','2025-06-30'), 'Oct_Nov_2025': ('2025-10-01','2025-11-30')}

def locations(root):
    root = Path(root).resolve()
    base = root / '02_Data_Preprocessing'
    stage3 = root / '03_Image_Processing'
    output = root / '04_Correlation_Analysis'
    for p in (base,stage3):
        if not p.is_dir(): raise FileNotFoundError(f'Missing required stage output: {p}')
    output.mkdir(parents=True, exist_ok=True)
    return base,stage3,output

def save_csv(df,path):
    path = Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(path,index=False,encoding='utf-8-sig')

def save_json(value,path):
    path = Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def calendar():
    pieces=[]
    for period,(start,end) in PERIODS.items():
        pieces.append(pd.DataFrame({'period':period,'date':pd.date_range(start,end).strftime('%Y-%m-%d')}))
    return pd.concat(pieces,ignore_index=True)
