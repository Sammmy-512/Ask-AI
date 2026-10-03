from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking import chunk_text


router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    contents = await file.read()

    text = contents.decode("utf-8")

    chunks = chunk_text(text)

    document = Document(filename=file.filename)

    db.add(document)
    
    db.flush()

    for index, chunk in enumerate(chunks):
        document_chunk = DocumentChunk(
        document_id=document.id,
        content=chunk,
        chunk_index=index
    )

        db.add(document_chunk)

    db.commit()
    db.refresh(document)

    return  {
        "id": document.id,
        "filename": document.filename,
        "created_at": document.created_at,
        "chunks": len(chunks)
    }

