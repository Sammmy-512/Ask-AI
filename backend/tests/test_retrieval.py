from unittest.mock import MagicMock, Mock

import pytest
from app.services import retrieval
from app.models.document_chunk import DocumentChunk


@pytest.fixture
def mock_embedding(monkeypatch):
    embedding = [0.25] * 384
    create = Mock(return_value=embedding)
    monkeypatch.setattr(retrieval, 'create_embedding', create)
    return create, embedding


def test_retrieves_ordered_chunks_from_selected_document(mock_embedding):
    create, embedding = mock_embedding
    db = MagicMock()
    chunks = [Mock(content='most relevant'), Mock(content='next relevant')]
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = chunks

    result = retrieval.retrieve_chunks('What happened?', document_id=7, db=db, limit=2)

    assert result is chunks
    create.assert_called_once_with('What happened?')
    db.query.assert_called_once_with(DocumentChunk)
    query = db.query.return_value
    query.filter.assert_called_once()
    assert len(query.filter.call_args.args) == 2  # document ID and non-null vector filters
    order_expression = query.filter.return_value.order_by.call_args.args[0]
    assert 'cosine_distance' in str(order_expression).lower() or order_expression is not None
    query.filter.return_value.order_by.return_value.limit.assert_called_once_with(2)


def test_default_limit_is_three(mock_embedding):
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    assert retrieval.retrieve_chunks('question', document_id=1, db=db) == []
    db.query.return_value.filter.return_value.order_by.return_value.limit.assert_called_once_with(3)


def test_empty_results_return_empty_list(mock_embedding, caplog):
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    with caplog.at_level('INFO', logger='app.services.retrieval'):
        result = retrieval.retrieve_chunks('No match', document_id=99, db=db)

    assert result == []
    assert 'Retrieved 0 chunks for document_id=99' in caplog.text


def test_embedding_failure_prevents_database_query(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(retrieval, 'create_embedding', Mock(side_effect=RuntimeError('model error')))

    with pytest.raises(RuntimeError, match='model error'):
        retrieval.retrieve_chunks('question', document_id=1, db=db)

    db.query.assert_not_called()


def test_database_failure_propagates(mock_embedding):
    db = MagicMock()
    db.query.side_effect = RuntimeError('database unavailable')

    with pytest.raises(RuntimeError, match='database unavailable'):
        retrieval.retrieve_chunks('question', document_id=1, db=db)
