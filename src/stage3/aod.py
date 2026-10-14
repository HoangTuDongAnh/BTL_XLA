from collections import defaultdict
import numpy as np
import pandas as pd
import rasterio
from .core import aod_files,weekly_key,PERIODS,tiff,save_csv,save_json

def load_stack(base):
    files=aod_files(base);dates=[];arr=[];meta=None
    for file in files:
        date=file.stem.removeprefix('AOD_055_');dt=pd.Timestamp(date)
        with rasterio.open(file) as src:
            if meta is None:meta={'transform':src.transform,'crs':src.crs,'shape':src.shape,'nodata':src.nodata}
            elif (src.shape!=meta['shape'] or src.transform!=meta['transform'] or src.crs!=meta['crs']):raise RuntimeError(f'AOD not on same grid: {file.name}')
            a=src.read(1,masked=True).astype('float32').filled(np.nan)
            a[~np.isfinite(a)]=np.nan
            arr.append(a);dates.append(dt)
    return np.stack(arr),pd.DatetimeIndex(dates),meta

def weekly(base,out):
    data,dates,meta=load_stack(base)
    gr=defaultdict(list)
    for i,date in enumerate(dates):
        period=next((p for p,(start,end) in PERIODS.items() if pd.Timestamp(start)<=date<=pd.Timestamp(end)),None)
        if period:
            k=weekly_key(date.strftime('%Y-%m-%d'),period)
            gr[k[0]].append(i)
    rows=[]
    for week,indices in sorted(gr.items()):
        values=data[indices];valid=np.isfinite(values);count=valid.sum(axis=0).astype('uint8')
        summ=np.nansum(values,axis=0);mean=np.divide(summ,count,out=np.full_like(summ,np.nan,dtype='float32'),where=count>0)
        tiff(out/'04_AOD_Weekly'/f'AOD_weekly_{week}.tif',mean,meta['transform'],meta['crs'],np.nan,'float32')
        tiff(out/'04_AOD_Weekly'/f'valid_day_count_{week}.tif',count,meta['transform'],meta['crs'],0,'uint8')
        rows.append({'week_id':week,'days_in_group':len(indices),'pixels_any_valid':int((count>0).sum()),'mean_valid_days_per_cell':round(float(count.mean()),4),'coverage_pct':round(float((count>0).mean()*100),4)})
    save_csv(out/'04_AOD_Weekly'/'weekly_quality.csv',pd.DataFrame(rows))
    save_json(out/'04_AOD_Weekly'/'metadata.json',{'aggregation':'unweighted arithmetic mean of valid nominal-UTC daily rasters','no_gap_filling':True,'count_nodata_note':'count 0 is no valid observation, not missing count','weeks':'7-day bins anchored separately at May 1 and Oct 1; final bin may be shorter','periods':PERIODS})
    return {'weeks':len(rows),'valid_daily_rasters':len(dates),'mean_weekly_coverage_pct':round(float(np.mean([r['coverage_pct'] for r in rows])),3)}

def interpolation(base,out,max_gap=2,holdout_fraction=0.1,seed=42):
    data,dates,meta=load_stack(base);n,h,w=data.shape
    # Never bridge season boundaries, and require true values on both sides.
    def fill_time(stack, valid_source, test_mask=None):
        output=stack.copy();new=np.zeros(stack.shape,dtype=bool)
        # source validity is based ONLY on original available values, not recursively filled output
        for period,(start,end) in PERIODS.items():
            ids=np.flatnonzero((dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end)))
            for i in ids:
                missing=~valid_source[i]
                if test_mask is not None:missing=missing|test_mask[i]
                if not missing.any():continue
                for k in range(1,max_gap+1):
                    b=i-k;a=i+k
                    if b not in ids or a not in ids:continue
                    both=missing&valid_source[b]&valid_source[a]
                    if not both.any():continue
                    left=stack[b];right=stack[a]
                    # ensure contiguous nominal dates even if input has missing files
                    if (dates[i]-dates[b]).days!=k or (dates[a]-dates[i]).days!=k:continue
                    output[i][both]=(left[both]+right[both])*0.5
                    new[i][both]=True
                    missing=missing&~both
                    if not missing.any():break
        return output,new
    valid=np.isfinite(data)
    # holdout validation: blocks hide whole dates at each selected pixel; no using targets as predictors
    rng=np.random.default_rng(seed)
    candidate=np.zeros(data.shape,dtype=bool)
    for period,(start,end) in PERIODS.items():
        ids=np.flatnonzero((dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end)))
        for i in ids:
            if i==ids[0] or i==ids[-1]:continue
            k=np.isfinite(data[i-1]) & np.isfinite(data[i]) & np.isfinite(data[i+1])
            candidate[i]=k
    holdout=(rng.random(data.shape)<holdout_fraction)&candidate
    masked=data.copy();masked[holdout]=np.nan
    predicted,filled=fill_time(masked,np.isfinite(masked))
    evaluated=holdout&filled
    residual=(predicted[evaluated]-data[evaluated]).astype('float64')
    metrics={'holdout_candidate_pixels':int(candidate.sum()),'holdout_selected_pixels':int(holdout.sum()),'holdout_predicted_pixels':int(evaluated.sum()),'mae':float(np.abs(residual).mean()) if residual.size else None,'rmse':float(np.sqrt((residual**2).mean())) if residual.size else None,'caveat':'random pixel-level holdout among cells with observed previous/next nominal day; optimistic vs true long cloud gaps; no claims for days with no neighboring observations'}
    # production fills only cells with previous and next ORIGINAL values; never overwrites originals
    prod,fillmask=fill_time(data,valid)
    rows=[]
    for i,d in enumerate(dates):
        name=d.strftime('%Y-%m-%d')
        # provenance: 0 no value, 1 source, 2 estimated temporal
        provenance=valid[i].astype('uint8')+2*fillmask[i].astype('uint8')
        assert not np.any(provenance==3)
        tiff(out/'05_AOD_Interpolation'/f'AOD_temporal_{name}.tif',prod[i],meta['transform'],meta['crs'],np.nan,'float32')
        tiff(out/'05_AOD_Interpolation'/f'provenance_{name}.tif',provenance,meta['transform'],meta['crs'],0,'uint8')
        rows.append({'date':name,'source_cells':int(valid[i].sum()),'new_estimated_cells':int(fillmask[i].sum()),'remaining_missing_cells':int((~np.isfinite(prod[i])).sum())})
    save_csv(out/'05_AOD_Interpolation'/'interpolation_daily_quality.csv',pd.DataFrame(rows))
    metrics.update({'days_total':len(dates),'total_source_cells':int(valid.sum()),'total_new_estimated_cells':int(fillmask.sum()),'method':'strict symmetric 1..max_gap-day temporal neighbor interpolation, no extrapolation, do not cross season boundaries','max_gap_days_per_side':max_gap,'evaluation_seed':seed,'holdout_fraction':holdout_fraction})
    save_json(out/'05_AOD_Interpolation'/'interpolation_validation.json',metrics)
    return metrics
