import re
import pandas as pd
from .common import write_csv,write_json,period_of

def get_time(df):
    for col in ['datetime_utc','datetime','date.utc','date_utc','period.datetimeFrom.utc','period_datetimeFrom_utc','datetimeFrom','date']:
        if col in df:
            s=df[col]
            if col=='date' and len(s) and str(s.iloc[0]).startswith('{'):
                import ast
                s=s.map(lambda x:ast.literal_eval(x).get('utc') if pd.notna(x) else None)
            return pd.to_datetime(s,utc=True,errors='coerce')
    raise ValueError('Không tìm thấy cột thời gian: '+str(df.columns.tolist()))

def run(groups,out,min_hours=18):
    src=groups['pm25'];target=out/'03_PM25';target.mkdir(parents=True,exist_ok=True)
    files=sorted(src.rglob('location_*_sensor_*.csv'))
    if not files:raise RuntimeError('Không có file location_*_sensor_*.csv')
    reports=[]; hourly=[]
    for f in files:
        df=pd.read_csv(f,low_memory=False)
        if df.empty:
            reports.append({'file':f.name,'rows':0,'valid':0,'warning':'empty'});continue
        try: stamp=get_time(df)
        except Exception as e:reports.append({'file':f.name,'rows':len(df),'valid':0,'warning':str(e)});continue
        valcol=next((x for x in ['value','pm25','pm2_5','concentration'] if x in df),None)
        if valcol is None:reports.append({'file':f.name,'rows':len(df),'valid':0,'warning':'missing value'});continue
        value=pd.to_numeric(df[valcol],errors='coerce'); valid=stamp.notna()&value.notna()&(value>=0)
        ids=re.search(r'location_(\d+)_sensor_(\d+)',f.name)
        location,sensor=ids.groups() if ids else ('unknown','unknown')
        data=pd.DataFrame({'location_id':location,'sensor_id':sensor,'time_utc':stamp[valid],'value_ugm3':value[valid]})
        data=data.drop_duplicates(['sensor_id','time_utc']).sort_values('time_utc')
        data['time_local']=data.time_utc.dt.tz_convert('Asia/Ho_Chi_Minh')
        data['date_local']=data.time_local.dt.strftime('%Y-%m-%d')
        data['period']=data.date_local.map(period_of)
        data=data[data.period.notna()]
        if not data.empty:hourly.append(data)
        reports.append({'file':f.name,'rows':len(df),'valid':len(data),'warning':'review_outliers' if (value>500).any() else ''})
    write_csv(target/'pm25_input_quality.csv',reports)
    if not hourly:raise RuntimeError('Không có timestamp/value PM2.5 hợp lệ. Xem pm25_input_quality.csv')
    allrows=pd.concat(hourly,ignore_index=True).drop_duplicates(['sensor_id','time_utc']).sort_values('time_utc')
    allrows['time_utc']=allrows.time_utc.dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    allrows['time_local']=allrows.time_local.dt.strftime('%Y-%m-%dT%H:%M:%S%z')
    write_csv(target/'pm25_hourly.csv',allrows)
    allrows['hour_local']=pd.to_datetime(allrows.time_local,utc=True).dt.tz_convert('Asia/Ho_Chi_Minh').dt.floor('h').astype(str)
    byhour=allrows.groupby(['location_id','sensor_id','period','date_local','hour_local'],as_index=False).agg(hourly_mean=('value_ugm3','mean'),n_source_records=('value_ugm3','size'))
    grouped=byhour.groupby(['location_id','sensor_id','period','date_local'],as_index=False).agg(pm25_mean=('hourly_mean','mean'),n_valid_hours=('hour_local','nunique'),n_observations=('n_source_records','sum'))
    grouped['usable_daily']=grouped.n_valid_hours>=min_hours
    write_csv(target/'pm25_daily.csv',grouped)
    write_json(target/'metadata.json',{'minimum_observations_per_day':min_hours,'daily_rule':'mean of unique local hourly means; minimum distinct local hours','no_automatic_outlier_deletion':True,'time_zone':'Asia/Ho_Chi_Minh'})
    return {'source_csv_files':len(files),'hourly_rows':len(allrows),'daily_rows':len(grouped),'usable_daily_rows':int(grouped.usable_daily.sum())}
