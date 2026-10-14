import argparse,traceback,sys
from src.stage3.core import project,save_json

def main():
    p=argparse.ArgumentParser(description='Stage 3: VIIRS Cropland, weekly fire/AOD, conservative AOD interpolation')
    p.add_argument('--project-root',default='.')
    p.add_argument('--module',default='all',choices=['all','overlay','fire','aod_weekly','aod_interpolation','visual','validate'])
    p.add_argument('--max-gap',type=int,default=2)
    args=p.parse_args()
    if not 1<=args.max_gap<=3:p.error('--max-gap must be 1..3')
    base,out=project(args.project_root)
    from src.stage3 import overlay,fire,aod,visual,validate
    steps={'overlay':lambda:overlay.run(base,out),'fire':lambda:fire.run(base,out),'aod_weekly':lambda:aod.weekly(base,out),'aod_interpolation':lambda:aod.interpolation(base,out,max_gap=args.max_gap),'visual':lambda:visual.run(out),'validate':lambda:validate.run(base,out)}
    results={}; names=steps if args.module=='all' else [args.module]
    for name in names:
        print('==',name,'==',flush=True)
        try:
            r=steps[name]();results[name]={'status':'OK','result':r};print(str(r)[:1300],flush=True)
        except Exception as ex:
            results[name]={'status':'FAILED','message':str(ex),'traceback':traceback.format_exc()};print(traceback.format_exc(),file=sys.stderr);break
    save_json(out/'07_Quality_Reports'/'stage3_run_report.json',results)
    if any(r['status']=='FAILED' for r in results.values()):sys.exit(2)
if __name__=='__main__':main()
