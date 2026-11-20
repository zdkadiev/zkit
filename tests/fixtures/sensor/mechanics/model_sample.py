"""Check the five deliveries after moving one sensor from R7 to R8."""


def run(broken=False):
    current = None
    violations = []
    deliveries = [
        ("first", "R8", 1, 20, (1, 20)),
        ("newer", "R8", 3, 21, (3, 21)),
        ("retired", "R7", 99, 30, (3, 21)),
        ("reordered", "R8", 2, 19, (3, 21)),
        ("duplicate", "R8", 3, 21, (3, 21)),
    ]
    for label, registration, sequence, temperature, expected in deliveries:
        if (broken or registration == "R8") and (current is None or sequence > current[0]):
            current = sequence, temperature
        if current != expected:
            violations.append(label)
    return violations
