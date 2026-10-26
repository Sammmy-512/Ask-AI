from unittest.mock import MagicMock
from datetime import datetime, timezone

import fitz
import pytest


def make_pdf(text="ASK-AI is a document question answering application.", pages=1):
    """Generate a real PDF in memory."""
    pdf = fitz.open()

    for _ in range(pages):
        page = pdf.new_page()
        if text:
            page.insert_text((72, 72), text)

    data = pdf.tobytes()
    pdf.close()
    return data


def upload(client, filename, content, content_type):
    return client.post(
        "/documents/",
        files={
            "file": (filename, content, content_type)
        }
    )


@pytest.mark.parametrize(
    "filename,content_type,content",
    [
        ("image.png", "image/png", b"\x89PNG\r\n\x1a\n"),
        ("photo.jpg", "image/jpeg", b"\xff\xd8\xff"),
        ("notes.txt", "text/plain", b"Hello world"),
        (
            "report.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"not a real docx"
        ),
        ("data.json", "application/json", b'{"hello": "world"}'),
        ("archive.zip", "application/zip", b"PK\x03\x04"),
    ]
)
def test_unsupported_file_types(
    client, filename, content_type, content
):
    response = upload(
        client, filename, content, content_type
    )

    assert response.status_code == 415
    assert response.json()["detail"] == (
        "Only PDF documents are supported."
    )


def test_missing_file(client):
    response = client.post("/documents/")

    assert response.status_code == 422


def test_wrong_form_field(client):
    response = client.post(
        "/documents/",
        files={
            "document": (
                "test.pdf",
                make_pdf(),
                "application/pdf"
            )
        }
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"This is not a PDF",
        b"%PDF-1.7\ncorrupted content",
        b"\x00\x01\x02\x03",
    ]
)
def test_corrupted_pdf(client, content):
    response = upload(
        client,
        "corrupted.pdf",
        content,
        "application/pdf"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid or corrupted PDF."
    )


def test_pdf_without_extractable_text(client):
    response = upload(
        client,
        "blank.pdf",
        make_pdf(text=""),
        "application/pdf"
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "PDF contains no extractable text."
    )


def test_pdf_page_limit(client, monkeypatch):
    import app.api.documents as documents_api

    fake_pdf = MagicMock()
    fake_pdf.page_count = 5001

    monkeypatch.setattr(
        documents_api.fitz,
        "open",
        lambda **kwargs: fake_pdf
    )

    response = upload(
        client,
        "huge.pdf",
        b"fake pdf content",
        "application/pdf"
    )

    assert response.status_code == 413
    assert fake_pdf.close.called


def test_valid_pdf_upload(client, mock_db, monkeypatch):
    import app.api.documents as documents_api

    monkeypatch.setattr(
        documents_api,
        "create_embedding",
        lambda text: [0.1] * 384
    )

    def refresh_document(document):
        document.id = 42
        document.created_at = datetime.now(timezone.utc)

    def flush_document():
        # Simulates SQLAlchemy assigning an ID after flush.
        for call in mock_db.add.call_args_list:
            obj = call.args[0]
            if hasattr(obj, "filename"):
                obj.id = 42

    mock_db.flush.side_effect = flush_document
    mock_db.refresh.side_effect = refresh_document

    response = upload(
        client,
        "valid.pdf",
        make_pdf(),
        "application/pdf"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 42
    assert data["filename"] == "valid.pdf"
    assert data["chunks"] >= 1
    assert "created_at" in data

    mock_db.commit.assert_called_once()


def test_embedding_failure_rolls_back(
    client, mock_db, monkeypatch
):
    import app.api.documents as documents_api

    def failing_embedding(text):
        raise RuntimeError("Embedding failed")

    monkeypatch.setattr(
        documents_api,
        "create_embedding",
        failing_embedding
    )

    response = upload(
        client,
        "valid.pdf",
        make_pdf(),
        "application/pdf"
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "An error occurred while processing the PDF."
    )

    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()


def test_database_commit_failure(
    client, mock_db, monkeypatch
):
    import app.api.documents as documents_api

    monkeypatch.setattr(
        documents_api,
        "create_embedding",
        lambda text: [0.1] * 384
    )

    mock_db.commit.side_effect = RuntimeError(
        "Database commit failed"
    )

    response = upload(
        client,
        "valid.pdf",
        make_pdf(),
        "application/pdf"
    )

    assert response.status_code == 500
    mock_db.rollback.assert_called_once()


def test_successful_upload_stores_all_chunks(
    client, mock_db, monkeypatch
):
    import app.api.documents as documents_api
    from app.models.document_chunk import DocumentChunk

    monkeypatch.setattr(
        documents_api,
        "chunk_text",
        lambda text: ["chunk one", "chunk two", "chunk three"]
    )

    monkeypatch.setattr(
        documents_api,
        "create_embedding",
        lambda text: [0.1] * 384
    )

    def flush_document():
        for call in mock_db.add.call_args_list:
            obj = call.args[0]
            if hasattr(obj, "filename"):
                obj.id = 42

    def refresh_document(document):
        document.created_at = datetime.now(timezone.utc)

    mock_db.flush.side_effect = flush_document
    mock_db.refresh.side_effect = refresh_document

    response = upload(
        client,
        "valid.pdf",
        make_pdf(),
        "application/pdf"
    )

    assert response.status_code == 200
    assert response.json()["chunks"] == 3

    saved_chunks = [
        call.args[0]
        for call in mock_db.add.call_args_list
        if isinstance(call.args[0], DocumentChunk)
    ]

    assert len(saved_chunks) == 3
    assert [chunk.chunk_index for chunk in saved_chunks] == [0, 1, 2]
    assert all(chunk.document_id == 42 for chunk in saved_chunks)