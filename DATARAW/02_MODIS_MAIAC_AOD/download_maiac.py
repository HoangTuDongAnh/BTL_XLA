#!/usr/bin/env python3
"""Download MCD19A2.061 HDF4 granules for the two 2025 rice harvest windows.

Uses publicly listed LAADS archive indexes, not the retired Classic API or Submit Order.
Install: python -m pip install requests beautifulsoup4
Set LAADS_TOKEN via environment; NEVER hardcode, share, or commit your token.
"""
import argparse
import csv
import datetime as dt
import hashlib
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = 'https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCD19A2/2025/'
WINDOWS = [(dt.date(2025, 5, 1), dt.date(2025, 6, 30), 'May_Jun'),
           (dt.date(2025, 10, 1), dt.date(2025, 11, 30), 'Oct_Nov')]
DEFAULT_TILES = ['h27v06', 'h28v06', 'h27v07', 'h28v07']
FNAME = re.compile(r'^MCD19A2\.A2025(\d{3})\.(h\d{2}v\d{2})\.061\.[\w]+\.hdf$', re.I)
HDF4_MAGIC = b'\x0e\x03\x13\x01'
COLUMNS = ['season', 'date', 'tile', 'filename', 'url', 'status', 'bytes', 'sha256', 'note']


def dates(a, b):
    day = a
    while day <= b:
        yield day
        day += dt.timedelta(days=1)


def http_session(token):
    session = requests.Session()
    session.headers.update({'User-Agent':'De9-MAIAC-Research-Downloader/1.0'})
    if token:
        session.headers['Authorization'] = 'Bearer ' + token
    retry = Retry(total=4, connect=4, read=4, backoff_factor=1,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(['GET']), respect_retry_after_header=True)
    session.mount('https://', HTTPAdapter(max_retries=retry))
    return session


def get_manifest(session, tiles):
    records=[]
    errors=[]
    for start,end,season in WINDOWS:
        for day in dates(start,end):
            doy=day.timetuple().tm_yday
            index=urljoin(BASE,f'{doy:03d}/')
            try:
                response=session.get(index, timeout=45)
                response.raise_for_status()
                soup=BeautifulSoup(response.text,'html.parser')
                matches={}
                for a in soup.find_all('a', href=True):
                    fn=a.get_text(strip=True)
                    m=FNAME.match(fn)
                    if m and int(m.group(1))==doy and m.group(2).lower() in tiles:
                        matches[fn]=urljoin(index,a['href'])
                for fn,url in sorted(matches.items()):
                    tile=FNAME.match(fn).group(2).lower()
                    records.append({'season':season,'date':day.isoformat(),'tile':tile,
                        'filename':fn,'url':url,'status':'pending','bytes':'','sha256':'','note':''})
                missing=set(tiles)-{r['tile'] for r in records if r['date']==day.isoformat()}
                if missing:
                    errors.append({'date':day.isoformat(),'issue':'missing_tile_in_listing',
                                   'details':','.join(sorted(missing))})
            except Exception as exc:
                errors.append({'date':day.isoformat(),'issue':'listing_failed','details':str(exc)})
            print(f'Scan {day}: {len([r for r in records if r["date"]==day.isoformat()])} files', flush=True)
            time.sleep(0.12)
    return records,errors


def safe_hdf(path):
    try:
        if path.stat().st_size < 4096:return False
        with path.open('rb') as f:return f.read(4)==HDF4_MAGIC
    except OSError:return False


def download(session,record,root):
    p=root/record['season']/record['filename']
    p.parent.mkdir(parents=True,exist_ok=True)
    if safe_hdf(p):
        record.update(status='already_present',bytes=p.stat().st_size,note='HDF4 header valid')
        return
    if p.exists():p.unlink()
    temp=p.with_suffix('.hdf.part')
    # Existing .part is deliberately re-downloaded to avoid incorrectly resuming changed content.
    if temp.exists():temp.unlink()
    try:
        with session.get(record['url'],stream=True,timeout=(30,180),allow_redirects=True) as resp:
            resp.raise_for_status()
            if 'text/html' in resp.headers.get('Content-Type','').lower():
                raise ValueError('HTML response instead of HDF: check Earthdata token')
            sha=hashlib.sha256()
            size=0
            with temp.open('wb') as f:
                for chunk in resp.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk);sha.update(chunk);size+=len(chunk)
            if not safe_hdf(temp):
                raise ValueError('Downloaded content is not a valid HDF4 signature')
            temp.replace(p)
            record.update(status='downloaded',bytes=size,sha256=sha.hexdigest(),note='HDF4 header valid')
    except Exception as exc:
        record.update(status='failed',note=str(exc))
        if temp.exists():temp.unlink()


def save_csv(path,rows,columns):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore')
        writer.writeheader();writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description='LAADS MCD19A2 downloader, both 2025 seasons')
    parser.add_argument('--mode',choices=['scan','test','download'],default='scan')
    parser.add_argument('--output',default='De9_AOD')
    parser.add_argument('--tiles',nargs='+',default=DEFAULT_TILES)
    args=parser.parse_args()
    tiles=[t.lower() for t in args.tiles]
    if any(not re.fullmatch(r'h\d{2}v\d{2}',t) for t in tiles):
        parser.error('Invalid tile, expected h27v06 etc.')
    root=Path(args.output)
    root.mkdir(parents=True,exist_ok=True)
    token=os.environ.get('LAADS_TOKEN','').strip()
    if args.mode!='scan' and not token:
        parser.error('Set LAADS_TOKEN in your environment before downloading.')
    session=http_session(token)
    manifest,issues=get_manifest(session,tiles)
    save_csv(root/'manifest.csv',manifest,COLUMNS)
    save_csv(root/'coverage_issues.csv',issues,['date','issue','details'])
    print(f'Found {len(manifest)} granules; coverage issues: {len(issues)}')
    if not manifest:
        sys.exit('No HDF granules located. Check internet, index pages, or tile IDs.')
    if args.mode=='scan':
        print('Review manifest.csv and coverage_issues.csv, then run --mode test.')
        return
    selected=manifest[:1] if args.mode=='test' else manifest
    for i,rec in enumerate(selected,1):
        print(f'{i}/{len(selected)} downloading {rec["filename"]}',flush=True)
        download(session,rec,root)
        save_csv(root/'manifest.csv',manifest,COLUMNS)
        time.sleep(0.2)
    counts={k:sum(r['status']==k for r in manifest) for k in ['downloaded','already_present','failed','pending']}
    print('Results:',counts)
    print('Files:',root.resolve())

if __name__=='__main__':main()
