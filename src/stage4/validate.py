import numpy as np
import pandas as pd
from .core import save_csv,save_json
from .analyze import pairs

def run(dataset,results,out):
    rows=[]
    def check(name,valid,detail):rows.append({'test':name,'status':'PASS' if valid else 'FAIL','detail':str(detail)})
    check('122 calendar days',len(dataset)==122,len(dataset))
    check('Unique season/calendar date',not dataset.duplicated(['period','date']).any(),'duplicate rows')
    check('Total Cropland events',dataset.fire_rrd.sum()==122,int(dataset.fire_rrd.sum()))
    check('Fire regional partition',bool((dataset.fire_rrd==dataset.fire_hanoi+dataset.fire_surrounding).all()),'RRD = Hanoi + surrounding')
    check('No negative Cropland detections',bool(dataset.fire_rrd.ge(0).all()),'counts >=0')
    check('PM25 nonnegative or missing',bool(dataset.pm25_hanoi.dropna().ge(0).all()),'PM25')
    check('AOD coverage in 0..100',bool(dataset.aod_coverage_pct.between(0,100).all()),'AOD grid coverage')
    check('AOD missing when insufficient source pixels',bool(dataset.loc[dataset.aod_valid_pixels<5,'aod_original_hanoi'].isna().all()),'AOD pixel threshold')
    check('Main correlations have 60 rows',len(results)==60,len(results))
    values=pd.concat([results.pearson_r,results.spearman_rho],ignore_index=True).dropna()
    check('Correlations bounded',bool(values.between(-1.000001,1.000001).all()),'[-1,1]')
    check('No unjustified statistics',bool(results.loc[results.status!='OK','pearson_r'].isna().all()),'no coefficient when n insufficient')
    # Regression guard: lag must never accidentally pair end of May-June with Oct-Nov.
    p=pairs(dataset,'fire_rrd','pm25_hanoi',3)
    check('Lag pairs within seasons',bool(all((pd.Timestamp(d)+pd.Timedelta(days=3)).strftime('%Y-%m-%d')<=('2025-06-30' if s=='May_Jun_2025' else '2025-11-30') for s,d in zip(p.period,p.date))),f'lag=3, pairs={len(p)}')
    table=pd.DataFrame(rows);save_csv(table,out/'06_Quality_Reports'/'stage4_validation_checks.csv')
    counts=table.status.value_counts().to_dict();state='PASS' if not counts.get('FAIL',0) else 'FAIL'
    output={'status':state,'counts':counts,'checks':rows,'scientific_warnings':['Association not causation','Nominal UTC AOD vs local day','AOD often absent: report n per pair','Multiple tests + autocorrelation','Uneven PM25 station availability']}
    save_json(output,out/'06_Quality_Reports'/'stage4_validation.json')
    if state!='PASS':raise RuntimeError(f'Stage4 validation FAIL; see {out}/06_Quality_Reports/stage4_validation.json')
    return {'status':state,'counts':counts}
