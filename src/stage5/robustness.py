"""Exploratory time-series robustness. Do not interpret results as causal evidence."""
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from .core import csv,js


def paired(frame,x,y,lag):
    # Exact calendar join prevents lag across season boundaries and missing-day compression.
    a=frame[['period','date',x]].copy()
    b=frame[['period','date',y]].copy()
    b['date']=(pd.to_datetime(b['date'])-pd.Timedelta(days=int(lag))).dt.strftime('%Y-%m-%d')
    m=a.merge(b,on=['period','date'],validate='one_to_one').sort_values(['period','date'])
    return m.replace([np.inf,-np.inf],np.nan).dropna(subset=[x,y]).reset_index(drop=True)

def corr(x,y):
    if len(x)<8 or np.std(x)==0 or np.std(y)==0:return np.nan
    return float(np.corrcoef(x,y)[0,1])

def block_bootstrap(x,y,block=7,reps=1200,seed=42):
    """Paired moving-block bootstrap, resamples contiguous *matched* rows (not full calendar days)."""
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float);n=len(x)
    if n<16:return np.array([])
    block=min(block,max(2,n//4));rng=np.random.default_rng(seed)
    starts=np.arange(n-block+1);result=[]
    for _ in range(reps):
        ix=np.concatenate([np.arange(s,s+block) for s in rng.choice(starts,size=int(np.ceil(n/block)))])[:n]
        val=corr(x[ix],y[ix]);
        if np.isfinite(val):result.append(val)
    return np.asarray(result)

def circular_shift_test(x,y,min_shift=7):
    """Full regular calendar vectors only: preserve NaNs and seasonal alignment while rolling y."""
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float);n=len(x)
    m=np.isfinite(x)&np.isfinite(y);obs=corr(x[m],y[m]);null=[]
    for shift in range(min_shift,n-min_shift+1):
        shifted=np.roll(y,shift);m=np.isfinite(x)&np.isfinite(shifted)
        r=corr(x[m],shifted[m]);
        if np.isfinite(r):null.append(r)
    p=(1+sum(abs(v)>=abs(obs) for v in null))/(1+len(null)) if len(null)>=10 and np.isfinite(obs) else np.nan
    return obs,p,len(null)

def run(data,out,reps=1200,block=7,seed=42):
    rows=[];boot=[];shifts=[];stability=[]
    specs=[('fire_pm25','fire_rrd','pm25_hanoi'),('fire_aod','fire_rrd','aod_original_hanoi'),('aod_pm25','aod_original_hanoi','pm25_hanoi')]
    for season in ('May_Jun_2025','Oct_Nov_2025'):
        subset=data[data.period==season].sort_values('date').copy()
        for comparison,x,y in specs:
            lagvals=[]
            for lag in range(4):
                pairs=paired(subset,x,y,lag);n=len(pairs);r=corr(pairs[x],pairs[y]);lagvals.append((lag,r))
                # Observed overlapping matched rows need not be calendar-contiguous; caveat stored.
                bs=block_bootstrap(pairs[x],pairs[y],block=block,reps=reps,seed=seed+lag)
                low,high=(map(float,np.quantile(bs,[.025,.975])) if len(bs)>=100 else (np.nan,np.nan))
                rows.append({'season':season,'comparison':comparison,'lag_days':lag,'n_pairs':n,'pearson_r':r,
                             'ci_95_low':low,'ci_95_high':high,'bootstrap_valid_reps':len(bs),
                             'block_matched_rows':block,'ci_excludes_zero':bool(low>0 or high<0) if np.isfinite(low) else False})
                # Store compact bootstrap quantiles, never thousands of rows in review package.
                boot.append({'season':season,'comparison':comparison,'lag_days':lag,'bootstrap_median':float(np.median(bs)) if len(bs) else np.nan,'q025':low,'q975':high})
                # Test shift on calendar series: construct Y(t+lag) explicitly, no shift across season.
                calendar=subset[['date',x]].copy().sort_values('date')
                target=subset[['date',y]].copy();target['date']=(pd.to_datetime(target.date)-pd.Timedelta(days=lag)).dt.strftime('%Y-%m-%d')
                calendar=calendar.merge(target,on='date',how='left',validate='one_to_one')
                ob,p,num=circular_shift_test(calendar[x],calendar[y])
                shifts.append({'season':season,'comparison':comparison,'lag_days':lag,'r_calendar':ob,'shift_p_two_sided':p,'null_shifts':num})
            valid=[(lag,r) for lag,r in lagvals if np.isfinite(r)]
            if valid:
                best=max(valid,key=lambda z:abs(z[1]));stability.append({'season':season,'comparison':comparison,'max_abs_lag':best[0],'max_abs_r':best[1],'note':'selection over 4 lags; exploratory'})
    csv(pd.DataFrame(rows),out/'01_Robustness'/'bootstrap_ci.csv')
    csv(pd.DataFrame(boot),out/'01_Robustness'/'bootstrap_quantiles.csv')
    csv(pd.DataFrame(shifts),out/'01_Robustness'/'circular_shift_tests.csv')
    csv(pd.DataFrame(stability),out/'01_Robustness'/'lag_stability.csv')
    summary={'evaluated_correlations':len(rows),'bootstrap_reps':reps,'bootstrap_block_matched_rows':block,
      'circular_shift_test':'within-season full-calendar circular shifts excluding close shifts, exploratory; null shifts not independent',
      'bootstrap_caveat':'matched-pair block bootstrap compresses missing dates, particularly for AOD; interpret AOD intervals cautiously',
      'multiple_lag_caveat':'best lag selected post hoc; no familywise correction for bootstrap/shift procedures',
      'causal_claim':False}
    js(summary,out/'05_Quality_Reports'/'robustness_audit.json')
    return summary
