from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import rasterio

def run(out):
    path=out/'06_Maps';path.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(out/'01_Cropland_Overlay'/'overlay_summary.csv')
    plot=df.pivot(index='period',columns='land_class',values='detections').fillna(0)
    fig,ax=plt.subplots(figsize=(9,4.5));plot.plot.bar(ax=ax,rot=0);ax.set(ylabel='VIIRS detections',xlabel='Season',title='VIIRS hotspots by WorldCover class');ax.legend(loc='upper right');fig.tight_layout();fig.savefig(path/'viirs_by_landclass.png',dpi=170);plt.close(fig)
    quality=pd.read_csv(out/'04_AOD_Weekly'/'weekly_quality.csv')
    fig,ax=plt.subplots(figsize=(10,4));ax.bar(range(len(quality)),quality.coverage_pct);ax.set(xlabel='7-day bin',ylabel='Coverage (%)',title='AOD valid-pixel coverage by week');fig.tight_layout();fig.savefig(path/'aod_weekly_coverage.png',dpi=170);plt.close(fig)
    samples=sorted((out/'02_Fire_Density').glob('fire_count_*.tif'))
    if samples:
        with rasterio.open(samples[0]) as src:
            arr=src.read(1,masked=True);fig,ax=plt.subplots(figsize=(7,5));ax.imshow(arr,cmap='inferno',vmin=0);ax.set(title=samples[0].stem);ax.axis('off');fig.tight_layout();fig.savefig(path/'fire_density_example.png',dpi=170);plt.close(fig)
    return {'figures':len(list(path.glob('*.png')))}
