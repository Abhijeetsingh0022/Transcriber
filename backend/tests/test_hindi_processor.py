import pytest
from engine.hindi_processor import clean_perso_arabic_bleed, HINDI_LEXICAL_PROMPT


def test_clean_perso_arabic_bleed_fixes_rogue_glyphs():
    # Test Perso-Arabic / Urdu character replacements in Devanagari words
    dirty_text = "उसे एक अंजान कम्पोनेंट मि\u0644ता है और वह अपनी टीचर से मदद मांग\u062Aा ह \u06C2।"
    cleaned = clean_perso_arabic_bleed(dirty_text)
    
    assert "\u0644" not in cleaned  # Arabic Lam stripped/mapped to ल
    assert "\u062A" not in cleaned  # Arabic Teh stripped/mapped to त
    assert "\u06C2" not in cleaned  # Urdu Heh goal stripped/mapped
    assert "मिलता" in cleaned
    assert "मांगता" in cleaned


def test_clean_perso_arabic_bleed_handles_empty_or_clean_text():
    assert clean_perso_arabic_bleed("") == ""
    assert clean_perso_arabic_bleed("नमस्ते बच्चों") == "नमस्ते बच्चों"


def test_hindi_lexical_prompt_contains_anchor_terms():
    assert "आईसी" in HINDI_LEXICAL_PROMPT
    assert "सर्किट" in HINDI_LEXICAL_PROMPT
    assert "इनपुट" in HINDI_LEXICAL_PROMPT
    assert "आउटपुट" in HINDI_LEXICAL_PROMPT
