
from pathlib import Path
from pyhdf.SD import SD, SDC

root = Path("DATARAW/02_MODIS_MAIAC_AOD")

files = sorted(root.rglob("*.hdf"))

if not files:
    raise FileNotFoundError("Khong tim thay file HDF!")

file_path = files[0]

print(f"File: {file_path.name}")
print(f"Tong so file HDF: {len(files)}")

hdf = SD(str(file_path), SDC.READ)

print("\nDanh sach cac lop du lieu:")
for name in hdf.datasets():
    print(f" - {name}")

hdf.end()

print("\nHDF4 READ OK")
