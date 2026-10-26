from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
import fitz
from app.db.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking import chunk_text
from app.services.embeddings import create_embedding
import logging
import time

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    start_time = time.perf_counter()
    logger.info("PDF upload started")
     # Only accept PDFs
    if file.content_type != "application/pdf":
        logger.warning("PDF upload rejected | reason=unsupported_file_type")

        raise HTTPException(
            status_code=415,
            detail="Only PDF documents are supported."
        )

    contents = await file.read()

    try:
        pdf = fitz.open(stream=contents, filetype="pdf")
    except Exception:
        logger.warning("PDF upload rejected | reason=invalid_pdf")
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted PDF."
        )

    page_count = pdf.page_count

    if page_count >= 5000:
        pdf.close()
        logger.warning("PDF upload rejected | reason=page_limit_exceeded | pages=%d", page_count)
        raise HTTPException(
            status_code=413,
            detail="PDF cannot contain more than 5,000 pages."
        )

    text = ""

    for page in pdf:
        text += page.get_text()
        text += "\n\n"

    pdf.close()

    if not text.strip():
        logger.warning("PDF upload rejected | reason=no_extractable_text")

        raise HTTPException(
        status_code=422,
        detail="PDF contains no extractable text."
        )
    
    chunks = chunk_text(text)



    try:
        document = Document(
        filename=file.filename,
        page_count=page_count
        )

        db.add(document)
        db.flush()

        for index, chunk in enumerate(chunks):
            embedding = create_embedding(chunk)

            document_chunk = DocumentChunk(
            document_id=document.id,
            content=chunk,
            chunk_index=index,
            embedding=embedding
        )

            db.add(document_chunk)

        db.commit()
        db.refresh(document)

        logger.info(
                    "PDF processed | pages=%d | chunks=%d | duration=%.2fs",
                    page_count,
                    len(chunks),
                    time.perf_counter() - start_time
                    )

        return  {
                "id": document.id,
                "filename": document.filename,
                "created_at": document.created_at,
                "chunks": len(chunks)
            }
            

    except Exception:
        db.rollback()
        logger.exception("PDF ingestion failed")

        raise HTTPException(
        status_code=500,
        detail="An error occurred while processing the PDF."
        )





