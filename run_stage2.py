import argparse,sys,traceback
from pathlib import Path
from datetime import datetime,timezone
from src.common import context,write_json

def main():
    ap=argparse.ArgumentParser(description='Đề 9 Stage 2, giữ nguyên DATARAW')
    ap.add_argument('--project-root',default='.')
    ap.add_argument('--module',choices=['all','viirs','pm25','spatial','aod'],default='all')
    ap.add_argument('--aod-full',action='store_true',help='Process all MAIAC HDF files into daily QA-filtered AOD GeoTIFF')
    ap.add_argument('--aod-qa',choices=['strict','best_land'],default='strict')
    ap.add_argument('--aod-resolution',type=float,default=0.01)
    ap.add_argument('--aod-limit-days',type=int,default=None,help='Test first N days before full run')
    ap.add_argument('--min-hours',type=int,default=18)
    a=ap.parse_args(); root,raw,out,groups=context(a.project_root)
    from src import viirs,pm25,spatial,aod
    jobs={'viirs':lambda:viirs.run(groups,out),'pm25':lambda:pm25.run(groups,out,min_hours=a.min_hours),'spatial':lambda:spatial.run(groups,out),'aod':lambda:aod.run(groups,out,full=a.aod_full,qa_mode=a.aod_qa,resolution=a.aod_resolution,limit_days=a.aod_limit_days)}
    outcomes={};targets=list(jobs) if a.module=='all' else [a.module]
    for name in targets:
        print(f'== {name} ==',flush=True)
        try:
            result=jobs[name]();outcomes[name]={'status':'ok','result':result};print(result,flush=True)
        except Exception as exc:
            outcomes[name]={'status':'failed','reason':str(exc),'traceback':traceback.format_exc()};print(f'ERROR: {exc}',file=sys.stderr,flush=True)
    write_json(out/'05_Quality_Reports'/'stage2_run_report.json',{'generated_utc':datetime.now(timezone.utc).isoformat(),'project_root':str(root),'modules':outcomes})
    if any(v['status']=='failed' for v in outcomes.values()):sys.exit(2)

if __name__=='__main__':main()
