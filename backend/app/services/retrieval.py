from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.services.embeddings import create_embedding


def retrieve_chunks(
    question: str,
    document_id: int,
    db: Session,
    limit: int = 3
) -> list[DocumentChunk]:

    # Turn the user's question into a 384-dimensional embedding
    question_embedding = create_embedding(question)

    # Search only chunks belonging to the selected document
    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document_id,
            DocumentChunk.embedding.is_not(None)
        )
        .order_by(
            DocumentChunk.embedding.cosine_distance(question_embedding)
        )
        .limit(limit)
        .all()
    )

    return chunks