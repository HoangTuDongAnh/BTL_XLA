"""Stage 2 MAIAC MCD19A2.061 AOD pipeline. No interpolation.

Uses SDS metadata for scale/validity and HDF-EOS StructMetadata for MODIS
sinusoidal georeferencing. Strict QA: clear land, normal adjacency,
AOD best-quality and no glint. Per orbit -> native pixel mean -> EPSG:4326
per-day mosaic. Preserves no-data and logs failures. 100% of observations
are never assumed to be valid.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import csv
import json
import re
import traceback
import numpy as np

MODIS_SINU = '+proj=sinu +R=6371007.181 +nadgrids=@null +wktext +no_defs'
FILENAME = re.compile(r'^MCD19A2\.A(\d{4})(\d{3})\.h(\d{2})v(\d{2})\.061\..*\.hdf$', re.I)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def _write_csv(path, records, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)


def qa_mask(aod, qa, attrs, qa_attrs, mode='strict'):
    """Return per-orbit boolean mask, deriving ranges from SDS metadata.

    Modes: strict=clear land, normal adjacency, quality=0, no glint;
    best_land=land, quality=0, no glint (less restrictive cloud mask).
    """
    fill = int(attrs.get('_FillValue', -28672))
    lo, hi = (int(x) for x in attrs.get('valid_range', [-100, 6000]))
    af = np.asarray(aod)
    qf = np.asarray(qa, dtype=np.uint16)
    valid = (af != fill) & (af >= lo) & (af <= hi)
    qfill = int(qa_attrs.get('_FillValue', 0))
    valid &= qf != qfill
    valid &= ((qf >> 3) & 3) == 0  # land
    valid &= ((qf >> 8) & 15) == 0  # best AOD quality
    valid &= ((qf >> 12) & 1) == 0   # no sun glint
    if mode == 'strict':
        valid &= (qf & 7) == 1       # clear
        valid &= ((qf >> 5) & 7) == 0  # normal adjacency
    elif mode != 'best_land':
        raise ValueError('mode phải là strict hoặc best_land')
    return valid


def _read_sds(hdf, name):
    s = hdf.select(name)
    try:
        attrs = dict(s.attributes())
        values = np.asarray(s.get())
        return values, attrs
    finally:
        s.endaccess()


def _native_transform(meta, shape):
    """Read exact grid1km (not grid5km) from HDF-EOS StructMetadata.0."""
    from rasterio.transform import from_bounds
    text = str(meta.get('StructMetadata.0', '')).replace('\x00', '')
    part = text.split('GROUP=GRID_1', 1)[-1].split('END_GROUP=GRID_1', 1)[0]
    if 'GridName="grid1km"' not in part or 'Projection=GCTP_SNSOID' not in part:
        raise ValueError('Missing expected grid1km MODIS sinusoidal georeferencing')
    def point(name):
        m = re.search(r'\b'+name+r'=\(\s*([-+\d.]+)\s*,\s*([-+\d.]+)\s*\)', part)
        if not m:
            raise ValueError('Missing '+name)
        return float(m.group(1)), float(m.group(2))
    x0,y0 = point('UpperLeftPointMtrs')
    x1,y1 = point('LowerRightMtrs')
    if not (x1 > x0 and y0 > y1):
        raise ValueError('Invalid grid bounds')
    xm = re.search(r'\bXDim=(\d+)', part); ym = re.search(r'\bYDim=(\d+)', part)
    if not xm or not ym or (int(ym.group(1)),int(xm.group(1))) != tuple(shape[-2:]):
        raise ValueError('SDS dimensions mismatch HDF-EOS grid1km')
    return from_bounds(x0,y1,x1,y0,int(xm.group(1)),int(ym.group(1)))


def _parse_file(file):
    m=FILENAME.match(file.name)
    if not m: raise ValueError('Unexpected MCD19A2 naming pattern')
    year,doy,h,v = map(int,m.groups())
    d=datetime(year,1,1)+timedelta(days=doy-1)
    if d.year!=year: raise ValueError('Invalid day-of-year')
    return d.strftime('%Y-%m-%d'), f'h{h:02d}v{v:02d}'


def _extract_tile(file, mode):
    from pyhdf.SD import SD, SDC
    hdf=SD(str(file), SDC.READ)
    try:
        datasets=hdf.datasets()
        if 'Optical_Depth_055' not in datasets or 'AOD_QA' not in datasets:
            raise ValueError('Missing required SDS AOD/QA')
        global_attrs=hdf.attributes()
        a,aa=_read_sds(hdf,'Optical_Depth_055')
        q,qa=_read_sds(hdf,'AOD_QA')
    finally:
        hdf.end()
    if a.ndim!=3 or a.shape!=q.shape:
        raise ValueError(f'Orbit SDS dimensions mismatch {a.shape} vs {q.shape}')
    transform=_native_transform(global_attrs,a.shape)
    valid=qa_mask(a,q,aa,qa,mode)
    scale=float(aa.get('scale_factor',1.0)); offset=float(aa.get('add_offset',0.0))
    # Scale convention follows the MCD19A2 SDS metadata (physical = raw*scale + offset).
    values=a.astype(np.float32)*scale+offset
    values[~valid]=np.nan
    counts=valid.sum(axis=0).astype(np.uint8)
    accum=np.nansum(values,axis=0)
    mean=np.full(a.shape[-2:],np.nan,dtype=np.float32)
    np.divide(accum,counts,out=mean,where=counts>0)
    return mean,counts,transform,{'orbits':int(a.shape[0]),'native_valid_observations':int(valid.sum()),'native_valid_cells':int((counts>0).sum()),'scale_factor':scale,'add_offset':offset,'aod_fill':aa.get('_FillValue'),'qa_fill':qa.get('_FillValue')}


def _region_grid(region_path, resolution):
    import geopandas as gpd
    from rasterio.transform import from_origin
    from rasterio.features import geometry_mask
    import math
    geo=gpd.read_file(region_path)
    if geo.empty or geo.crs is None: raise ValueError('GeoJSON geometry/CRS missing')
    geo=geo.to_crs('EPSG:4326')
    geometries=[g for g in geo.geometry if g is not None and not g.is_empty]
    if not geometries: raise ValueError('Boundary geometries empty')
    xmin,ymin,xmax,ymax=geo.total_bounds
    x0=math.floor(float(xmin)/resolution)*resolution
    y1=math.ceil(float(ymax)/resolution)*resolution
    width=math.ceil((float(xmax)-x0)/resolution)
    height=math.ceil((y1-float(ymin))/resolution)
    if width*height > 10_000_000: raise ValueError('Output grid too large')
    transform=from_origin(x0,y1,resolution,resolution)
    inside=geometry_mask(geometries,out_shape=(height,width),transform=transform,invert=True)
    return transform,inside,geo


def _reproject(mean,counts,src_transform,dst_transform,dst_shape):
    from rasterio.warp import reproject,Resampling
    from rasterio.crs import CRS
    dst_mean=np.full(dst_shape,np.nan,dtype=np.float32)
    # Average resampling observes nodata, avoids assigning invalid QA pixels.
    reproject(source=mean,destination=dst_mean,src_transform=src_transform,
              src_crs=CRS.from_string(MODIS_SINU),src_nodata=np.nan,
              dst_transform=dst_transform,dst_crs='EPSG:4326',dst_nodata=np.nan,
              resampling=Resampling.average,init_dest_nodata=True)
    # Count native passes is a QC diagnostic, reprojected nearest; don't use it
    # as an inverse-variance weight or a strict ground-pixel count.
    dst_count=np.zeros(dst_shape,dtype=np.uint8)
    reproject(source=counts,destination=dst_count,src_transform=src_transform,
              src_crs=CRS.from_string(MODIS_SINU),src_nodata=0,
              dst_transform=dst_transform,dst_crs='EPSG:4326',dst_nodata=0,
              resampling=Resampling.nearest,init_dest_nodata=True)
    return dst_mean,dst_count


def _write_tif(path, array, transform, nodata, dtype, tags):
    import rasterio
    path.parent.mkdir(parents=True,exist_ok=True)
    opts={'driver':'GTiff','height':array.shape[0],'width':array.shape[1],
          'count':1,'crs':'EPSG:4326','transform':transform,'dtype':dtype,
          'nodata':nodata,'compress':'deflate','predictor':3 if dtype=='float32' else 2}
    with rasterio.open(path,'w',**opts) as ds:
        ds.write(array.astype(dtype),1)
        ds.update_tags(**{k:str(v) for k,v in tags.items()})


def run(groups,out,full=False,qa_mode='strict',resolution=0.01,limit_days=None):
    """Metadata probe by default; --aod-full processes all daily rasters."""
    from .common import write_json
    target=out/'02_AOD'; target.mkdir(parents=True,exist_ok=True)
    files=sorted(groups['aod'].rglob('*.hdf'))
    if not files: raise RuntimeError('Không tìm thấy MCD19A2 HDF')
    groups_by_date=defaultdict(list)
    anomalies=[]
    for f in files:
        try:
            date,tile=_parse_file(f)
            groups_by_date[date].append((f,tile))
        except Exception as e: anomalies.append({'file':f.name,'error':str(e)})
    if not full:
        from pyhdf.SD import SD,SDC
        results=[]
        for f in [files[0],files[-1]]:
            h=SD(str(f),SDC.READ)
            try:
                ss={}
                for key in ('Optical_Depth_055','AOD_QA'):
                    ds=h.select(key)
                    try: ss[key]={'info':ds.info(),'attributes':ds.attributes()}
                    finally:ds.endaccess()
                results.append({'file':f.name,'datasets':ss,'projection_present':'GridName="grid1km"' in str(h.attributes().get('StructMetadata.0',''))})
            finally:h.end()
        _write_json(target/'hdf_probe_v2.json',results)
        result={'state':'READY_FOR_FULL_PROCESS','raw_files':len(files),'unique_days':len(groups_by_date),'sample_count':len(results),
                'next_command':'python run_stage2.py --module aod --aod-full','qa_mode':qa_mode}
        _write_json(target/'aod_status.json',result)
        return result
    if not (0.002<=resolution<=0.1): raise ValueError('Resolution out of reasonable range')
    # region = supplied stage1 region union, not an assumed bounding box.
    root=Path(out).parent
    region=root/'DATARAW/05_GADM_Boundary/red_river_delta_union.geojson'
    if not region.exists(): raise FileNotFoundError(region)
    transform,inside,_=_region_grid(region,resolution)
    dates=sorted(groups_by_date)
    if limit_days is not None: dates=dates[:max(0,int(limit_days))]
    manifest=[];daily=[]
    for date in dates:
        sum_raster=np.zeros(inside.shape,dtype=np.float64)
        n_raster=np.zeros(inside.shape,dtype=np.uint8)
        observed=np.zeros(inside.shape,dtype=np.uint8)
        ok=0
        for path,tile in groups_by_date[date]:
            try:
                mean,counts,src_transform,stats=_extract_tile(path,qa_mode)
                warped,warped_count=_reproject(mean,counts,src_transform,transform,inside.shape)
                keep=np.isfinite(warped)&inside
                sum_raster[keep]+=warped[keep]
                n_raster[keep]+=1
                observed[keep]=np.maximum(observed[keep],warped_count[keep])
                manifest.append({'date':date,'tile':tile,'file':path.name,'status':'ok','error':'',**stats})
                ok+=1
            except Exception as error:
                manifest.append({'date':date,'tile':tile,'file':path.name,'status':'error','error':f'{type(error).__name__}: {error}','traceback':traceback.format_exc(limit=2)})
        aod=np.full(inside.shape,np.nan,dtype=np.float32)
        np.divide(sum_raster,n_raster,out=aod,where=n_raster>0)
        aod[~inside]=np.nan
        observed[~inside]=0
        tags={'source':'NASA MODIS MCD19A2.061 Optical_Depth_055','date_utc':date,'qa_mode':qa_mode,
              'daily_method':'quality-filter per orbit, mean valid overpasses per tile, spatial average warp, mosaic',
              'resolution_degree':resolution,'no_interpolation':True,'valid_range_raw':'from file SDS metadata',
              'quality_mask':'cloud=clear,land,adjacency=normal,AOD_quality=best,glint=absent' if qa_mode=='strict' else 'land,AOD_quality=best,glint=absent'}
        d=target/'Daily'
        _write_tif(d/f'AOD_055_{date}.tif',aod,transform,float('nan'),'float32',tags)
        _write_tif(d/f'obs_count_{date}.tif',observed,transform,0,'uint8',{'date_utc':date,'description':'nearest native overpass count; QC diagnostic'})
        valid=int(np.count_nonzero(np.isfinite(aod)&inside))
        total=int(np.count_nonzero(inside))
        daily.append({'date_utc':date,'input_files':len(groups_by_date[date]),'ok_files':ok,'failed_files':len(groups_by_date[date])-ok,
                      'region_pixels':total,'valid_pixels':valid,'coverage_pct':round(valid*100/total,3) if total else 0,
                      'mean_aod':round(float(np.nanmean(aod)),6) if valid else None,
                      'output_aod':str((d/f'AOD_055_{date}.tif').relative_to(out))})
        print(f'[AOD] {date} files={ok}/{len(groups_by_date[date])}, valid region={valid}/{total}',flush=True)
    fields=['date','tile','file','status','error','orbits','native_valid_observations','native_valid_cells','scale_factor','add_offset','aod_fill','qa_fill','traceback']
    _write_csv(target/'aod_file_manifest.csv',manifest,fields)
    _write_csv(target/'aod_daily_quality.csv',daily,['date_utc','input_files','ok_files','failed_files','region_pixels','valid_pixels','coverage_pct','mean_aod','output_aod'])
    _write_json(target/'aod_filename_anomalies.json',anomalies)
    fails=sum(r['status']=='error' for r in manifest)
    status={'state':'COMPLETED' if fails==0 and not anomalies and len(dates)==len(groups_by_date) else 'PARTIAL_OR_TEST',
            'input_files':len(files),'days_total':len(groups_by_date),'days_processed':len(dates),'successful_files':len(manifest)-fails,
            'failed_files':fails,'qa_mode':qa_mode,'resolution_degree':resolution,
            'notes':['Date is source file nominal UTC date; not grouped by each pixel local acquisition time',
                     'Only QA best-quality land retrievals (plus strict clear & adjacency if chosen)',
                     'No gap filling, no haze interpolation; daily raster averages accepted source overpasses',
                     'Per-pixel percentages are output geographic grid cells, not sensor sampling probability',
                     'Failed tiles logged; any such day is incomplete and must not be treated as fully valid']}
    _write_json(target/'aod_status.json',status)
    return status
