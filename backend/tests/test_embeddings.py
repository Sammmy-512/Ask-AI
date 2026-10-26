from unittest.mock import Mock

import pytest
from app.services import embeddings


def test_create_embedding_returns_vector_and_disables_progress(monkeypatch):
    fake_model = Mock()
    fake_model.encode.return_value.tolist.return_value = [0.1] * 384
    monkeypatch.setattr(embeddings, 'model', fake_model)

    result = embeddings.create_embedding('What is ASK-AI?')

    assert isinstance(result, list)
    assert len(result) == 384
    assert result[0] == 0.1
    fake_model.encode.assert_called_once_with('What is ASK-AI?', show_progress_bar=False)


def test_create_embedding_preserves_empty_input(monkeypatch):
    fake_model = Mock()
    fake_model.encode.return_value.tolist.return_value = [0.0] * 384
    monkeypatch.setattr(embeddings, 'model', fake_model)

    result = embeddings.create_embedding('')

    assert result == [0.0] * 384
    fake_model.encode.assert_called_once_with('', show_progress_bar=False)


def test_model_failure_propagates(monkeypatch):
    fake_model = Mock()
    fake_model.encode.side_effect = RuntimeError('embedding unavailable')
    monkeypatch.setattr(embeddings, 'model', fake_model)

    with pytest.raises(RuntimeError, match='embedding unavailable'):
        embeddings.create_embedding('Question')
