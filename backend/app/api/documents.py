from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
import fitz
from app.db.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking import chunk_text
from app.services.embeddings import create_embedding


router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
     # Only accept PDFs
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=415,
            detail="Only PDF documents are supported."
        )

    contents = await file.read()

    try:
        pdf = fitz.open(stream=contents, filetype="pdf")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted PDF."
        )

    page_count = pdf.page_count

    if page_count > 5000:
        pdf.close()

        raise HTTPException(
            status_code=413,
            detail="PDF cannot contain more than 5,000 pages."
        )

    text = ""

    for page in pdf:
        text += page.get_text()
        text += "\n\n"

    pdf.close()


    
    print(repr(text[:2000]))
    chunks = chunk_text(text)
    print("Number of chunks:", len(chunks))

    for i, chunk in enumerate(chunks):
        print(i, len(chunk))

    document = Document(filename=file.filename, page_count = page_count)

    db.add(document)
    
    db.flush()

    for index, chunk in enumerate(chunks):
        embedding = create_embedding(chunk)
        document_chunk = DocumentChunk(
        document_id=document.id,
        content=chunk,
        chunk_index=index,
        embedding = embedding
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

