from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


@lru_cache(maxsize=1)
def load_rubric() -> Dict[str, Any]:
    rubric_path = Path(__file__).resolve().parent.parent / "rubrics" / "corsair_v1.json"
    return json.loads(rubric_path.read_text())
