from pathlib import Path
import json
import pandas as pd

PERIODS={'May_Jun_2025':('2025-05-01','2025-06-30'),'Oct_Nov_2025':('2025-10-01','2025-11-30')}

def dirs(root):
    root=Path(root).resolve()
    for name in ('02_Data_Preprocessing','03_Image_Processing','04_Correlation_Analysis'):
        if not (root/name).is_dir():raise FileNotFoundError(f'Missing Stage 2/3/4 folder: {root/name}')
    output=root/'05_Final_Evaluation';output.mkdir(exist_ok=True)
    return root,output

def csv(df,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(path,index=False,encoding='utf-8-sig')

def js(x,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def load(root):
    s3=root/'03_Image_Processing';s4=root/'04_Correlation_Analysis'
    paths={
      'daily':s4/'01_Daily_Dataset'/'daily_analysis_dataset.csv',
      'stations':s4/'01_Daily_Dataset'/'pm25_daily_station.csv',
      'lag':s4/'02_Correlation'/'lag_correlation_results.csv',
      'sensitivity':s4/'04_Sensitivity'/'sensitivity_results.csv',
      'fire':s3/'03_Fire_Statistics'/'fire_by_province_week_class.csv',
      'aod_weekly':s3/'04_AOD_Weekly'/'weekly_quality.csv',
      'aod_interp':s3/'05_AOD_Interpolation'/'interpolation_validation.json',
    }
    missing=[str(p) for p in paths.values() if not p.is_file()]
    if missing:raise FileNotFoundError('Missing required Stage 3/4 outputs:\n'+'\n'.join(missing))
    frames={k:pd.read_csv(p) for k,p in paths.items() if p.suffix=='.csv'}
    frames['aod_interp']=json.loads(paths['aod_interp'].read_text(encoding='utf-8'))
    return frames,paths
