"""Read explicit zkit participants and ordered exchanges for both diagram readers."""
import re

ARROW = r"(?:→|->)"
PART = r"B-\d+"
ENDPOINT = rf"({PART})(?:\s*\([^()]*\))?"


def exchanges(interface, parts):
    """One publisher/caller and its explicit recipients. Roles are descriptive."""
    sides = re.split(ARROW, interface.endpoints)
    if len(sides) != 2:
        return []
    source = re.fullmatch(ENDPOINT, sides[0].strip())
    if not source or source[1] not in parts:
        return []
    # Commas inside parenthesized role labels are not recipient separators.
    targets = re.sub(r"\([^()]*\)", "", sides[1])
    recipients = re.split(r"\s*(?:,|\+|\band\b|\bи\b)\s*", targets.strip())
    if not recipients or not all(recipient in parts for recipient in recipients):
        return []
    return [(source[1], interface.id, target) for target in dict.fromkeys(recipients)]


def ordered_steps(raw, edges):
    steps = []
    for chain in re.split(r"\s*(?:;|<br\s*/?>)\s*", raw, flags=re.IGNORECASE):
        ids = [token.strip() for token in re.split(ARROW, chain)]
        if len(ids) < 3 or len(ids) % 2 != 1:
            return []
        for i in range(0, len(ids) - 1, 2):
            step = tuple(ids[i:i + 3])
            if step not in edges:
                return []
            steps.append(step)
    return steps
