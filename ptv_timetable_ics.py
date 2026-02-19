import datetime
import uuid
from zoneinfo import ZoneInfo
import sqlite3
from icalendar import Calendar, Event
from bottle import route, request, response, run

from get_ancestor import get_ancestor

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

# Serve ICS
def date_time(date_string, time_string):
    date = datetime.datetime.fromisoformat(date_string).replace(tzinfo=ZoneInfo("Australia/Melbourne"))
    hours, minutes, seconds = time_string.split(":")
    time = datetime.timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))
    return date + time

@route("/<requested_stop_id:path>")
def index(requested_stop_id):
    db_connection = sqlite3.connect("gtfs.db", timeout=float("inf"))
    db_cursor = db_connection.cursor()

    requested_stop_id = get_ancestor(requested_stop_id, db_cursor)
    _, stop_name, stop_lat, stop_lon, _ = db_cursor.execute(
        "SELECT * FROM stops WHERE stop_id=:stop_id",
        {"stop_id": requested_stop_id}
    ).fetchone()

    calendar = Calendar()
    calendar.add("PRODID", "-//Nht Nhan//ptv-timetable-ics")
    calendar.add("VERSION", "2.0")
    calendar.add("SUMMARY", "ptv-timetable-ics")

    route_direction_set = set()
    for route_id in request.query.keys():
        for direction_id in request.query.getall(route_id):
            route_direction_set.add((route_id, direction_id))

    for trip_id, departure_time, _, _, pickup_type, drop_off_type in db_cursor.execute(
        "SELECT * FROM stop_times WHERE stop_id=:stop_id",
        {"stop_id": requested_stop_id}
    ).fetchall():
        route_id, service_id, trip_id, trip_headsign, direction_id, wheelchair_accessible, bikes_allowed = db_cursor.execute(
            "SELECT * FROM trips WHERE trip_id=:trip_id",
            {"trip_id": trip_id}
        ).fetchone()
        
        if (route_id, direction_id) in route_direction_set:
            service_id, start_date, end_date = db_cursor.execute(
                "SELECT service_id, start_date, end_date FROM services WHERE service_id=:service_id",
                {"service_id": service_id}
            ).fetchone()
            onday = db_cursor.execute(
                "SELECT monday, tuesday, wednesday, thursday, friday, saturday, sunday FROM services WHERE service_id=:service_id",
                {"service_id": service_id}
            ).fetchone()
            start_datetime = date_time(start_date, departure_time)

            addition = db_cursor.execute("SELECT date FROM additions WHERE service_id=:service_id", {"service_id": service_id}).fetchall()
            removal = db_cursor.execute("SELECT date FROM removals WHERE service_id=:service_id", {"service_id": service_id}).fetchall()

            event = Event()
            event.add("DTSTAMP", datetime.datetime.now())
            event.add("UID", f"{uuid.uuid4()}@nhan.au")
            event.add("SUMMARY", f"{trip_headsign} {route_id}")
            event.add("GEO", (stop_lat, stop_lon))
            event.add("LOCATION", stop_name)
            event.add("DTSTART", start_datetime)
            event.add("DTEND", start_datetime+datetime.timedelta(minutes=1))
            event.add("RDATE", [date_time(date, departure_time) for (date,) in addition])
            event.add("EXDATE", [date_time(date, departure_time) for (date,) in removal])

            event.add("RRULE", {
                "FREQ": "WEEKLY",
                "BYDAY": [ics_day for i, (gtfs_day, ics_day) in enumerate(weekdays) if onday[i] == "1"],
                "UNTIL": date_time(end_date, departure_time)
            })

            event.add("DESCRIPTION", "\n".join((
                pickup_type_descriptions[pickup_type],
                drop_off_type_descriptions[drop_off_type],
                wheelchair_accessible_descriptions[wheelchair_accessible],
                bikes_allowed_descriptions[bikes_allowed]
            )))

            calendar.add_component(event)
    
    db_connection.close()
    
    calendar.add_missing_timezones()

    response.content_type = "text/calendar; charset=UTF-8"
    return calendar.to_ical().decode("utf-8")

run(host="0.0.0.0", port=3002)