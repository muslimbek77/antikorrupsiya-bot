import json
import logging
from collections import Counter
from typing import Dict, List

logger = logging.getLogger(__name__)


CATEGORY_KEYWORDS = {
    "Pora va tovlamachilik": ["pora", "pul so'radi", "tovlamachilik", "berishimni so'radi"],
    "Davlat xaridi": ["tender", "xarid", "kontrakt", "shartnoma", "tanlov"],
    "Kadrlar va ishga olish": ["ishga olish", "kadr", "lavozim", "ishga kiritish"],
    "Moliyaviy buzilish": ["o'zlashtirish", "byudjet", "hisobot", "naqd", "pul"],
    "Yer va ruxsatnoma": ["yer", "ruxsatnoma", "ajratish", "kadastr", "qurilish"],
}

ROUTE_BY_CATEGORY = {
    "Pora va tovlamachilik": "Xavfsizlik va komplaens bo'limi",
    "Davlat xaridi": "Xarid komissiyasi nazorati",
    "Kadrlar va ishga olish": "Kadrlar va ichki nazorat bo'limi",
    "Moliyaviy buzilish": "Ichki audit bo'limi",
    "Yer va ruxsatnoma": "Hududiy tekshiruv guruhi",
    "Boshqa": "Operator ko'rib chiqishi",
}

HIGH_RISK_KEYWORDS = [
    "pora", "tovlamachilik", "qo'rqitish", "talon-taroj", "o'zlashtirish", "tender"
]
MEDIUM_RISK_KEYWORDS = [
    "kechikish", "navbat", "ruxsat", "noqonuniy", "bosim", "shubha"
]


def _extract_keywords(text: str) -> List[str]:
    words = [
        word.strip(".,!?;:()[]{}\"'").lower()
        for word in text.split()
        if len(word.strip(".,!?;:()[]{}\"'")) > 4
    ]
    most_common = [word for word, _ in Counter(words).most_common(5)]
    return most_common


def analyze_appeal(message_text: str) -> Dict[str, str]:
    normalized = message_text.lower()
    best_category = "Boshqa"
    best_score = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score > best_score:
            best_category = category
            best_score = score

    high_hits = sum(1 for keyword in HIGH_RISK_KEYWORDS if keyword in normalized)
    medium_hits = sum(1 for keyword in MEDIUM_RISK_KEYWORDS if keyword in normalized)

    if high_hits >= 2 or "pora" in normalized:
        risk_level = "Yuqori"
        priority = "Tezkor"
    elif high_hits == 1 or medium_hits >= 2:
        risk_level = "O'rta"
        priority = "Muhim"
    else:
        risk_level = "Past"
        priority = "Rejalashtirilgan"

    keywords = _extract_keywords(message_text)
    route_to = ROUTE_BY_CATEGORY.get(best_category, "Operator ko'rib chiqishi")
    summary = message_text.strip().replace("\n", " ")
    if len(summary) > 220:
        summary = f"{summary[:217]}..."

    analysis = {
        "category": best_category,
        "risk_level": risk_level,
        "priority": priority,
        "route_to": route_to,
        "summary": summary,
        "keywords": ", ".join(keywords) if keywords else "aniqlanmadi",
        "analysis_notes": (
            f"Tizim murojaatni '{best_category}' toifasiga ajratdi, "
            f"xavf darajasi '{risk_level}' deb baholandi."
        ),
    }
    logger.info("Appeal analyzed locally: %s", json.dumps(analysis, ensure_ascii=False))
    return analysis
