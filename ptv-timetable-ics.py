from urllib.request import urlretrieve
from zipfile import ZipFile
import os
import shutil
import csv
import datetime
import uuid
from zoneinfo import ZoneInfo
from icalendar import Calendar, Event
from bottle import route, request, response, run, template

services = {}
additions = {}
removals = {}
stop_times = []
stops = {}
trips = {}

weekdays = [
    ("monday", "MO"),
    ("tuesday", "TU"),
    ("wednesday", "WE"),
    ("thursday", "TH"),
    ("friday", "FR"),
    ("saturday", "SA"),
    ("sunday", "SU")
]

pickup_type_descriptions = {
    "0": "Regularly scheduled pickup.",
    "1": "No pickup available.",
    "2": "Must phone agency to arrange pickup.",
    "3": "Must coordinate with driver to arrange pickup."
}

drop_off_type_descriptions = {
    "0": "Regularly scheduled drop off.",
    "1": "No drop off available.",
    "2": "Must phone agency to arrange drop off.",
    "3": "Must coordinate with driver to arrange drop off."
}

wheelchair_accessible_descriptions = {
    "0": "No accessibility information for the trip.",
    "1": "Vehicle being used on this particular trip can accommodate at least one rider in a wheelchair.",
    "2": "No riders in wheelchairs can be accommodated on this trip."
}

bikes_allowed_descriptions = {
    "0": "No bike information for the trip.",
    "1": "Vehicle being used on this particular trip can accommodate at least one bicycle.",
    "2": "No bicycles are allowed on this trip."
}

def get_parent(stop_id):
    parent_id = stop_id
    while stops[parent_id]["parent_station"] != "":
        parent_id = stops[parent_id]["parent_station"]
    return parent_id

# Data retrieval
urlretrieve("http://data.ptv.vic.gov.au/downloads/gtfs.zip", "gtfs.zip")
print("Retrieved gtfs.zip")

with ZipFile("gtfs.zip", "r") as filezip:
    filezip.extractall()
    print("Unzipped gtfs.zip")

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
                                services[row["service_id"]] = row
                                additions[row["service_id"]] = []
                                removals[row["service_id"]] = []
                    if path.endswith("calendar_dates.txt"):
                        with open(path, newline="", encoding="utf-8-sig") as filecsv:
                            for row in csv.DictReader(filecsv):
                                if row["exception_type"] == "1":
                                    additions[row["service_id"]].append(row)
                                if row["exception_type"] == "2":
                                    removals[row["service_id"]].append(row)
                    if path.endswith("stop_times.txt"):
                        with open(path, newline="", encoding="utf-8-sig") as filecsv:
                            for row in csv.DictReader(filecsv):
                                stop_times.append(row)
                    if path.endswith("stops.txt"):
                        with open(path, newline="", encoding="utf-8-sig") as filecsv:
                            for row in csv.DictReader(filecsv):
                                stops[row["stop_id"]] = row
                    if path.endswith("trips.txt"):
                        with open(path, newline="", encoding="utf-8-sig") as filecsv:
                            for row in csv.DictReader(filecsv):
                                trips[row["trip_id"]] = row
            shutil.rmtree(directory, ignore_errors=True)
            print("Processed " + directory)
os.remove("gtfs.zip")

for stop_time in stop_times:
    stop_time["stop_id"] = get_parent(stop_time["stop_id"])

# Serve ICS
@route("/<requested_stop_id>")
def index(requested_stop_id):
    requested_parent_id = get_parent(requested_stop_id)
    stop = stops[requested_parent_id]
    stop_name = stop["stop_name"]
    stop_lat = stop["stop_lat"]
    stop_lon = stop["stop_lon"]

    calendar = Calendar()
    calendar.add("PRODID", "-//Nht Nhan//ptv-timetable-ics")
    calendar.add("VERSION", "2.0")
    calendar.add("SUMMARY", "ptv-timetable-ics")

    route_direction_set = set()
    for route_id in request.query.keys():
        for direction_id in request.query.getall(route_id):
            route_direction_set.add((route_id, direction_id))

    for stop_time in stop_times:
        trip_id = stop_time["trip_id"]
        departure_time = stop_time["departure_time"]
        stop_id = stop_time["stop_id"]
        pickup_type = stop_time.get("pickup_type", "0")
        drop_off_type = stop_time.get("drop_off_type", "0")

        trip = trips[trip_id]
        route_id = trip["route_id"]
        service_id = trip["service_id"]
        trip_headsign = trip["trip_headsign"]
        direction_id = trip["direction_id"]
        wheelchair_accessible = trip.get("wheelchair_accessible", "0")
        bikes_allowed = trip.get("bikes_allowed", "0")

        service = services[service_id]
        start_date = service["start_date"]
        end_date = service["end_date"]

        if stop_id == requested_parent_id and (route_id, direction_id) in route_direction_set:
            event = Event()

            event.add("DTSTAMP", datetime.datetime.now())
            event.add("UID", f"{uuid.uuid4()}@nhan.au")
            event.add("SUMMARY", f"{trip_headsign} {route_id}")
            event.add("DTSTART", datetime.datetime.fromisoformat("T".join((start_date, departure_time))).replace(tzinfo=ZoneInfo("Australia/Melbourne")))
            event.add("DTEND", event["DTSTART"])
            event.add("GEO", (stop_lat, stop_lon))
            event.add("LOCATION", stop_name)
            
            event.add("RDATE", [datetime.date.fromisoformat(addition["date"]) for addition in additions[service_id]])
            event.add("EXDATE", [datetime.date.fromisoformat(removal["date"]) for removal in removals[service_id]])

            event.add("DESCRIPTION", "\n".join((
                pickup_type_descriptions[pickup_type],
                drop_off_type_descriptions[drop_off_type],
                wheelchair_accessible_descriptions[wheelchair_accessible],
                bikes_allowed_descriptions[bikes_allowed]
            )))

            event.add("RRULE", {
                "FREQ": "WEEKLY",
                "BYDAY": [ics_day for gtfs_day, ics_day in weekdays if service[gtfs_day] == "1"],
                "UNTIL": datetime.datetime.fromisoformat("T".join((end_date, departure_time))).replace(tzinfo=ZoneInfo("Australia/Melbourne"))
            })

            calendar.add_component(event)
    calendar.add_missing_timezones()

    response.content_type = "text/calendar; charset=UTF-8"
    return calendar.to_ical().decode("utf-8")

run(host="0.0.0.0", port=80)