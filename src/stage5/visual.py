import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

def run(frames,out):
    vis=out/'04_Visualizations';vis.mkdir(exist_ok=True)
    data=frames['lag'];sel=data[(data.comparison=='fire_pm25')&(data.season!='all')]
    fig,ax=plt.subplots(figsize=(9,4.4))
    for season,g in sel.groupby('season'):ax.plot(g.lag_days,g.pearson_r,marker='o',label=season)
    ax.axhline(0,linewidth=.8,color='gray');ax.set_xticks([0,1,2,3]);ax.set_xlabel('Lag (days)');ax.set_ylabel('Pearson r')
    ax.set_title('VIIRS Cropland vs Hanoi PM2.5');ax.grid(alpha=.25);ax.legend();fig.tight_layout();fig.savefig(vis/'lag_season_comparison.png',dpi=160);plt.close(fig)
    bs=pd.read_csv(out/'01_Robustness'/'bootstrap_ci.csv');sel=bs[(bs.comparison=='fire_pm25')]
    fig,ax=plt.subplots(figsize=(9,4.4))
    for season,g in sel.groupby('season'):
        g=g.sort_values('lag_days');ax.errorbar(g.lag_days,g.pearson_r,yerr=[(g.pearson_r-g.ci_95_low).clip(lower=0),(g.ci_95_high-g.pearson_r).clip(lower=0)],capsize=4,marker='o',label=season)
    ax.axhline(0,linewidth=.8,color='gray');ax.set_xticks([0,1,2,3]);ax.set_xlabel('Lag (days)');ax.set_ylabel('Pearson r and block-bootstrap CI')
    ax.grid(alpha=.25);ax.legend();fig.tight_layout();fig.savefig(vis/'bootstrap_ci_fire_pm25.png',dpi=160);plt.close(fig)
    eval_file=out/'02_AOD_Evaluation'/'aod_block_holdout_summary.csv';a=pd.read_csv(eval_file)
    if not a.empty:
        fig,ax=plt.subplots(figsize=(9,4));idx=range(len(a));ax.bar(idx,a.rmse);ax.set_xticks(list(idx),a.method,rotation=12,ha='right');ax.set_ylabel('RMSE');ax.set_title('AOD blocked holdout: original observations');fig.tight_layout();fig.savefig(vis/'aod_blocked_rmse.png',dpi=160);plt.close(fig)
    return {'figures':len(list(vis.glob('*.png')))}
