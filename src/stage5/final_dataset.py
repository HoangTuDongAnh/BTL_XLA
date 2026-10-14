import pandas as pd
from .core import csv,js

def run(frames,out):
    daily=frames['daily'].copy();lag=frames['lag'].copy();fire=frames['fire'].copy()
    if len(daily)!=122 or daily[['period','date']].duplicated().any():raise ValueError('Stage4 calendar is not unique 122 days')
    csv(daily,out/'03_Final_Dataset'/'final_daily_dataset.csv')
    csv(lag,out/'03_Final_Dataset'/'final_lag_results.csv')
    csv(lag[lag.lag_days.eq(0)],out/'03_Final_Dataset'/'final_correlation_results.csv')
    csv(fire,out/'03_Final_Dataset'/'final_fire_statistics.csv')
    summary={'days':len(daily),'pm25_days':int(daily.pm25_hanoi.notna().sum()),
      'aod_original_days':int(daily.aod_original_hanoi.notna().sum()),
      'cropland_detections':int(daily.fire_rrd.sum()),'lag_rows':len(lag),
      'notes':['No causal inference','AOD nominal UTC vs VIIRS/PM25 UTC+7','WorldCover 2021 vs VIIRS 2025',
               'Interpolated AOD not used in primary comparisons']}
    js(summary,out/'03_Final_Dataset'/'final_quality_summary.json')
    return summary
