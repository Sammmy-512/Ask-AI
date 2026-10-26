from unittest.mock import MagicMock

import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    RateLimitError,
)
from httpx import Request, Response


QUERY_URL = "/query/"


def make_request(document_id=1, question="Summarize this document"):
    return {
        "document_id": document_id,
        "question": question
    }


@pytest.fixture
def existing_document(mock_db):
    document = MagicMock()
    document.id = 1

    mock_db.query.return_value.filter.return_value.first.return_value = document

    return document


def test_valid_query(
    client, existing_document, monkeypatch
):
    import app.api.query as query_api

    chunk = MagicMock()
    chunk.content = "ASK-AI processes PDF documents."
    chunk.chunk_index = 0

    monkeypatch.setattr(
        query_api,
        "retrieve_chunks",
        lambda **kwargs: [chunk]
    )

    monkeypatch.setattr(
        query_api,
        "generate_answer",
        lambda **kwargs: "ASK-AI processes PDFs."
    )

    response = client.post(
        QUERY_URL,
        json=make_request()
    )

    assert response.status_code == 200

    data = response.json()

    assert data["document_id"] == 1
    assert data["question"] == "Summarize this document"
    assert data["answer"] == "ASK-AI processes PDFs."
    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["chunk_index"] == 0


def test_nonexistent_document(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.post(
        QUERY_URL,
        json=make_request(document_id=999999)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"document_id": 1},
        {"question": "Hello"},
        {"document_id": "invalid", "question": "Hello"},
        {"document_id": None, "question": "Hello"},
        {"document_id": 1, "question": None},
        {"document_id": 1, "question": ["invalid"]},
    ]
)
def test_invalid_query_payload(client, payload):
    response = client.post(
        QUERY_URL,
        json=payload
    )

    assert response.status_code == 422


def test_invalid_json(client):
    response = client.post(
        QUERY_URL,
        content=b'{"document_id": 1, invalid}',
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422


def setup_mock_retrieval(monkeypatch):
    import app.api.query as query_api

    chunk = MagicMock()
    chunk.content = "Document context"
    chunk.chunk_index = 0

    monkeypatch.setattr(
        query_api,
        "retrieve_chunks",
        lambda **kwargs: [chunk]
    )

    return query_api


def test_openai_timeout(
    client, existing_document, monkeypatch
):
    query_api = setup_mock_retrieval(monkeypatch)

    def failing_llm(**kwargs):
        raise APITimeoutError(
            request=Request("POST", "https://api.openai.com")
        )

    monkeypatch.setattr(
        query_api, "generate_answer", failing_llm
    )

    response = client.post(
        QUERY_URL,
        json=make_request()
    )

    assert response.status_code == 504
    assert response.json()["detail"] == (
        "The AI service took too long to respond."
    )


def test_openai_connection_failure(
    client, existing_document, monkeypatch
):
    query_api = setup_mock_retrieval(monkeypatch)

    def failing_llm(**kwargs):
        raise APIConnectionError(
            request=Request("POST", "https://api.openai.com")
        )

    monkeypatch.setattr(
        query_api, "generate_answer", failing_llm
    )

    response = client.post(
        QUERY_URL,
        json=make_request()
    )

    assert response.status_code == 503


def test_openai_rate_limit(
    client, existing_document, monkeypatch
):
    query_api = setup_mock_retrieval(monkeypatch)

    def failing_llm(**kwargs):
        raise RateLimitError(
            "Rate limit exceeded",
            response=Response(
                429,
                request=Request("POST", "https://api.openai.com")
            ),
            body=None
        )

    monkeypatch.setattr(
        query_api, "generate_answer", failing_llm
    )

    response = client.post(
        QUERY_URL,
        json=make_request()
    )

    assert response.status_code == 503


def test_openai_upstream_error(
    client, existing_document, monkeypatch
):
    query_api = setup_mock_retrieval(monkeypatch)

    def failing_llm(**kwargs):
        raise APIStatusError(
            "Upstream service error",
            response=Response(
                500,
                request=Request("POST", "https://api.openai.com")
            ),
            body=None
        )

    monkeypatch.setattr(
        query_api, "generate_answer", failing_llm
    )

    response = client.post(
        QUERY_URL,
        json=make_request()
    )

    assert response.status_code == 502


def test_request_id_header(client):
    response = client.get("/nonexistent")

    assert response.status_code == 404
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]
