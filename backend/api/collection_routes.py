"""
Collection API routes — CRUD for learning collections.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from models import get_db, Collection, CollectionItem, Video

router = APIRouter(prefix="/api/collections", tags=["collections"])


class CreateCollectionRequest(BaseModel):
    name: str
    description: Optional[str] = None


class AddVideoRequest(BaseModel):
    video_id: str
    notes: Optional[str] = None


@router.post("")
async def create_collection(req: CreateCollectionRequest, db: Session = Depends(get_db)):
    collection = Collection(name=req.name, description=req.description)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return {
        "id": collection.id,
        "name": collection.name,
        "description": collection.description,
    }


@router.get("")
async def list_collections(db: Session = Depends(get_db)):
    collections = db.query(Collection).order_by(Collection.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "video_count": len(c.items),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in collections
    ]


@router.get("/{collection_id}")
async def get_collection(collection_id: str, db: Session = Depends(get_db)):
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    videos = []
    for item in collection.items:
        v = item.video
        videos.append({
            "item_id": item.id,
            "video_id": v.id,
            "title": v.title,
            "source": v.source,
            "duration": v.duration,
            "thumbnail": v.thumbnail,
            "channel": v.channel,
            "status": v.status,
            "notes": item.notes,
            "added_at": item.added_at.isoformat() if item.added_at else None,
        })

    return {
        "id": collection.id,
        "name": collection.name,
        "description": collection.description,
        "videos": videos,
    }


@router.post("/{collection_id}/add")
async def add_video_to_collection(
    collection_id: str,
    req: AddVideoRequest,
    db: Session = Depends(get_db),
):
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    video = db.query(Video).filter(Video.id == req.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check duplicate
    existing = (
        db.query(CollectionItem)
        .filter(CollectionItem.collection_id == collection_id, CollectionItem.video_id == req.video_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Video already in collection")

    item = CollectionItem(
        collection_id=collection_id,
        video_id=req.video_id,
        notes=req.notes,
    )
    db.add(item)
    db.commit()
    return {"success": True, "item_id": item.id}


@router.delete("/{collection_id}/remove/{video_id}")
async def remove_video_from_collection(
    collection_id: str,
    video_id: str,
    db: Session = Depends(get_db),
):
    item = (
        db.query(CollectionItem)
        .filter(CollectionItem.collection_id == collection_id, CollectionItem.video_id == video_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return {"success": True}


@router.delete("/{collection_id}")
async def delete_collection(collection_id: str, db: Session = Depends(get_db)):
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    db.delete(collection)
    db.commit()
    return {"success": True}
