import argparse
from pathlib import Path
import zipfile

EXACT=[
 '01_Daily_Dataset/fire_daily_timeseries.csv','01_Daily_Dataset/pm25_daily_station.csv',
 '01_Daily_Dataset/pm25_daily_hanoi.csv','01_Daily_Dataset/aod_daily_hanoi.csv',
 '01_Daily_Dataset/daily_analysis_dataset.csv','02_Correlation/correlation_results.csv',
 '02_Correlation/lag_correlation_results.csv','04_Sensitivity/sensitivity_results.csv'
]
def main():
    p=argparse.ArgumentParser();p.add_argument('--project-root',default='.');args=p.parse_args()
    out=Path(args.project_root).resolve()/'04_Correlation_Analysis'
    missing=[f for f in EXACT if not (out/f).is_file()]
    if missing:raise FileNotFoundError('Stage4 is incomplete: '+str(missing))
    output=out/'Stage4_Results_For_Review.zip';files=[out/f for f in EXACT]
    files+=sorted((out/'06_Quality_Reports').glob('*.json'))
    files+=sorted((out/'06_Quality_Reports').glob('*.csv'))
    files+=sorted((out/'05_Visualizations').glob('*.png'))
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,f.relative_to(out))
    print(f'Created: {output} | {len(files)} files | {output.stat().st_size:,} bytes')
if __name__=='__main__':main()
