"""Surface reviewed citation mismatches without declaring models valid.

Evidence matches the exact source/reference pair, not a title or fuzzy name.
Editing equations cannot make a mismatched citation authoritative. Correcting
either citation field ends this specific match; it does not certify the update.
"""
from functools import lru_cache
import json
from pathlib import Path

@lru_cache(maxsize=1)
def _reviews():
    path = Path(__file__).resolve().parents[1] / 'data' / 'source_reviews.json'
    return json.loads(path.read_text())['reviews']

def citation_reviews(model):
    return [dict(row) for row in _reviews()
            if model.source == row['source'] and model.reference == row['reference']]
