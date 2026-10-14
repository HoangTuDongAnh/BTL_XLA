import argparse,zipfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--project-root',default='.');a=p.parse_args()
    folder=Path(a.project_root).resolve()/'05_Final_Evaluation'
    validation=folder/'05_Quality_Reports'/'stage5_validation.json'
    if not validation.is_file():raise FileNotFoundError('Run run_stage5.py first')
    target=folder/'Stage5_Results_For_Review.zip';included=0
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for f in sorted(folder.rglob('*')):
            if f==target or not f.is_file():continue
            if f.suffix.lower() not in ('.csv','.json','.png','.md'):continue
            if f.stat().st_size>10*1024*1024:continue
            z.write(f,f.relative_to(folder));included+=1
    print(f'Created {target} with {included} files ({target.stat().st_size/1024:.1f} KB)')
if __name__=='__main__':main()
