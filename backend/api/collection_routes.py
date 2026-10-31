"""
Collection API routes — CRUD for learning collections.
Per-user isolation via user_id column.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from models import get_db, Collection, CollectionItem, Video
from middleware.auth import require_auth
from api.video_routes import _can_view

router = APIRouter(prefix="/api/collections", tags=["collections"])


class CreateCollectionRequest(BaseModel):
    name: str
    description: Optional[str] = None


class AddVideoRequest(BaseModel):
    video_id: str
    notes: Optional[str] = None


class UpdateCollectionRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    is_official: Optional[bool] = None  # admin only


def _get_user_id(user: dict) -> str:
    return user.get("sub", "")


def _is_admin(user: dict) -> bool:
    return user.get("role") == "admin"


@router.post("")
async def create_collection(req: CreateCollectionRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    collection = Collection(name=req.name, description=req.description, user_id=_get_user_id(user))
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return {"id": collection.id, "name": collection.name, "description": collection.description}


@router.get("")
async def list_collections(db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    collections = (
        db.query(Collection)
        .filter(Collection.user_id == user_id)
        .order_by(Collection.created_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "video_count": len(c.items),
            "is_public": bool(c.is_public),
            "is_official": bool(c.is_official),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in collections
    ]


@router.patch("/{collection_id}")
async def update_collection(collection_id: str, req: UpdateCollectionRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    collection = db.query(Collection).filter(Collection.id == collection_id, Collection.user_id == user_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if req.name is not None and req.name.strip():
        collection.name = req.name.strip()
    if req.description is not None:
        collection.description = req.description.strip() or None
    if req.is_public is not None:
        collection.is_public = req.is_public
    if req.is_official is not None:
        if not _is_admin(user):
            raise HTTPException(status_code=403, detail="Admin only")
        collection.is_official = req.is_official

    db.commit()
    return {
        "success": True,
        "id": collection.id,
        "name": collection.name,
        "description": collection.description,
        "is_public": bool(collection.is_public),
        "is_official": bool(collection.is_official),
    }


@router.get("/{collection_id}")
async def get_collection(collection_id: str, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    collection = db.query(Collection).filter(Collection.id == collection_id, Collection.user_id == user_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    videos = []
    for item in collection.items:
        v = item.video
        videos.append({
            "item_id": item.id, "video_id": v.id, "title": v.title, "source": v.source,
            "duration": v.duration, "thumbnail": v.thumbnail, "channel": v.channel,
            "status": v.status, "notes": item.notes,
            "added_at": item.added_at.isoformat() if item.added_at else None,
        })

    return {"id": collection.id, "name": collection.name, "description": collection.description, "videos": videos}


@router.post("/{collection_id}/add")
async def add_video_to_collection(collection_id: str, req: AddVideoRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    collection = db.query(Collection).filter(Collection.id == collection_id, Collection.user_id == user_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    video = db.query(Video).filter(Video.id == req.video_id).first()
    if not video or not _can_view(db, user, video):
        raise HTTPException(status_code=404, detail="Video not found")

    existing = db.query(CollectionItem).filter(
        CollectionItem.collection_id == collection_id, CollectionItem.video_id == req.video_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Video already in collection")

    item = CollectionItem(collection_id=collection_id, video_id=req.video_id, notes=req.notes)
    db.add(item)
    db.commit()
    return {"success": True, "item_id": item.id}


@router.delete("/{collection_id}/remove/{video_id}")
async def remove_video_from_collection(collection_id: str, video_id: str, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    collection = db.query(Collection).filter(Collection.id == collection_id, Collection.user_id == user_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    item = db.query(CollectionItem).filter(
        CollectionItem.collection_id == collection_id, CollectionItem.video_id == video_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return {"success": True}


@router.delete("/{collection_id}")
async def delete_collection(collection_id: str, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    collection = db.query(Collection).filter(Collection.id == collection_id, Collection.user_id == user_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    db.delete(collection)
    db.commit()
    return {"success": True}
