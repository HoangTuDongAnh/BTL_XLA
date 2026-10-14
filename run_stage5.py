import argparse,traceback
from pathlib import Path
from src.stage5 import core,final_dataset,robustness,aod_evaluation,visual,validate

def main():
    p=argparse.ArgumentParser();p.add_argument('--project-root',default='.');p.add_argument('--bootstrap-reps',type=int,default=1200)
    p.add_argument('--bootstrap-block',type=int,default=7);p.add_argument('--aod-days-per-season',type=int,default=6)
    a=p.parse_args();root,out=core.dirs(a.project_root)
    frames,paths=core.load(root)
    try:
        print('== Final dataset ==',flush=True);print(final_dataset.run(frames,out),flush=True)
        print('== Robustness ==',flush=True);print(robustness.run(frames['daily'],out,reps=a.bootstrap_reps,block=a.bootstrap_block),flush=True)
        print('== AOD blocked evaluation ==',flush=True);print(aod_evaluation.run(root,out,max_days=a.aod_days_per_season*2),flush=True)
        print('== Figures ==',flush=True);print(visual.run(frames,out),flush=True)
        print('== Validation ==',flush=True);report=validate.run(frames,out);print(report['status'],report['counts'],flush=True)
        core.js({'status':report['status'],'input_files':{k:str(v) for k,v in paths.items()},'validation':report['counts']},out/'05_Quality_Reports'/'stage5_run_report.json')
        print('Stage5 completed. Run tools/package_stage5_results.py --project-root .',flush=True)
        return 1 if report['status']=='FAIL' else 0
    except Exception as ex:
        core.js({'status':'ERROR','error':str(ex),'traceback':traceback.format_exc()},out/'05_Quality_Reports'/'stage5_run_error.json')
        raise
if __name__=='__main__':raise SystemExit(main())
