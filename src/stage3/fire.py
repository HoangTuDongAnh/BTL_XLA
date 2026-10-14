import numpy as np
import pandas as pd
import geopandas as gpd
from rasterio.features import rasterize,geometry_mask
from rasterio.transform import from_origin
from shapely.geometry import Point
from .core import save_csv,save_json,tiff,PERIODS

CRS='EPSG:6933';RES=1000

def run(base,out):
    df=pd.read_csv(out/'01_Cropland_Overlay'/'viirs_cropland_overlay.csv',low_memory=False)
    prov=gpd.read_file(base/'04_Spatial'/'provinces.geojson').to_crs(CRS)
    region=gpd.read_file(base/'04_Spatial'/'region.geojson').to_crs(CRS)
    geo=gpd.GeoDataFrame(df,geometry=gpd.points_from_xy(df.longitude,df.latitude),crs=4326).to_crs(CRS)
    col=next((c for c in ['NAME_1','province','name'] if c in prov),None)
    if col is None:raise ValueError('Province name column missing')
    if 'province' not in geo or geo.province.isna().any():
        # Only fallback for missing administrative labels
        tagged=gpd.sjoin(geo[['geometry']],prov[[col,'geometry']],how='left',predicate='intersects')
        tagged=tagged[~tagged.index.duplicated(keep='first')]
        geo['province']=geo.get('province',pd.Series([None]*len(geo))).fillna(tagged[col].reindex(geo.index))
    counts=geo.groupby(['period','week_id','province','land_class'],dropna=False).size().reset_index(name='detections')
    target=out/'03_Fire_Statistics';save_csv(target/'fire_by_province_week_class.csv',counts)
    daily=geo.groupby(['period','date_local','land_class'],dropna=False).size().reset_index(name='detections');save_csv(target/'fire_daily.csv',daily)
    weekly=geo.groupby(['period','week_id','land_class'],dropna=False).size().reset_index(name='detections');save_csv(target/'fire_weekly.csv',weekly)
    # Raster counts in equal-area grid. Per-province area denominator later from WorldCover, not polygon area.
    minx,miny,maxx,maxy=region.total_bounds
    minx=np.floor(minx/RES)*RES;maxx=np.ceil(maxx/RES)*RES;miny=np.floor(miny/RES)*RES;maxy=np.ceil(maxy/RES)*RES
    width=int(round((maxx-minx)/RES));height=int(round((maxy-miny)/RES));transform=from_origin(minx,maxy,RES,RES)
    mask=geometry_mask(region.geometry,out_shape=(height,width),transform=transform,invert=True)
    crop=geo[geo.land_class.eq('Cropland')];rows=[]
    for (period,week),data in crop.groupby(['period','week_id'],dropna=False):
        if not isinstance(week,str) or not week:continue
        shapes=((g,1) for g in data.geometry)
        arr=rasterize(shapes,out_shape=(height,width),transform=transform,fill=0,all_touched=False,merge_alg=__import__('rasterio').enums.MergeAlg.add,dtype='int32')
        total=int(arr.sum());assert total==len(data),(week,total,len(data))
        arr[(~mask)&(arr==0)]=-1
        tiff(out/'02_Fire_Density'/f'fire_count_{week}.tif',arr,transform,CRS,-1,'int32')
        rows.append({'period':period,'week_id':week,'input_cropland_points':len(data),'raster_sum':total,'max_cell_count':int(arr.max())})
    save_csv(out/'02_Fire_Density'/'density_quality.csv',pd.DataFrame(rows))
    # KDE is a visualization-only option; keep raw counts as authoritative
    return {'cropland_points':len(crop),'weeks_with_detections':len(rows),'density_resolution_m':RES,'province_statistics_rows':len(counts)}
