#!/usr/bin/env python3
"""OpenAQ v3 downloader for De 9. Python 3.10+, requests."""
import argparse
import csv
import json
import os
import random
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = 'https://api.openaq.org/v3'
LOCATIONS = [2161306, 2161292, 4946812, 4946813]
SEASONS = {'May_Jun_2025': ('2025-05-01', '2025-06-30'), 'Oct_Nov_2025': ('2025-10-01', '2025-11-30')}
FIELDS = ['location_id','location_name','sensor_id','sensor_name','parameter','unit','season','datetime_utc','datetime_local','value','coverage_observed_count','coverage_expected_count','source_endpoint']

class APIError(Exception):
    pass

class OpenAQ:
    def __init__(self, token, pause=0.4):
        self.session = requests.Session()
        self.session.headers.update({'X-API-Key':token,'Accept':'application/json','User-Agent':'De9-PM25-Research/1.0'})
        self.pause=pause

    def get(self, path, params=None):
        url=BASE+path
        for retry in range(6):
            try:
                r=self.session.get(url,params=params,timeout=(15,75))
            except requests.RequestException as e:
                if retry==5: raise APIError(f'{path}: network error: {e}') from e
                time.sleep(min(30,2**retry)+random.random())
                continue
            if r.status_code in (429,500,502,503,504):
                if retry==5: raise APIError(f'{path}: HTTP {r.status_code} {r.text[:200]}')
                wait=r.headers.get('Retry-After')
                try: delay=min(90,max(1,float(wait)))
                except (ValueError,TypeError): delay=min(45,2**retry)+random.random()
                time.sleep(delay)
                continue
            if r.status_code in (401,403):
                raise APIError('Authentication/permission error (HTTP %s). Check OPENAQ_API_KEY and account permissions.'%r.status_code)
            if not r.ok:
                raise APIError(f'{path}: HTTP {r.status_code}: {r.text[:300]}')
            try: body=r.json()
            except ValueError: raise APIError(f'{path}: response was not JSON')
            if not isinstance(body,dict) or not isinstance(body.get('results'),list):
                raise APIError(f'{path}: unexpected response keys {list(body) if isinstance(body,dict) else type(body)}')
            time.sleep(self.pause)
            return body
        raise APIError(f'{path}: retries exhausted')

    def pages(self,path,params=None):
        page=1
        params=dict(params or {})
        params['limit']=1000
        while True:
            params['page']=page
            result=self.get(path,params)
            rows=result['results']
            yield from rows
            found=result.get('meta',{}).get('found')
            if len(rows)<1000 or (isinstance(found,int) and page*1000>=found): break
            page+=1
            if page>1000:raise APIError(f'{path}: pagination exceeded 1000 pages')

def normalize_name(s):
    return str(s or '').strip().lower().replace('₂','2').replace(' ','').replace('.','').replace('µ','u').replace('μ','u')

def find_pm25_sensor(s):
    param=s.get('parameter') or {}
    name=param.get('name','') if isinstance(param,dict) else str(param)
    display=param.get('displayName','') if isinstance(param,dict) else ''
    return any(normalize_name(x) in ('pm25','pm2_5') for x in (name,display))

def str_date(obj):
    if isinstance(obj,str):return obj
    if isinstance(obj,dict):
        return obj.get('utc') or obj.get('local') or ''
    return ''

def get_dt(row):
    # OpenAQ hours include period.datetimeFrom and period.datetimeTo.
    p=row.get('period') or {}
    dt_from=(p.get('datetimeFrom') or p.get('datetime_from') or {}) if isinstance(p,dict) else {}
    dt=str_date(dt_from)
    if not dt: dt=str_date(row.get('datetime'))
    if not dt: dt=str_date(row.get('date'))
    local=(dt_from.get('local') or '') if isinstance(dt_from,dict) else ''
    return dt,local

def dt_utc(s):
    if not s:return None
    try:
        value=datetime.fromisoformat(s.replace('Z','+00:00'))
        if value.tzinfo is None:return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    except ValueError: return None

def hours_to_rows(raw,loc,sensor,season):
    out=[]
    param=sensor.get('parameter') or {}
    for record in raw:
        utc,local=get_dt(record)
        value=record.get('value')
        if not utc or value is None:
            raise APIError('An hourly record lacks datetime/value: '+str(record)[:400])
        coverage=record.get('coverage') or {}
        out.append({'location_id':loc.get('id'), 'location_name':loc.get('name'),
                    'sensor_id':sensor.get('id'),'sensor_name':sensor.get('name',''),
                    'parameter':param.get('name','pm25'),'unit':param.get('units',''),
                    'season':season,'datetime_utc':utc,'datetime_local':local,
                    'value':value,
                    'coverage_observed_count':coverage.get('observedCount',''),
                    'coverage_expected_count':coverage.get('expectedCount',''),
                    'source_endpoint':f"/sensors/{sensor['id']}/hours"})
    return out

def write_csv(path,rows,columns):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore')
        writer.writeheader();writer.writerows(rows)

def expected_dates(start,end):
    d=date.fromisoformat(start); last=date.fromisoformat(end)
    while d<=last:
        yield d.isoformat();d+=timedelta(days=1)

def main():
    ap=argparse.ArgumentParser(description='OpenAQ v3 Hanoi PM2.5 downloader (De 9)')
    ap.add_argument('--mode',choices=['scan','download'],default='scan',help='scan=check PM2.5 sensors; download=download all hourly data')
    ap.add_argument('--output',default='OpenAQ_PM25')
    ap.add_argument('--locations',default=','.join(map(str,LOCATIONS)),help='Comma-separated OpenAQ Location IDs')
    ap.add_argument('--include-daily',action='store_true',help='Additionally obtain OpenAQ precomputed daily averages')
    args=ap.parse_args()
    api_key=os.environ.get('OPENAQ_API_KEY','').strip()
    if not api_key:sys.exit('ERROR: Set OPENAQ_API_KEY in current terminal (do NOT put key into script).')
    output=Path(args.output)
    api=OpenAQ(api_key)
    locations=[int(x.strip()) for x in args.locations.split(',') if x.strip()]
    stations=[];sensors_meta=[];manifest=[];coverage=[];issues=[]
    for loc_id in locations:
        print(f'\n[Location {loc_id}]',flush=True)
        try:
            records=api.get(f'/locations/{loc_id}')['results']
            if not records:raise APIError('no location found')
            loc=records[0]
            # Use canonical /locations/{id}/sensors endpoint; do not assume embedded list is complete.
            sensors=list(api.pages(f'/locations/{loc_id}/sensors'))
            selected=[s for s in sensors if find_pm25_sensor(s)]
            co=loc.get('coordinates') or {}
            stations.append({'location_id':loc_id,'name':loc.get('name',''),'latitude':co.get('latitude',''),'longitude':co.get('longitude',''),
                             'timezone':loc.get('timezone',''),'provider':str(loc.get('provider','')),
                             'pm25_sensors':len(selected),'url':f'https://explore.openaq.org/locations/{loc_id}'})
            for s in selected:
                sensors_meta.append({'location_id':loc_id,'sensor_id':s.get('id'),'sensor_name':s.get('name',''),
                                     'parameter_name':(s.get('parameter') or {}).get('name',''),
                                     'unit':(s.get('parameter') or {}).get('units',''),
                                     'first_datetime':str(s.get('datetimeFirst','')),
                                     'last_datetime':str(s.get('datetimeLast',''))})
            print(f"  {loc.get('name')} | {len(selected)} PM2.5 sensor(s)")
            if not selected:issues.append({'location_id':loc_id,'sensor_id':'','season':'','error':'NO_PM25_SENSOR'})
        except (APIError,KeyError,TypeError,ValueError) as e:
            print('  ERROR:',e)
            issues.append({'location_id':loc_id,'sensor_id':'','season':'','error':str(e)})
            continue
        if args.mode=='scan':continue
        for s in selected:
            sid=s['id']
            for season,(start,end) in SEASONS.items():
                # End-exclusive interval; in UTC includes complete two dates and avoids truncation.
                end_exclusive=(date.fromisoformat(end)+timedelta(days=1)).isoformat()
                params={'datetime_from':start+'T00:00:00Z','datetime_to':end_exclusive+'T00:00:00Z'}
                name=f'location_{loc_id}_sensor_{sid}_{season}.csv'
                target=output/season/name
                try:
                    print(f'  Sensor {sid} | {season}: fetching hourly...',flush=True)
                    raw=list(api.pages(f'/sensors/{sid}/hours',params))
                    rows=hours_to_rows(raw,loc,s,season)
                    # UTC day range; OpenAQ may return times from alternate local timezones.
                    unique={}
                    for row in rows:
                        t=dt_utc(row['datetime_utc'])
                        if t is None:continue
                        if not (datetime.fromisoformat(start).replace(tzinfo=timezone.utc)<=t<datetime.fromisoformat(end_exclusive).replace(tzinfo=timezone.utc)):continue
                        unique[row['datetime_utc']]=row
                    rows=[unique[k] for k in sorted(unique)]
                    write_csv(target,rows,FIELDS)
                    day_count=defaultdict(int)
                    for row in rows:
                        day_count[row['datetime_utc'][:10]]+=1
                    for day in expected_dates(start,end):
                        coverage.append({'location_id':loc_id,'sensor_id':sid,'season':season,'date_utc':day,'hours_with_data':day_count[day],'has_any_data':int(day_count[day]>0)})
                    manifest.append({'location_id':loc_id,'sensor_id':sid,'season':season,'file':str(target),'records':len(rows),'days_with_data':sum(v>0 for v in day_count.values()),'expected_days':61,'status':'downloaded'})
                    print(f'    Saved {len(rows)} hourly values across {len(day_count)} UTC day(s)')
                    if args.include_daily:
                        dailyraw=list(api.pages(f'/sensors/{sid}/days',params))
                        daily_rows=[]
                        for item in dailyraw:
                            d,local=get_dt(item)
                            daily_rows.append({'location_id':loc_id,'sensor_id':sid,'datetime_utc':d,'datetime_local':local,'value':item.get('value',''),'unit':(s.get('parameter') or {}).get('units','')})
                        write_csv(output/season/f'location_{loc_id}_sensor_{sid}_{season}_openaq_days.csv',daily_rows,['location_id','sensor_id','datetime_utc','datetime_local','value','unit'])
                except (APIError,requests.RequestException) as e:
                    issues.append({'location_id':loc_id,'sensor_id':sid,'season':season,'error':str(e)})
                    manifest.append({'location_id':loc_id,'sensor_id':sid,'season':season,'file':str(target),'records':0,'days_with_data':0,'expected_days':61,'status':'ERROR'})
                    print('    ERROR:',e)
    write_csv(output/'stations.csv',stations,['location_id','name','latitude','longitude','timezone','provider','pm25_sensors','url'])
    write_csv(output/'sensors.csv',sensors_meta,['location_id','sensor_id','sensor_name','parameter_name','unit','first_datetime','last_datetime'])
    write_csv(output/'issues.csv',issues,['location_id','sensor_id','season','error'])
    if args.mode=='download':
        write_csv(output/'manifest.csv',manifest,['location_id','sensor_id','season','file','records','days_with_data','expected_days','status'])
        write_csv(output/'coverage_report.csv',coverage,['location_id','sensor_id','season','date_utc','hours_with_data','has_any_data'])
    print(f'\nDone. Output: {output.resolve()}')
    print('NOTE: coverage_report is observation coverage, NOT proof of hourly continuity or sensor quality.')
    if issues:sys.exit('Completed with warnings/errors; inspect issues.csv')

if __name__=='__main__':main()
