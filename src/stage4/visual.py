import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def run(dataset,results,out):
    target=out/'05_Visualizations';target.mkdir(parents=True,exist_ok=True)
    for period,frame in dataset.groupby('period'):
        fig,axs=plt.subplots(3,1,figsize=(11,7),sharex=True)
        dates=pd.to_datetime(frame.date)
        for ax,(name,label) in zip(axs,[('fire_rrd','VIIRS Cropland detections'),('pm25_hanoi','PM2.5 (ug/m3)'),('aod_original_hanoi','Original AOD 550 nm')]):
            ax.plot(dates,pd.to_numeric(frame[name],errors='coerce'),marker='.',linewidth=1)
            ax.set_ylabel(label);ax.grid(alpha=.2)
        axs[-1].tick_params(axis='x',rotation=25);fig.suptitle(period+' | original observations; missing data are gaps')
        fig.tight_layout();fig.savefig(target/f'timeseries_{period}.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.5))
    for name,group in results[(results.season=='all') & (results.status=='OK')].groupby('comparison'):
        ax.plot(group.lag_days,group.pearson_r,marker='o',label=name)
    ax.axhline(0,color='gray',linewidth=.8);ax.set_xticks([0,1,2,3]);ax.set_ylabel('Pearson r');ax.set_xlabel('Lag in days: predictor at t vs outcome at t+lag');ax.legend();ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(target/'lag_pearson_overview.png',dpi=160);plt.close(fig)
    return {'figures':3}
