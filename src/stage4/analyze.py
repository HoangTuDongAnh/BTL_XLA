import numpy as np
import pandas as pd
from scipy.stats import pearsonr,spearmanr
from .core import PERIODS,save_csv,save_json

VARIABLES={
    'fire_pm25': ('fire_rrd','pm25_hanoi'),
    'fire_aod': ('fire_rrd','aod_original_hanoi'),
    'aod_pm25': ('aod_original_hanoi','pm25_hanoi'),
    'fire_pm25_hanoi': ('fire_hanoi','pm25_hanoi'),
    'fire_pm25_surrounding': ('fire_surrounding','pm25_hanoi'),
}

def pairs(df,xcol,ycol,lag):
    # Lag +k: X on calendar date t versus Y on calendar date t+k.
    # Strictly within the SAME season; merge on calendar dates, no position shift.
    x=df[['period','date',xcol]].copy()
    y=df[['period','date',ycol]].copy()
    y['date']=(pd.to_datetime(y.date)-pd.Timedelta(days=lag)).dt.strftime('%Y-%m-%d')
    merged=x.merge(y,on=['period','date'],how='inner',validate='one_to_one')
    return merged.replace([np.inf,-np.inf],np.nan).dropna(subset=[xcol,ycol])

def calculate(df,comparisons=VARIABLES,coverage=0,min_n=8):
    result=[]
    sub=df.copy()
    if coverage>0:
        aodcols={'aod_original_hanoi','aod_filled_hanoi'}
        for col in aodcols.intersection(sub.columns):sub.loc[sub.aod_coverage_pct<coverage,col]=np.nan
    for season in ['all',*PERIODS]:
        frame=sub if season=='all' else sub[sub.period==season]
        for name,(x,y) in comparisons.items():
            for lag in range(4):
                matches=pairs(frame,x,y,lag)
                n=len(matches);reason='OK'
                pr=sr=pp=sp=np.nan
                if n<min_n:reason='INSUFFICIENT_N'
                elif matches[x].nunique()<2 or matches[y].nunique()<2:reason='CONSTANT_VARIABLE'
                else:
                    pr,pp=map(float,pearsonr(matches[x],matches[y]))
                    sr,sp=map(float,spearmanr(matches[x],matches[y]))
                result.append({'season':season,'comparison':name,'x':x,'y':y,'lag_days':lag,'n_pairs':n,'pearson_r':pr,'pearson_p':pp,'spearman_rho':sr,'spearman_p':sp,'status':reason,'aod_min_coverage_pct':coverage})
    return pd.DataFrame(result)

def bh_adjust(frame,col):
    # Benjamini-Hochberg within the declared family, not across unrelated scenarios.
    p=pd.to_numeric(frame[col],errors='coerce').to_numpy(dtype=float)
    ok=np.flatnonzero(np.isfinite(p));out=np.full(len(p),np.nan)
    if not len(ok):return out
    ix=ok[np.argsort(p[ok])];m=len(ix)
    adjusted=np.minimum.accumulate((p[ix]*m/np.arange(1,m+1))[::-1])[::-1]
    out[ix]=np.minimum(adjusted,1.0)
    return out

def run(dataset,stations,out,min_n=8):
    # Main: nominal-day original AOD, coverage >0, >= 5 original pixels already required in Stage4 build.
    main=calculate(dataset,min_n=min_n)
    for col in ('pearson_p','spearman_p'):
        main[col+'_fdr_bh']=bh_adjust(main,col)
    save_csv(main,out/'02_Correlation'/'lag_correlation_results.csv')
    save_csv(main[main.lag_days.eq(0)],out/'02_Correlation'/'correlation_results.csv')
    # AOD source-only coverage thresholds are sensitivity analyses, not primary.
    alternatives=[]
    for cut in (5,10):
        t=calculate(dataset,comparisons={k:v for k,v in VARIABLES.items() if 'aod' in k},coverage=cut,min_n=min_n)
        t['scenario']=f'original_aod_coverage_ge_{cut}pct';alternatives.append(t)
    filled=calculate(dataset,comparisons={'fire_aod':('fire_rrd','aod_filled_hanoi'),'aod_pm25':('aod_filled_hanoi','pm25_hanoi')},min_n=min_n)
    filled['scenario']='interpolated_aod_sensitivity_only';alternatives.append(filled)
    for location,loc in stations.groupby('location_id'):
        joined=dataset.drop(columns=['pm25_hanoi']).merge(loc[['period','date','pm25_mean']],on=['period','date'],how='left')
        t=calculate(joined,comparisons={'fire_pm25':('fire_rrd','pm25_mean'),'aod_pm25':('aod_original_hanoi','pm25_mean')},min_n=min_n)
        t['scenario']=f'station_{location}';alternatives.append(t)
    sensitivity=pd.concat(alternatives,ignore_index=True)
    save_csv(sensitivity,out/'04_Sensitivity'/'sensitivity_results.csv')
    audit={'main_tests':len(main),'main_computable':int(main.status.eq('OK').sum()),'sensitivity_tests':len(sensitivity),'main_fdr_family':'all main comparisons x all seasons x all lags for each coefficient separately','warning':'Nominal UTC AOD days compared with local VIIRS/PM25 dates. Exploratory, not causal; naive p-values do not correct temporal autocorrelation.'}
    save_json(audit,out/'06_Quality_Reports'/'correlation_audit.json')
    return main,sensitivity,audit
