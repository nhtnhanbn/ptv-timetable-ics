def get_ancestor(stop_id, db_cursor):
    parent_id = db_cursor.execute("SELECT parent_station FROM stops WHERE stop_id=:stop_id", {"stop_id": stop_id}).fetchone()[0]
    while parent_id is not None:
        stop_id = parent_id
        parent_id = db_cursor.execute("SELECT parent_station FROM stops WHERE stop_id=:stop_id", {"stop_id": stop_id}).fetchone()[0]
    return stop_id