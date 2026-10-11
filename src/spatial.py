from pathlib import Path
import json
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from rasterio.features import geometry_mask
from .common import write_csv,write_json

def run(groups,out):
    target=out/'04_Spatial';target.mkdir(parents=True,exist_ok=True)
    provfile=groups['boundary']/'red_river_delta_11_provinces.geojson'
    geo=gpd.read_file(provfile).to_crs(4326)
    if len(geo)!=11:raise ValueError(f'Cần 11 tỉnh, file có {len(geo)}')
    geo.to_file(target/'provinces.geojson',driver='GeoJSON')
    united=geo.geometry.union_all() if hasattr(geo.geometry,'union_all') else geo.unary_union
    gpd.GeoDataFrame({'name':['Red River Delta 11 provinces']},geometry=[united],crs=4326).to_file(target/'region.geojson',driver='GeoJSON')
    maps=sorted(groups['worldcover'].rglob('*_Map.tif'))
    info=[]
    for file in maps:
        # Stream just a crop; never load a 36k x 36k raster entirely.
        with rasterio.open(file) as src:
            if src.crs is None: raise ValueError(f'CRS missing: {file}')
            poly=gpd.GeoSeries([united],crs=4326).to_crs(src.crs).iloc[0]
            bbox=poly.bounds
            left=max(src.bounds.left,bbox[0]);bottom=max(src.bounds.bottom,bbox[1]);right=min(src.bounds.right,bbox[2]);top=min(src.bounds.top,bbox[3])
            if left>=right or bottom>=top:continue
            window=from_bounds(left,bottom,right,top,src.transform).round_offsets().round_lengths()
            window=window.intersection(rasterio.windows.Window(0,0,src.width,src.height))
            transform=src.window_transform(window)
            outpath=target/(file.stem+'_region.tif')
            h,w=int(window.height),int(window.width)
            profile=src.profile.copy();profile.update(driver='GTiff',height=h,width=w,transform=transform,dtype='uint8',nodata=0,compress='deflate',tiled=True,bigtiff='IF_SAFER',blockxsize=512,blockysize=512)
            import numpy as np
            pixels=0; cropland=0
            with rasterio.open(outpath,'w',**profile) as dst:
                for _,block in dst.block_windows(1):
                    srcblock=rasterio.windows.Window(window.col_off+block.col_off,window.row_off+block.row_off,block.width,block.height)
                    arr=src.read(1,window=srcblock)
                    localtransform=dst.window_transform(block)
                    mask=geometry_mask([poly],out_shape=arr.shape,transform=localtransform,invert=True)
                    cropped=np.where(mask,arr,0).astype('uint8')
                    dst.write(cropped,1,window=block)
                    pixels+=int(mask.sum());cropland+=int(((cropped==40)&mask).sum())
            info.append({'tile':file.name,'pixels_in_roi':pixels,'cropland_pixels':cropland,'crs':str(src.crs),'output':outpath.name})
    write_csv(target/'worldcover_quality.csv',info)
    write_json(target/'metadata.json',{'worldcover_version':'2021 v200','cropland_code':40,'categorical_resampling':'nearest','note':'Subset tile rasters, not mosaic; imagery 2021 used as proxy for land cover 2025'})
    return {'provinces':len(geo),'worldcover_tiles_processed':len(info)}
