from fastapi import APIRouter, Depends, HTTPException
from openai import RateLimitError, APITimeoutError, APIConnectionError, APIStatusError
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
from app.db.database import get_db
from app.services.retrieval import retrieve_chunks
from app.models.document import Document
from app.services.llm_service import generate_answer

logger = logging.getLogger(__name__)



router = APIRouter(
    prefix="/query",
    tags=["query"]
)


class QueryRequest(BaseModel):
    document_id: int
    question: str


@router.post("/")
def query_document(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    # Make sure the document exists
    document = (
        db.query(Document)
        .filter(Document.id == request.document_id)
        .first()
    )

    if document is None:
        logger.warning(f"no document with request id:{request.document_id} found")
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    # Retrieve the most relevant chunks
    chunks = retrieve_chunks(
        question=request.question,
        document_id=request.document_id,
        db=db
    )

    #create one string from three of the most relevant chunks to the query requests question
    context = "\n\n".join(chunk.content for chunk in chunks)

    try:
        answer = generate_answer(
        question=request.question,
        context=context
        )

    except RateLimitError:
        raise HTTPException(
        status_code=503,
        detail="ASK-AI is temporarily unavailable. Please try again later."
        )

    except APITimeoutError:
        raise HTTPException(
        status_code=504,
        detail="The AI service took too long to respond."
    )

    except APIConnectionError:
        raise HTTPException(
        status_code=503,
        detail="Unable to connect to the AI service."
    )

    except APIStatusError:
        raise HTTPException(
        status_code=502,
        detail="The AI service encountered an error."
    )
    


    return {
        "document_id": request.document_id,
        "question": request.question,
        "chunks": [
            {
                "chunk_index": chunk.chunk_index,
                "content": chunk.content
            }
            for chunk in chunks
        ],
        "answer": answer
    }


