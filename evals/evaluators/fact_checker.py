from typing import List, Tuple


def verify_required_facts(text: str, required_keywords: List[str]) -> Tuple[bool, List[str]]:
    """
    Verifies that all mandatory factual keywords are present in output text.
    """
    text_lower = text.lower()
    missing: List[str] = []

    for kw in required_keywords:
        if kw.lower() not in text_lower:
            missing.append(kw)

    passed = len(missing) == 0
    return passed, missing
