"""Spatial block masking validation of temporal AOD; no changes to original rasters."""
from pathlib import Path
import numpy as np
import pandas as pd
from .core import PERIODS,csv,js


def _read(path):
    import rasterio
    with rasterio.open(path) as ds:
        a=ds.read(1,masked=True).astype('float32').filled(np.nan)
        if ds.nodata is not None:a[a==ds.nodata]=np.nan
        a[~np.isfinite(a)]=np.nan
        return a,ds.shape,ds.transform,ds.crs

def temporal_prediction(prev,next_,weight=0.5):
    pred=np.full(prev.shape,np.nan,dtype=np.float32)
    ok=np.isfinite(prev)&np.isfinite(next_)
    pred[ok]=prev[ok]*(1-weight)+next_[ok]*weight
    return pred

def run(root,out,max_days=12,block_size=8,seed=42):
    daily=root/'02_Data_Preprocessing'/'02_AOD'/'Daily';files={p.stem[-10:]:p for p in daily.glob('AOD_055_????-??-??.tif')}
    if len(files)<100:raise FileNotFoundError(f'Need original daily AOD raster (~122), found {len(files)} at {daily}')
    rng=np.random.default_rng(seed);records=[];sampled=0;eligible=0
    for period,(start,end) in PERIODS.items():
        dates=pd.date_range(start,end);candidate=[]
        for day in dates[1:-1]:
            d=day.strftime('%Y-%m-%d');p=(day-pd.Timedelta(days=1)).strftime('%Y-%m-%d');n=(day+pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            if all(k in files for k in (p,d,n)):candidate.append((p,d,n))
        # Deterministic selection, enough days to span both seasons; avoid unconstrained memory use.
        candidate=[candidate[i] for i in rng.permutation(len(candidate))]
        selected=0
        for prev,now,nxt in candidate:
            if selected>=max_days//2:break
            truth,shape,transform,crs=_read(files[now]);a,_,_,_=_read(files[prev]);b,_,_,_=_read(files[nxt]);
            if truth.shape!=a.shape or truth.shape!=b.shape:continue
            both=np.isfinite(a)&np.isfinite(b)&np.isfinite(truth)
            # Sample contiguous 8x8 grid blocks with a minimum number of reference pixels.
            centers=np.argwhere(both)
            if len(centers)<30:continue
            eligible+=1;points=[]
            for center in centers[rng.permutation(len(centers))[:min(300,len(centers))]]:
                rr,cc=(center//block_size)*block_size
                region=both[rr:rr+block_size,cc:cc+block_size]
                if int(region.sum())>=min(8,block_size):
                    loc=np.argwhere(region);points=[(rr+int(u),cc+int(v)) for u,v in loc];break
            if not points:continue
            rows,cols=np.array(points).T; y=truth[rows,cols];estimated=(a[rows,cols]+b[rows,cols])/2
            baseline=a[rows,cols];
            for method,pred in [('temporal_symmetric_1day',estimated),('previous_day_baseline',baseline)]:
                err=pred-y
                records.append({'period':period,'date':now,'method':method,'masked_block_size':block_size,
                                'n_test_pixels':len(y),'mae':float(np.mean(np.abs(err))),
                                'rmse':float(np.sqrt(np.mean(err*err))),'bias':float(np.mean(err))})
            selected+=1;sampled+=1
    frame=pd.DataFrame(records,columns=['period','date','method','masked_block_size','n_test_pixels','mae','rmse','bias'])
    csv(frame,out/'02_AOD_Evaluation'/'aod_block_holdout_per_day.csv')
    summary=[]
    for method,g in frame.groupby('method'):
        # Aggregating day metrics weighted by tested pixels; RMSE needs squared weighting.
        n=g.n_test_pixels.to_numpy(float);summary.append({'method':method,'days':len(g),'tested_pixels':int(n.sum()),
          'mae':float(np.average(g.mae,weights=n)),'rmse':float(np.sqrt(np.average(g.rmse**2,weights=n))),
          'bias':float(np.average(g.bias,weights=n))})
    csv(pd.DataFrame(summary,columns=['method','days','tested_pixels','mae','rmse','bias']),out/'02_AOD_Evaluation'/'aod_block_holdout_summary.csv')
    audit={'days_evaluated':sampled,'candidate_days_reaching_min_pixels':eligible,'original_daily_rasters':len(files),
      'block_size_pixels':block_size,'evaluation':'masked spatial block, one day in time, symmetric prev/next',
      'limitations':'Synthetic masked blocks only where target and both neighboring days are observed; not a realistic long cloud gap, not a spatial interpolation benchmark. Pixels in same block are spatially dependent.'}
    js(audit,out/'05_Quality_Reports'/'aod_block_audit.json')
    return audit
