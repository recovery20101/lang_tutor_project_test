import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict


def calculate_sm2(
    score_10: int,
    repetitions: int,
    interval: int,
    easiness_factor: float
) -> Dict[str, Any]:
    """Calculates the next SM-2 spaced repetition metrics based on score and history."""
    if score_10 >= 9:
        q = 5
    elif score_10 == 8:
        q = 4
    elif score_10 >= 6:
        q = 3
    elif score_10 >= 4:
        q = 2
    elif score_10 >= 2:
        q = 1
    else:
        q = 0

    new_ef = easiness_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    if new_ef < 1.3:
        new_ef = 1.3

    if q < 3:
        new_repetitions = 0
        new_interval = 1
    else:
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = math.ceil(interval * easiness_factor)

        new_repetitions = repetitions + 1

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    next_review = now + timedelta(days=new_interval)

    return {
        "repetitions": new_repetitions,
        "interval": new_interval,
        "easiness_factor": round(new_ef, 2),
        "last_reviewed": now,
        "next_review": next_review,
        "status": "mastered" if q >= 4 else "learning"
    }
