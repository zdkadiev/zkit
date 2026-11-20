"""Illustrative one-second receiver budget. The ring starts empty."""

ASSUMPTIONS = {
    "A-1": {"label": "Offered frames", "unit": "frames/s", "best": 400, "expected": 800, "worst": 1200},
    "A-2": {"label": "Receiver rate", "unit": "frames/s", "best": 1000, "expected": 1000, "worst": 1000},
}
DESIGN_INPUTS = {"DC-1": {"op": "<=", "unit": "registrations"}}

UNITS = {"registration_memory": "B", "arrivals": "frames/s", "service": "frames/s", "backlog": "frames"}


def compute(a):
    return {
        "arrivals": a["A-1"],
        "service": a["A-2"],
        "backlog": max(0, a["A-1"] - a["A-2"]),
        "registration_memory": a["DC-1"] * 16,  # bytes per active registration
    }


LIMITS = [
    {"id": "L-1", "label": "Receive ring", "metric": "backlog", "op": "<=", "limit": 200, "req": "FR-1"},
]

CAPACITY = [{
    "resource": "B-2 receiver",
    "interfaces": ["I-1"],
    "demand": {"metric": "arrivals", "basis": "estimated", "assumptions": ["A-1"]},
    "capacity": {"metric": "service", "basis": "estimated", "assumptions": ["A-2"]},
    "limits": ["L-1"],
    "windows": {"best": "quiet, 1 s", "expected": "normal, 1 s", "worst": "burst, 1 s"},
}]
