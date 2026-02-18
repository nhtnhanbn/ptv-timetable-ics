from urllib.request import urlretrieve
from zipfile import ZipFile
import os

urlretrieve("http://data.ptv.vic.gov.au/downloads/gtfs.zip", "gtfs.zip")

with ZipFile("gtfs.zip", "r") as filezip:
    filezip.extractall()
    for name in filezip.namelist():
        if name.endswith("/google_transit.zip"):
            with ZipFile(name, "r") as filezippy:
                filezippy.extractall(name.removesuffix("google_transit.zip"), ("stop_times.txt", "stops.txt", "trips.txt"))
            os.remove(name)
os.remove("gtfs.zip")