from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import AssetNode, User
from app.schemas.common import AssetNodeCreate, AssetNodeOut, AssetNodeUpdate, AssetTreeNode
from app.services.assets import build_asset_tree, can_move_asset_node, serialize_asset_node
from app.services.audit import write_audit_log

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/nodes", response_model=list[AssetNodeOut])
def list_asset_nodes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    nodes = (
        db.query(AssetNode)
        .options(joinedload(AssetNode.parent), joinedload(AssetNode.children), joinedload(AssetNode.machines))
        .order_by(AssetNode.name.asc())
        .all()
    )
    return [serialize_asset_node(node) for node in nodes]


@router.get("/tree", response_model=list[AssetTreeNode])
def get_asset_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return build_asset_tree(db)


@router.post("/nodes", response_model=AssetNodeOut)
def create_asset_node(
    payload: AssetNodeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "expert")),
):
    if payload.parent_id is not None:
        parent = db.query(AssetNode).filter(AssetNode.id == payload.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent hierarchy node not found")
    node = AssetNode(**payload.model_dump())
    db.add(node)
    db.flush()
    write_audit_log(
        db,
        "create_asset_node",
        "asset_node",
        user=current_user,
        entity_id=node.id,
        request=request,
        details=f"{node.node_type}:{node.name}",
    )
    db.commit()
    db.refresh(node)
    db.refresh(node)
    return serialize_asset_node(node)


@router.put("/nodes/{node_id}", response_model=AssetNodeOut)
def update_asset_node(
    node_id: int,
    payload: AssetNodeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "expert")),
):
    node = (
        db.query(AssetNode)
        .options(joinedload(AssetNode.parent), joinedload(AssetNode.children), joinedload(AssetNode.machines))
        .filter(AssetNode.id == node_id)
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Hierarchy node not found")
    if not can_move_asset_node(db, node, payload.parent_id):
        raise HTTPException(status_code=400, detail="Le parent choisi cree une boucle dans la hierarchie")
    if payload.parent_id is not None:
        parent = db.query(AssetNode).filter(AssetNode.id == payload.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent hierarchy node not found")

    node.name = payload.name
    node.node_type = payload.node_type
    node.parent_id = payload.parent_id
    write_audit_log(
        db,
        "update_asset_node",
        "asset_node",
        user=current_user,
        entity_id=node.id,
        request=request,
        details=f"{node.node_type}:{node.name}",
    )
    db.commit()
    db.refresh(node)
    db.refresh(node)
    return serialize_asset_node(node)


@router.delete("/nodes/{node_id}")
def delete_asset_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "expert")),
):
    node = (
        db.query(AssetNode)
        .options(joinedload(AssetNode.children), joinedload(AssetNode.machines))
        .filter(AssetNode.id == node_id)
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Hierarchy node not found")
    if node.children:
        raise HTTPException(status_code=400, detail="Supprimez ou deplacez d'abord les noeuds enfants")
    if node.machines:
        raise HTTPException(status_code=400, detail="Ce noeud est encore associe a des machines")

    node_name = node.name
    node_type = node.node_type
    db.delete(node)
    write_audit_log(
        db,
        "delete_asset_node",
        "asset_node",
        user=current_user,
        entity_id=node_id,
        request=request,
        details=f"{node_type}:{node_name}",
    )
    db.commit()
    return {"message": "Hierarchy node deleted"}
