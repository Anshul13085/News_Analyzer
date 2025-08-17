from langdetect import detect
def detect_language(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "en"
