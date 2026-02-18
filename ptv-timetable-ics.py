from urllib.request import urlretrieve
from zipfile import ZipFile
import os
import shutil
import csv

stop_times = []
stops = []
trips = []

urlretrieve("http://data.ptv.vic.gov.au/downloads/gtfs.zip", "gtfs.zip")
with ZipFile("gtfs.zip", "r") as filezip:
    filezip.extractall()
    for name in filezip.namelist():
        if name.endswith("/google_transit.zip"):
            directory = name.removesuffix("google_transit.zip")
            with ZipFile(name, "r") as filezippy:
                filezippy.extractall(directory, ("stop_times.txt", "stops.txt", "trips.txt"))
                for namey in filezippy.namelist():
                    path = directory + namey
                    if path.endswith("stop_times.txt"):
                        with open(path, newline="") as filecsv:
                            for row in csv.DictReader(filecsv):
                                stop_times.append(row)
                    if path.endswith("stops.txt"):
                        with open(path, newline="") as filecsv:
                            for row in csv.DictReader(filecsv):
                                stops.append(row)
                    if path.endswith("trips.txt"):
                        with open(path, newline="") as filecsv:
                            for row in csv.DictReader(filecsv):
                                trips.append(row)
            shutil.rmtree(directory)
os.remove("gtfs.zip")
print(stops)