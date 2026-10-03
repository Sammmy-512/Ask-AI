from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.document import Document


router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)


@router.post("/")
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    document = Document(filename=file.filename)

    db.add(document)
    db.commit()
    db.refresh(document)

    return document

