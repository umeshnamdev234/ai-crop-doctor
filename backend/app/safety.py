"""Deterministic safety net, applied before the model answers.

Pesticide poisoning is a real risk on farms. If a message suggests someone swallowed,
inhaled or was splashed with a farm chemical (or is thinking of self-harm with one),
the API flags it so every client shows an emergency banner, whatever the model says.
"""
import re

EMERGENCY_NOTICE = (
    "This may be pesticide poisoning, which is a medical emergency. Call 108 (ambulance) now, "
    "move the person to fresh air, remove contaminated clothes, wash skin with plenty of water, "
    "and take the pesticide container/label to the hospital. Do not try home remedies or make them vomit."
)

SAFETY_REMINDER = (
    "Always follow the label dose, wear gloves and a mask while spraying, keep children and animals away, "
    "and respect the pre-harvest waiting period."
)

_EMERGENCY = re.compile(
    # English
    r"(drank|swallowed|ingested|consumed|drinking|accidentally (drank|ate|swallowed))\s+(\w+\s+){0,3}"
    r"(pesticide|insecticide|herbicide|weedicide|fungicide|poison|chemical|spray|keetnashak)"
    r"|pesticide poisoning|poisoned by (pesticide|spray|chemical)|inhaled (pesticide|spray|chemical)"
    r"|(fainted|unconscious|vomiting|dizzy|breathless|fits|seizure)\s+(\w+\s+){0,4}(after|while)\s+spray"
    r"|spray(ed|ing)?\s+(\w+\s+){0,3}(in|into) (my |his |her )?eyes?"
    r"|suicid|kill myself|end my life|want to die"
    # Hindi / Hinglish
    r"|ज़हर|जहर|कीटनाशक\s*(पी|खा)|दवा\s*पी\s*(ली|लिया)|ज़हर\s*खा|बेहोश|आत्महत्या|मरना\s*चाहता"
    r"|zeher|jahar|keetnashak\s*(pi|kha)|dawa\s*pi\s*(li|liya)|behosh|atmahatya",
    re.IGNORECASE,
)


def detect_emergency(text: str) -> bool:
    return bool(text and _EMERGENCY.search(text))


EMERGENCY_NOTICE_HI = (
    "यह कीटनाशक ज़हर हो सकता है, जो मेडिकल इमरजेंसी है। तुरंत 108 (एम्बुलेंस) पर कॉल करें। व्यक्ति को खुली हवा में ले जाएं, "
    "दूषित कपड़े उतारें, त्वचा को खूब पानी से धोएं, और दवा का डिब्बा/लेबल अस्पताल ले जाएं। घरेलू उपाय न करें और उल्टी न कराएं।"
)
SAFETY_REMINDER_HI = (
    "हमेशा लेबल पर लिखी मात्रा का पालन करें, छिड़काव करते समय दस्ताने और मास्क पहनें, बच्चों और पशुओं को दूर रखें, "
    "और कटाई से पहले की प्रतीक्षा अवधि का पालन करें।"
)
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def wants_hindi(text: str, reply_language: str = "auto") -> bool:
    return reply_language == "hi" or (reply_language == "auto" and bool(_DEVANAGARI.search(text or "")))


def emergency_notice(text: str, reply_language: str = "auto") -> str:
    return EMERGENCY_NOTICE_HI if wants_hindi(text, reply_language) else EMERGENCY_NOTICE


def safety_reminder(text: str, reply_language: str = "auto") -> str:
    return SAFETY_REMINDER_HI if wants_hindi(text, reply_language) else SAFETY_REMINDER
