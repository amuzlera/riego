programed_times = {
    "tz_offset_seconds": -10800,
    "zones": {
        "zona1": 4,
        "zona2": 5,
        "zona3": 18
    },
    "programed_times": {
        "lunes":    [{"start": "20:00", "duration_min": 10}],
        "jueves":   [{"start": "20:00", "duration_min": 10}, {"start": "21:15", "duration_min": 5}],
        "domingo":  [{"start": "22:53", "duration_min": 2}]
    },
    "policy": {
        "mode": "multipliers",
        "include": ["zona1", "zona2", "zona3"],
        "multipliers": {"zona2": 2.0}
    }
}
