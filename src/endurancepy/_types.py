"""Reference column schemas (names and dtypes) for the EndurancePy data objects.

These mirror FastF1's data model where it makes sense and add endurance-specific
columns (car number, class, manufacturer, per-class position, gaps...). They are
the single source of truth for the parsers (milestones 2.2+) and guarantee that
the columns always exist with a stable dtype, even when a given session does not
populate them.

See ``docs/analyse_fastf1.md`` (§5, §7) and ``docs/plan_implementation.md`` (§4).
"""

from __future__ import annotations

# --- Laps -------------------------------------------------------------------
# Columns reused from FastF1 (same names/dtypes) plus endurance additions.
LAPS_COLUMNS: dict[str, str] = {
    # timing
    "Time": "timedelta64[ns]",
    "LapTime": "timedelta64[ns]",
    "LapNumber": "float64",
    "Stint": "float64",
    "Sector1Time": "timedelta64[ns]",
    "Sector2Time": "timedelta64[ns]",
    "Sector3Time": "timedelta64[ns]",
    "Sector1SessionTime": "timedelta64[ns]",
    "Sector2SessionTime": "timedelta64[ns]",
    "Sector3SessionTime": "timedelta64[ns]",
    "PitInTime": "timedelta64[ns]",
    "PitOutTime": "timedelta64[ns]",
    "LapStartTime": "timedelta64[ns]",
    "LapStartDate": "datetime64[ns]",
    # speeds
    "SpeedST": "float64",  # top speed at the speed-trap (from TOP_SPEED)
    "LapAvgSpeed": "float64",  # average lap speed in km/h (from KPH) -- NOT top speed
    # identity (endurance unit is the car/crew)
    "CarNumber": "string",  # keep leading zeros -> string, never int
    "Driver": "string",
    "DriverNumber": "string",
    "Team": "string",
    "Class": "string",
    "Manufacturer": "string",
    # position
    "Position": "float64",
    "PositionInClass": "float64",
    "GapToLeader": "timedelta64[ns]",
    "GapToLeaderInClass": "timedelta64[ns]",
    # status / flags
    "TrackStatus": "string",
    "IsPersonalBest": "boolean",
    "IsAccurate": "boolean",
    "Generated": "boolean",
    "DriverChange": "boolean",
    "Hour": "float64",
}

# Columns kept for FastF1 compatibility but not populated for endurance data.
LAPS_COMPAT_COLUMNS: dict[str, str] = {
    "Compound": "string",
    "TyreLife": "float64",
    "FreshTyre": "boolean",
    "SpeedI1": "float64",
    "SpeedI2": "float64",
    "SpeedFL": "float64",
    "Deleted": "boolean",
    "DeletedReason": "string",
}

# --- Session results --------------------------------------------------------
# One row per *car/crew* (the endurance unit): individual driver identity is not
# meaningful at the classification level, so only the crew (drivers "; "-joined)
# is kept. Counters (positions, grid, laps) are nullable integers (``Int64``),
# never floats -- a finishing position of ``2`` should read ``2``, not ``2.0``.
RESULTS_COLUMNS: dict[str, str] = {
    "CarNumber": "string",
    "Class": "string",
    "Manufacturer": "string",
    "TeamName": "string",
    "Crew": "string",  # the car's drivers, "; "-joined
    "Position": "Int64",
    "PositionInClass": "Int64",
    "ClassifiedPosition": "string",
    "ClassifiedPositionInClass": "string",
    "GridPosition": "Int64",
    "Time": "timedelta64[ns]",
    "BestLapTime": "timedelta64[ns]",
    "Status": "string",
    "Points": "float64",  # may be fractional (half points), so kept as float
    "Laps": "Int64",
}

# --- Weather ----------------------------------------------------------------
WEATHER_COLUMNS: dict[str, str] = {
    "Time": "timedelta64[ns]",
    "AirTemp": "float64",
    "TrackTemp": "float64",
    "Humidity": "float64",
    "Pressure": "float64",
    "Rainfall": "boolean",
    "WindSpeed": "float64",
    "WindDirection": "float64",
}

# --- Track status -----------------------------------------------------------
TRACK_STATUS_COLUMNS: dict[str, str] = {
    "Time": "timedelta64[ns]",
    "Status": "string",
    "Message": "string",
}
