import pytest
from app.services.chunking import chunk_text


def test_empty_and_whitespace():
    assert chunk_text('') == []
    assert chunk_text(' \n\n \t ') == []


def test_short_paragraph():
    assert chunk_text('  Hello world.  ') == ['Hello world.']


def test_paragraphs_fit_together():
    assert chunk_text('First paragraph.\n\nSecond paragraph.', max_size=100) == [
        'First paragraph.\n\nSecond paragraph.'
    ]


def test_paragraphs_split_at_limit():
    assert chunk_text('Alpha.\n\nBravo.', max_size=10) == ['Alpha.', 'Bravo.']


def test_windows_newlines_normalized():
    assert chunk_text('Alpha.\r\n\r\nBravo.', max_size=100) == [
        'Alpha.\n\nBravo.'
    ]


def test_empty_paragraphs_ignored():
    assert chunk_text('\n\n\n\nAlpha.\n\n\n\n') == ['Alpha.']


def test_long_paragraph_split_at_sentence_boundaries():
    text = 'First sentence. Second sentence! Third sentence?'
    assert chunk_text(text, max_size=24) == [
        'First sentence.', 'Second sentence!', 'Third sentence?'
    ]


def test_oversized_sentence_hard_split():
    assert chunk_text('ABCDEFGHIJKL', max_size=5) == ['ABCDE', 'FGHIJ', 'KL']


def test_oversized_sentence_flushes_previous_chunk():
    assert chunk_text('Hi.\n\nABCDEFGHIJKL', max_size=5) == [
        'Hi.', 'ABCDE', 'FGHIJ', 'KL'
    ]


def test_every_chunk_respects_maximum_for_representative_text():
    text = 'One. Two. Three. Four. Five. Six. Seven. Eight.'
    chunks = chunk_text(text, max_size=15)
    assert chunks
    assert all(0 < len(chunk) <= 15 for chunk in chunks)
    assert ' '.join(chunks) == text

