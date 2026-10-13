"""
Unit and integration tests for syntactic sentence continuation bonding
and accurate Narrator/Character identification in speaker attribution.
Verifies both Tier 1 (local pragmatic state graph) and Tier 2 (LLM reasoner).
"""

import pytest
from engine.speaker_id import (
    is_sentence_continuation,
    identify_speakers_for_segments,
    extract_vocatives_and_mentions,
)


def test_is_sentence_continuation_comma_split():
    """Segment ending with comma continuing into lowercase or coordinate list is a sentence continuation."""
    prev = {"text": "Today we'll learn about Ohm's law and how voltage,", "start_time": 0.0, "end_time": 5.8}
    curr = {"text": "current and resistance are related in an electric circuit.", "start_time": 6.0, "end_time": 9.0}
    assert is_sentence_continuation(prev, curr) is True


def test_is_sentence_continuation_raw_unpunctuated_split():
    """Segment ending without punctuation continuing into ongoing clause."""
    prev = {"text": "Ohm's law explains how voltage, current and resistance", "start_time": 10.0, "end_time": 13.0}
    curr = {"text": "are related in an electric circuit.", "start_time": 13.2, "end_time": 16.0}
    assert is_sentence_continuation(prev, curr) is True


def test_is_sentence_continuation_conjunction_continuation():
    """Segment ending with comma continuing into conjunction."""
    prev = {"text": "In a simple circuit, the battery provides voltage,", "start_time": 1.0, "end_time": 3.0}
    curr = {"text": "and the wires carry current.", "start_time": 3.2, "end_time": 5.0}
    assert is_sentence_continuation(prev, curr) is True


def test_is_sentence_continuation_terminal_punctuation_dialogue():
    """Segment ending with terminal punctuation followed by direct dialogue is NOT a continuation."""
    prev = {"text": "current and resistance are related in an electric circuit.", "start_time": 6.0, "end_time": 9.0}
    curr = {"text": "Teacher, how can I know how much current flows through this LED?", "start_time": 9.0, "end_time": 13.0}
    assert is_sentence_continuation(prev, curr) is False


def test_is_sentence_continuation_large_time_gap():
    """Segments with large gap (> 2.5s) are not mid-sentence continuations."""
    prev = {"text": "Today we'll learn about Ohm's law and how voltage,", "start_time": 0.0, "end_time": 5.0}
    curr = {"text": "current and resistance are related in an electric circuit.", "start_time": 10.0, "end_time": 13.0}
    assert is_sentence_continuation(prev, curr) is False


def test_narrator_intro_sentence_continuation_tier1():
    """
    Direct regression test for user report:
    Seg 0: 'Hello students, welcome to Edinoverse. Today we'll learn about Ohm's law and how voltage,'
    Seg 1: 'current and resistance are related in an electric circuit.'
    Seg 2: 'Teacher, how can I know how much current flows through this LED?'
    Seg 3: 'Good question Kunal. First we need to understand voltage, current and resistance.'
    
    Verifies that Seg 1 stays bound to Narrator and Kunal/Teacher are accurately recognized.
    """
    segments = [
        {
            "segment_index": 0,
            "start_time": 0.0,
            "end_time": 5.8,
            "text": "Hello students, welcome to Edinoverse. Today we'll learn about Ohm's law and how voltage,",
        },
        {
            "segment_index": 1,
            "start_time": 6.0,
            "end_time": 9.0,
            "text": "current and resistance are related in an electric circuit.",
        },
        {
            "segment_index": 2,
            "start_time": 9.0,
            "end_time": 13.0,
            "text": "Teacher, how can I know how much current flows through this LED?",
        },
        {
            "segment_index": 3,
            "start_time": 13.5,
            "end_time": 18.0,
            "text": "Good question Kunal. First we need to understand voltage, current and resistance.",
        },
    ]

    res = identify_speakers_for_segments(segments, num_speakers=3, tier="tier1")
    assert res["success"] is True

    assignments = res["segment_assignments"]
    addressees = res["addressee_assignments"]
    spk_map = {s["speaker_label"]: s["display_name"] for s in res["speakers"]}

    # Seg 0 and Seg 1 MUST both be Narrator
    assert spk_map[assignments[0]] == "Narrator"
    assert spk_map[assignments[1]] == "Narrator"
    assert addressees[0] == "Audience"
    assert addressees[1] == "Audience"

    # Seg 2 must be Student/Kunal asking Teacher
    assert spk_map[assignments[2]] == "Kunal"
    assert addressees[2] == "Teacher"
    assert res["intent_assignments"][2] == "inquiry"

    # Seg 3 must be Teacher explaining to Kunal
    assert spk_map[assignments[3]] == "Teacher"
    assert addressees[3] == "Kunal"
    assert res["intent_assignments"][3] == "explanation"


def test_extract_vocatives_pedagogical_praise():
    """Verifies that 'Good question Kunal' extracts Kunal as a dynamic participant."""
    segments = [
        {"segment_index": 0, "text": "Teacher, what is this?"},
        {"segment_index": 1, "text": "Good question Kunal. This is a resistor."},
    ]
    data = extract_vocatives_and_mentions(segments)
    assert "Kunal" in data["names"]
    assert "Teacher" in data["honorifics"]


def test_acoustic_diarization_clustering():
    """Verifies that acoustic MFCC clustering accurately tags segments with distinct voice tracks."""
    import torch
    from engine.diarizer import tag_segments_with_acoustic_clusters

    sr = 16000
    t = torch.linspace(0, 10, sr * 10)
    # Two distinct synthetic voice frequencies
    v1 = torch.sin(2 * 3.14159 * 180 * t).unsqueeze(0)
    v2 = torch.sin(2 * 3.14159 * 550 * t).unsqueeze(0)
    audio = torch.cat([v1, v2], dim=1)

    segments = [
        {"start_time": 0.0, "end_time": 4.5, "text": "Hello students."},
        {"start_time": 5.0, "end_time": 9.5, "text": "Today we learn circuits."},
        {"start_time": 10.5, "end_time": 14.5, "text": "Teacher, how does this work?"},
        {"start_time": 15.0, "end_time": 19.5, "text": "Why is the bulb off?"},
    ]

    tagged = tag_segments_with_acoustic_clusters(audio, segments, num_speakers=2)
    assert tagged[0]["acoustic_cluster"] == tagged[1]["acoustic_cluster"]
    assert tagged[2]["acoustic_cluster"] == tagged[3]["acoustic_cluster"]
    assert tagged[0]["acoustic_cluster"] != tagged[2]["acoustic_cluster"]


def test_self_address_normalization():
    """Verifies that internal monologue or musing normalizes addressed_to from speaker's own name to 'Self'."""
    from engine.gemini_speaker_id import _parse_ai_character_response

    mock_result = {
        "characters": [{"name": "Kunal", "role": "Student"}],
        "turns": [
            {"segment_index": 0, "speaker": "Kunal", "addressed_to": "Kunal", "intent": "inquiry"}
        ]
    }
    segments = [{"start_time": 0.0, "end_time": 2.0, "text": "Hmm. Why did this bulb stop?"}]
    parsed = _parse_ai_character_response(mock_result, segments, "test")
    assert parsed["addressee_assignments"][0] == "Self"

