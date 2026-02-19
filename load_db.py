import sqlite3
from urllib.request import urlretrieve
from zipfile import ZipFile
import os
import shutil
import csv

from get_ancestor import get_ancestor

urlretrieve("http://data.ptv.vic.gov.au/downloads/gtfs.zip", "gtfs.zip")
print("Retrieved gtfs.zip")

with ZipFile("gtfs.zip", "r") as filezip:
	filezip.extractall()
	print("Unzipped gtfs.zip")

	db_connection = sqlite3.connect("gtfs.db", timeout=float("inf"))
	db_cursor = db_connection.cursor()

	for table in ("services", "additions", "removals", "stop_times", "stops", "trips"):
		db_cursor.execute("DELETE FROM " + table)

	for name in filezip.namelist():
		if name.endswith("/google_transit.zip"):
			directory = name.removesuffix("google_transit.zip")
			with ZipFile(name, "r") as filezippy:
				filezippy.extractall(directory, ("calendar.txt", "calendar_dates.txt", "stop_times.txt", "stops.txt", "trips.txt"))
				for namey in filezippy.namelist():
					path = directory + namey
					if path.endswith("calendar.txt"):
						with open(path, newline="", encoding="utf-8-sig") as filecsv:
							for row in csv.DictReader(filecsv):
								row["service_id"] = directory + row["service_id"]
								db_cursor.execute(
									"INSERT INTO services VALUES(:service_id, :monday, :tuesday, :wednesday, :thursday, :friday, :saturday, :sunday, :start_date, :end_date)",
									row
								)
					if path.endswith("calendar_dates.txt"):
						with open(path, newline="", encoding="utf-8-sig") as filecsv:
							for row in csv.DictReader(filecsv):
								row["service_id"] = directory + row["service_id"]
								if row["exception_type"] == "1":
									db_cursor.execute(
										"INSERT INTO additions VALUES(:service_id, :date)",
										row
									)
								if row["exception_type"] == "2":
									db_cursor.execute(
										"INSERT INTO removals VALUES(:service_id, :date)",
										row
									)
					if path.endswith("stops.txt"):
						with open(path, newline="", encoding="utf-8-sig") as filecsv:
							for row in csv.DictReader(filecsv):
								row["stop_id"] = directory + row["stop_id"]
								if row["parent_station"] == "":
									row["parent_station"] = None
								else:
									row["parent_station"] = directory + row["parent_station"]
								db_cursor.execute(
									"INSERT INTO stops VALUES(:stop_id, :stop_name, :stop_lat, :stop_lon, :parent_station)",
									row
								)
					if path.endswith("trips.txt"):
						with open(path, newline="", encoding="utf-8-sig") as filecsv:
							for row in csv.DictReader(filecsv):
								row["service_id"] = directory + row["service_id"]
								if "bikes_allowed" not in row:
									row["bikes_allowed"] = "0"
								db_cursor.execute(
									"INSERT INTO trips VALUES(:route_id, :service_id, :trip_id, :trip_headsign, :direction_id, :wheelchair_accessible, :bikes_allowed)",
									row
								)
				
				for namey in filezippy.namelist():
					path = directory + namey
					if path.endswith("stop_times.txt"):
						with open(path, newline="", encoding="utf-8-sig") as filecsv:
							for row in csv.DictReader(filecsv):
								row["stop_id"] = get_ancestor(directory + row["stop_id"], db_cursor)
								db_cursor.execute(
									"INSERT INTO stop_times VALUES(:trip_id, :departure_time, :stop_id, :stop_sequence, :pickup_type, :drop_off_type)",
									row
								)

			shutil.rmtree(directory, ignore_errors=True)
			print("Processed " + directory)

	db_connection.commit()
	db_connection.close()

os.remove("gtfs.zip")