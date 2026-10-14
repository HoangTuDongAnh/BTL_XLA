import json
import pandas as pd
import numpy as np
import rasterio
from .core import save_json,save_csv,PERIODS

def run(base,out):
    checks=[]
    def check(name,pass_,detail,warn=False):checks.append({'test':name,'status':'PASS' if pass_ else ('WARN' if warn else 'FAIL'),'detail':str(detail)})
    overlay=out/'01_Cropland_Overlay'/'viirs_cropland_overlay.csv'
    check('overlay CSV exists',overlay.exists(),overlay)
    if overlay.exists():
        df=pd.read_csv(overlay);check('VIIRS 1068 observations',len(df)==1068,len(df),warn=True)
        check('VIIRS land classes populated',df.land_class.notna().all() and df.land_class.isin(['Cropland','Non-Cropland','NoData_or_Outside']).all(),df.land_class.value_counts().to_dict())
        check('All VIIRS assigned valid week',df.week_id.notna().all() and df.week_id.astype(str).str.len().gt(0).all(),int(df.week_id.isna().sum()))
        summary=json.loads((out/'01_Cropland_Overlay'/'overlay_status.json').read_text(encoding='utf-8'))
        check('Overlay class reconciliation',summary['cropland']+summary['non_cropland']+summary['unknown']==len(df),summary)
    dens=out/'02_Fire_Density'/'density_quality.csv';check('Density quality exists',dens.exists(),dens)
    if dens.exists():
        d=pd.read_csv(dens);check('Raster point counts reconciled',bool((d.input_cropland_points==d.raster_sum).all()),int((d.input_cropland_points-d.raster_sum).abs().sum()))
        if overlay.exists():check('All Cropland records represented in density',int(d.raster_sum.sum())==int((df.land_class=='Cropland').sum()),int(d.raster_sum.sum()))
    q=out/'04_AOD_Weekly'/'weekly_quality.csv';check('AOD weekly quality exists',q.exists(),q)
    if q.exists():
        x=pd.read_csv(q);check('AOD days exactly 122',int(x.days_in_group.sum())==122,int(x.days_in_group.sum()))
        check('AOD coverage within range',bool(x.coverage_pct.between(0,100).all()),[float(x.coverage_pct.min()),float(x.coverage_pct.max())])
        check('Weekly rasters pairs',len(list((out/'04_AOD_Weekly').glob('AOD_weekly_*.tif')))==len(x) and len(list((out/'04_AOD_Weekly').glob('valid_day_count_*.tif')))==len(x),len(x))
    interp=out/'05_AOD_Interpolation'/'interpolation_daily_quality.csv';check('Interpolated AOD report exists',interp.exists(),interp)
    if interp.exists():
        x=pd.read_csv(interp);check('Interpolation 122 days',len(x)==122,len(x))
        check('Interpolated 122 TIFFs',len(list((out/'05_AOD_Interpolation').glob('AOD_temporal_*.tif')))==122,122)
        check('Provenance 122 TIFFs',len(list((out/'05_AOD_Interpolation').glob('provenance_*.tif')))==122,122)
        metrics=json.loads((out/'05_AOD_Interpolation'/'interpolation_validation.json').read_text(encoding='utf-8'))
        check('Holdout has evaluated pixels',metrics['holdout_predicted_pixels']>0,metrics['holdout_predicted_pixels'],warn=True)
    status='FAIL' if any(c['status']=='FAIL' for c in checks) else ('PASS_WITH_WARNINGS' if any(c['status']=='WARN' for c in checks) else 'PASS')
    report={'status':status,'counts':{s:sum(c['status']==s for c in checks) for s in ['PASS','WARN','FAIL']},'checks':checks,'scientific_warnings':['AOD dates are nominal NASA UTC dates, VIIRS uses UTC+7 local date; not identical acquisition-time clock','Interpolated AOD is model-estimated, not measured; preserve provenance','2021 WorldCover vs 2025 VIIRS, Cropland detection is not direct evidence of rice-straw burning','Low AOD coverage strict QA; weekly means are valid-pixel only']}
    target=out/'07_Quality_Reports';save_json(target/'stage3_validation.json',report);save_csv(target/'stage3_validation_checks.csv',pd.DataFrame(checks))
    return report
