#!/usr/bin/env python3
"""Stage 2 preflight: inventory raw datasets; never change raw files. Python >=3.9."""
import argparse
import csv
import json
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

GROUPS = {
    '01_VIIRS_Fire': 'viirs',
    '02_MODIS_MAIAC_AOD': 'aod',
    '03_OpenAQ_PM25': 'pm25',
    '04_ESA_WorldCover': 'worldcover',
    '05_GADM_Boundary': 'boundary',
}
EXCLUDE = {'.git', '__pycache__', '.idea', '.venv', 'venv', 'node_modules'}
TILE_RE = re.compile(r'(h\d{2}v\d{2})', re.I)
WC_TILE_RE = re.compile(r'(N\d{2}E\d{3})', re.I)
HDF_DATE_RE = re.compile(r'\.A(\d{7})\.', re.I)


def utc_iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec='seconds')


def file_record(path, root, group, nested=False):
    rel = path.relative_to(root).as_posix()
    stat = path.stat()
    name = path.name
    ext = path.suffix.lower()
    tile = (TILE_RE.search(name) or WC_TILE_RE.search(name))
    date = HDF_DATE_RE.search(name)
    date_value = ''
    if date:
        try:
            date_value = datetime.strptime(date.group(1), '%Y%j').strftime('%Y-%m-%d')
        except ValueError:
            pass
    return {
        'group': group, 'relative_path': rel, 'extension': ext,
        'size_bytes': stat.st_size, 'modified_utc': utc_iso(stat.st_mtime),
        'tile': tile.group(1) if tile else '', 'acquisition_date': date_value,
        'is_zip': ext == '.zip', 'zip_members': '', 'zip_error': '',
    }


def main():
    ap = argparse.ArgumentParser(description='Inventory 5 raw-data folders and generate portable path config')
    ap.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parent.parent,
                    help='Project root containing DATARAW (default: parent of script folder)')
    ap.add_argument('--raw-dir', default='DATARAW', help='Raw data folder inside project root')
    ap.add_argument('--output', default='02_Data_Preprocessing/00_Inventory', help='Output directory relative to project')
    ap.add_argument('--zip-list', action='store_true', help='List names inside ZIP (metadata only; no extraction)')
    args = ap.parse_args()
    project = args.project_root.expanduser().resolve()
    raw = (project / args.raw_dir).resolve()
    out = (project / args.output).resolve()
    if not raw.is_dir():
        ap.error(f'DATARAW directory not found: {raw}')
    if out == raw or raw in out.parents:
        ap.error('Output must be outside DATARAW to protect raw files')
    out.mkdir(parents=True, exist_ok=True)

    records = []
    issues = []
    overview = {}
    for folder, kind in GROUPS.items():
        directory = raw / folder
        if not directory.exists():
            issues.append({'severity':'ERROR','group':kind,'message':f'Missing folder: {folder}'})
            overview[kind] = {'folder':folder, 'files':0, 'bytes':0, 'extensions':{}}
            continue
        file_paths = []
        for base, dirs, files in os.walk(directory, followlinks=False):
            dirs[:] = [x for x in dirs if x not in EXCLUDE and not (Path(base)/x).is_symlink()]
            for filename in files:
                p = Path(base) / filename
                if not p.is_symlink():
                    file_paths.append(p)
        ext_counts = Counter()
        size_sum = 0
        for path in sorted(file_paths):
            try:
                rec = file_record(path, raw, kind)
                if rec['is_zip'] and args.zip_list:
                    try:
                        with zipfile.ZipFile(path) as z:
                            members = [i.filename for i in z.infolist() if not i.is_dir()]
                            rec['zip_members'] = len(members)
                            # list ZIP member names in separate CSV, never extract them
                            for member in members:
                                zip_records.append({'archive':rec['relative_path'], 'member':member})
                    except Exception as exc:
                        rec['zip_error'] = f'{type(exc).__name__}: {exc}'
                        issues.append({'severity':'WARNING','group':kind,'message':f'Could not list ZIP {path.name}: {exc}'})
                records.append(rec)
                ext_counts[rec['extension'] or '(none)'] += 1
                size_sum += rec['size_bytes']
            except (OSError, ValueError) as exc:
                issues.append({'severity':'ERROR','group':kind,'message':f'Cannot inspect {path}: {exc}'})
        overview[kind] = {'folder':folder,'files':len(file_paths),'bytes':size_sum,
                          'extensions':dict(sorted(ext_counts.items()))}
        if not file_paths:
            issues.append({'severity':'WARNING','group':kind,'message':f'Folder empty: {folder}'})

    # The config intentionally uses paths relative to the project root.
    config = {
        'schema_version':1,
        'project_root_hint':'.',
        'raw_dir':args.raw_dir,
        'groups':{v:(Path(args.raw_dir)/k).as_posix() for k,v in GROUPS.items()},
        'output_dir':'02_Data_Preprocessing',
        'periods':{'May_Jun_2025':['2025-05-01','2025-06-30'],
                   'Oct_Nov_2025':['2025-10-01','2025-11-30']},
        'region_file':None,
        'notes':'Paths are relative to project root; inventory does not validate scientific data quality.'
    }
    # Suggested region file is not assumed to exist.
    target = raw/'05_GADM_Boundary'/'red_river_delta_union.geojson'
    if target.is_file():
        config['region_file'] = target.relative_to(project).as_posix()
    elif (raw/'05_GADM_Boundary'/'gadm41_VNM_1.json').is_file():
        config['region_file'] = (Path(args.raw_dir)/'05_GADM_Boundary'/'gadm41_VNM_1.json').as_posix()
        issues.append({'severity':'INFO','group':'boundary','message':'Found national boundary only; create/verify 11-province union before filtering.'})
    else:
        issues.append({'severity':'INFO','group':'boundary','message':'Region boundary not auto-selected; set region_file in paths_config.json later.'})

    (out/'paths_config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2),encoding='utf-8')
    (out/'inventory_summary.json').write_text(json.dumps({'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'project_root_local':str(project),'raw_dir_local':str(raw),'groups':overview,
        'inventory_file_count':len(records),'issues':issues},ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'file_inventory.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['group','relative_path','extension','size_bytes','modified_utc','tile','acquisition_date','is_zip','zip_members','zip_error'])
        writer.writeheader();writer.writerows(records)
    with (out/'issues.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['severity','group','message']);writer.writeheader();writer.writerows(issues)
    if args.zip_list:
        with (out/'zip_members.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=['archive','member']);writer.writeheader();writer.writerows(zip_records)
    print('Project:',project)
    print('Raw:',raw)
    print('Output:',out)
    print('File count:',len(records))
    for kind, entry in overview.items():
        print(f"  {kind:10} {entry['files']:6} files {entry['bytes']/1024**2:10.1f} MiB {entry['extensions']}")
    print('Issues:',len(issues))
    print('Done: file_inventory.csv, inventory_summary.json, paths_config.json, issues.csv')
    return 0


if __name__ == '__main__':
    # Populated only when --zip-list is requested.
    zip_records = []
    sys.exit(main())
