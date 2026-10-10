NASA LAADS / MCD19A2.061 downloader — Đề 9

1. Install Python 3.10+ and packages:
   py -m pip install requests beautifulsoup4

2. Open PowerShell in the folder containing download_maiac.py.

3. Build file list and coverage report (no token needed for accessible public indexes):
   py download_maiac.py --mode scan
   Open De9_AOD/manifest.csv and De9_AOD/coverage_issues.csv.

4. Sign in to NASA Earthdata and generate your own LAADS/Earthdata bearer download token
   following the current LAADS Download Help instructions. Never paste this token into chats.
   In PowerShell, for THIS session only:
   $env:LAADS_TOKEN = 'PASTE_YOUR_TOKEN_LOCALLY'

5. Test a single HDF:
   py download_maiac.py --mode test
   Inspect the HDF file and manifest.csv.

6. Download both seasons (May-Jun & Oct-Nov 2025):
   py download_maiac.py --mode download
   You may rerun after interruption. Existing files with a valid HDF4 header are skipped.

Default tiles: h27v06, h28v06, h27v07, h28v07, from your LAADS screenshot.
Total scheduled calendar days: 122. A full 4-tile/day set would be 488 files,
BUT this is not guaranteed; report missing date/tile combinations rather than inventing files.
Check the study boundary before deciding the 4-tile list is scientifically final.

Files created:
- De9_AOD/manifest.csv: source URLs, dates, tile, download status and hashes
- De9_AOD/coverage_issues.csv: missing tile/date or archive listing failures
- De9_AOD/May_Jun/*.hdf and De9_AOD/Oct_Nov/*.hdf: original satellite data

Technical caveat: HDF4 signature verification catches HTML/corrupt auth responses but
is NOT an exhaustive scientific integrity or SDS content check. Check HDF datasets,
AOD_QA and Optical_Depth_055 separately in the next data validation stage.
