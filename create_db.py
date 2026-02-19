import sqlite3

db_connection = sqlite3.connect("gtfs.db", timeout=float("inf"))
db_cursor = db_connection.cursor()

db_cursor.executescript(
	"""
	CREATE TABLE services(
		service_id TEXT PRIMARY KEY,
		monday TEXT CHECK( monday IN ("0", "1") ) NOT NULL,
		tuesday TEXT CHECK( tuesday IN ("0", "1") ) NOT NULL,
		wednesday TEXT CHECK( wednesday IN ("0", "1") ) NOT NULL,
		thursday TEXT CHECK( thursday IN ("0", "1") ) NOT NULL,
		friday TEXT CHECK( friday IN ("0", "1") ) NOT NULL,
		saturday TEXT CHECK( saturday IN ("0", "1") ) NOT NULL,
		sunday TEXT CHECK( sunday IN ("0", "1") ) NOT NULL,
		start_date TEXT NOT NULL,
		end_date TEXT NOT NULL
	);
	CREATE TABLE additions(
		service_id TEXT NOT NULL,
		date TEXT NOT NULL,
		PRIMARY KEY (service_id, date),
		FOREIGN KEY (service_id) REFERENCES services(service_id)
	);
	CREATE TABLE removals(
		service_id TEXT NOT NULL,
		date TEXT NOT NULL,
		PRIMARY KEY (service_id, date),
		FOREIGN KEY (service_id) REFERENCES services(service_id)
	);
	CREATE TABLE stop_times(
		trip_id TEXT NOT NULL,
		departure_time TEXT NOT NULL,
		stop_id TEXT NOT NULL,
		stop_sequence TEXT NOT NULL,
		pickup_type TEXT CHECK( pickup_type IN ("0", "1", "2", "3") ),
		drop_off_type TEXT CHECK( drop_off_type IN ("0", "1", "2", "3") ),
		PRIMARY KEY (trip_id, stop_sequence),
		FOREIGN KEY (trip_id) REFERENCES trips(trip_id),
		FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
	);
	CREATE TABLE stops(
		stop_id TEXT PRIMARY KEY,
		stop_name TEXT NOT NULL,
		stop_lat TEXT NOT NULL,
		stop_lon TEXT NOT NULL,
		parent_station TEXT
	);
	CREATE TABLE trips(
		route_id TEXT NOT NULL,
		service_id TEXT NOT NULL,
		trip_id TEXT PRIMARY KEY,
		trip_headsign TEXT,
		direction_id TEXT NOT NULL,
		wheelchair_accessible TEXT CHECK( wheelchair_accessible IN ("0", "1", "2") ),
		bikes_allowed TEXT CHECK( bikes_allowed IN ("0", "1", "2") ),
		FOREIGN KEY (service_id) REFERENCES services(service_id)
	);
	"""
)

db_connection.commit()
db_connection.close()