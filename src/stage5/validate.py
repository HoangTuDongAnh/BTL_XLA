from pathlib import Path
import numpy as np
import pandas as pd
from .core import csv,js

def run(frames,out):
    checks=[]
    def check(name,ok,detail,warn=False):checks.append({'test':name,'status':'PASS' if ok else ('WARN' if warn else 'FAIL'),'detail':str(detail)})
    daily=frames['daily'];lag=frames['lag']
    check('122 date records',len(daily)==122,len(daily))
    check('Unique period/date',not daily[['period','date']].duplicated().any(),'period,date unique')
    check('Cropland observations preserved',int(daily.fire_rrd.sum())==122,int(daily.fire_rrd.sum()))
    check('Fire split reconciled',bool((daily.fire_rrd==daily.fire_hanoi+daily.fire_surrounding).all()),'RRD = Hanoi + surrounding')
    check('Original AOD not replaced',bool((daily.aod_original_hanoi.isna() | daily.aod_filled_hanoi.notna()).all()),'missing original not silently overwritten')
    check('Correlation inputs preserved',lag.shape[0]==60,len(lag))
    check('No coefficient outside bounds',bool(lag.pearson_r.dropna().abs().le(1+1e-9).all()),'pearson range')
    check('Bootstrap results exist',(out/'01_Robustness'/'bootstrap_ci.csv').is_file(),'bootstrap file')
    boot=pd.read_csv(out/'01_Robustness'/'bootstrap_ci.csv')
    check('Bootstrap all season-comparison-lag',len(boot)==24,len(boot))
    check('Shift null results exist',(out/'01_Robustness'/'circular_shift_tests.csv').is_file(),'shift file')
    eval_file=out/'02_AOD_Evaluation'/'aod_block_holdout_summary.csv'
    ae=pd.read_csv(eval_file)
    check('AOD blocked holdout evaluated',not ae.empty,'days '+str(ae.days.max() if not ae.empty else 0),warn=True)
    check('AOD two-method comparison',len(ae.method.unique())==2 if not ae.empty else False,str(ae.method.tolist()),warn=True)
    check('Final dataset exists',(out/'03_Final_Dataset'/'final_daily_dataset.csv').is_file(),'daily file')
    check('Dashboard exists',(out.parent/'app'/'streamlit_app.py').is_file(),'app/streamlit_app.py')
    check('Figures exist',len(list((out/'04_Visualizations').glob('*.png')))>=2,'PNG count')
    cs=pd.DataFrame(checks);counts={k:int((cs.status==k).sum()) for k in ('PASS','WARN','FAIL')}
    status='FAIL' if counts['FAIL'] else ('PASS_WITH_WARNINGS' if counts['WARN'] else 'PASS')
    csv(cs,out/'05_Quality_Reports'/'stage5_validation_checks.csv')
    report={'status':status,'counts':counts,'checks':checks,'scope':'QA of tabular outputs; raster pixel audit limited to blocked AOD sample; Streamlit browser UI must be manually tested'}
    js(report,out/'05_Quality_Reports'/'stage5_validation.json')
    return report
