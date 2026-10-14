from pathlib import Path
import argparse
from src.stage4.core import locations,save_json
from src.stage4.dataset import build
from src.stage4.analyze import run as analyze
from src.stage4.visual import run as visuals
from src.stage4.validate import run as validate

def main():
    p=argparse.ArgumentParser(description='Stage 4 | Exploratory daily association and 0-3 day lags')
    p.add_argument('--project-root',default='.')
    p.add_argument('--min-hours',type=int,default=18)
    p.add_argument('--min-aod-pixels',type=int,default=5)
    p.add_argument('--min-pairs',type=int,default=8)
    args=p.parse_args()
    root=Path(args.project_root).resolve();base,s3,out=locations(root)
    print('== Daily dataset ==',flush=True)
    daily,stations=build(base,s3,out,args.min_hours,args.min_aod_pixels)
    print(f'calendar={len(daily)}; PM25 days={daily.pm25_hanoi.notna().sum()}; original AOD days={daily.aod_original_hanoi.notna().sum()}',flush=True)
    print('== Lag correlations and sensitivity ==',flush=True)
    mainresults,sensitivity,audit=analyze(daily,stations,out,min_n=args.min_pairs)
    print(audit,flush=True)
    print('== Visualizations ==',flush=True)
    print(visuals(daily,mainresults,out),flush=True)
    print('== Validation ==',flush=True)
    print(validate(daily,mainresults,out),flush=True)
    save_json({'status':'COMPLETED','days':len(daily),'primary_computable_tests':audit['main_computable'],'review_package':'run tools/package_stage4_results.py'},out/'06_Quality_Reports'/'stage4_run_report.json')
    print('Stage 4 complete. Run tools/package_stage4_results.py --project-root .',flush=True)
if __name__=='__main__':main()
