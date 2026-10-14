import argparse,zipfile
from pathlib import Path
from datetime import datetime

def main():
    p=argparse.ArgumentParser(description='Create small Stage3 validation bundle; never include large raster/VIIRS raw data')
    p.add_argument('--project-root',default='.')
    args=p.parse_args();root=Path(args.project_root).resolve();out=root/'03_Image_Processing'
    files=[out/'01_Cropland_Overlay'/'overlay_status.json',out/'01_Cropland_Overlay'/'overlay_summary.csv',out/'02_Fire_Density'/'density_quality.csv',out/'03_Fire_Statistics'/'fire_daily.csv',out/'03_Fire_Statistics'/'fire_weekly.csv',out/'03_Fire_Statistics'/'fire_by_province_week_class.csv',out/'04_AOD_Weekly'/'weekly_quality.csv',out/'04_AOD_Weekly'/'metadata.json',out/'05_AOD_Interpolation'/'interpolation_validation.json',out/'05_AOD_Interpolation'/'interpolation_daily_quality.csv',out/'07_Quality_Reports'/'stage3_validation.json',out/'07_Quality_Reports'/'stage3_validation_checks.csv',out/'07_Quality_Reports'/'stage3_run_report.json']
    files+=sorted((out/'06_Maps').glob('*.png'))
    path=out/'Stage3_Results_For_Review.zip'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as zip:
        for f in files:
            if f.is_file():zip.write(f,arcname=str(f.relative_to(out)))
    print('RESULTS:',path,'\nIncluded:',sum(f.exists() for f in files),'of',len(files),'expected files')
if __name__=='__main__':main()
