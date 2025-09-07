import logging
import numpy as np
from collections import Counter, defaultdict
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def convert_numpy_types(obj):

    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj


def build_analytics(publications: List[Dict[str, Any]]) -> Dict[str, Any]:

    timeline = defaultdict(int)
    types = Counter()
    keywords = Counter()

    for p in publications:

        yr = p.get("publication_year")
        if yr:
            try:
                timeline[int(yr)] += 1
            except (ValueError, TypeError):

                logger.warning(f"Invalid publication year: {yr}")

        t = p.get("publication_type")
        if t:
            types[t] += 1

        kws = p.get("keywords", [])
        if isinstance(kws, str):
            kws = [kws]
        keywords.update(kws)


    return {
        "timeline": sorted(
            [{"year": y, "count": c} for y, c in timeline.items()],
            key=lambda x: x["year"],
        ),
        "types": [{"type": t, "count": c} for t, c in types.most_common()],
        "keywords": [{"value": k, "count": c} for k, c in keywords.most_common(40)],
    }


HEAVY_FIELDS = {"abstract", "references", "full_text"}

def strip_heavy(pub: dict, *, keep_keywords: bool = True) -> dict:

    for field in list(pub.keys()):
        if field in HEAVY_FIELDS:
            pub.pop(field, None)
        elif field == "keywords" and not keep_keywords:
            pub.pop(field, None)
    return pub