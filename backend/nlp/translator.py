# Simple stub for now (returns input). Plug your preferred API later.
# You can swap to googletrans or a paid API (DeepL/GCP) when ready.
def translate_to_english(text: str, src_lang: str) -> str:
    if not text: 
        return text
    if src_lang.lower().startswith("en"):
        return text
    # TODO: integrate your translator here
    return text  # placeholder (no-op)
