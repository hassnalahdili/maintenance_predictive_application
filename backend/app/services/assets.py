from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.models import AssetNode, Machine
from app.schemas.common import AssetNodeOut, AssetTreeNode, MachineOut


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def get_asset_lineage(node: AssetNode | None) -> list[AssetNode]:
    lineage: list[AssetNode] = []
    current = node
    while current is not None:
        lineage.append(current)
        current = current.parent
    return list(reversed(lineage))


def ensure_asset_path(
    db: Session,
    *,
    site: str | None,
    zone: str | None = None,
    line: str | None = None,
    component: str | None = None,
) -> AssetNode | None:
    levels = [
        ("site", _clean(site)),
        ("zone", _clean(zone)),
        ("line", _clean(line)),
        ("component", _clean(component)),
    ]
    parent: AssetNode | None = None
    deepest: AssetNode | None = None
    for node_type, name in levels:
        if not name:
            continue
        query = db.query(AssetNode).filter(AssetNode.node_type == node_type, AssetNode.name == name)
        if parent is None:
            query = query.filter(AssetNode.parent_id.is_(None))
        else:
            query = query.filter(AssetNode.parent_id == parent.id)
        existing = query.first()
        if existing is None:
            existing = AssetNode(name=name, node_type=node_type, parent=parent)
            db.add(existing)
            db.flush()
        parent = existing
        deepest = existing
    return deepest


def build_asset_path(node: AssetNode | None) -> str | None:
    lineage = get_asset_lineage(node)
    if not lineage:
        return None
    return " > ".join(item.name for item in lineage)


def apply_asset_node_to_machine(machine: Machine, node: AssetNode | None) -> None:
    machine.asset_node = node
    lineage = get_asset_lineage(node)
    names = [item.name for item in lineage]
    machine.site = names[0] if len(names) > 0 else None
    machine.zone = names[1] if len(names) > 1 else None
    machine.line = names[2] if len(names) > 2 else None
    machine.component = names[-1] if len(names) > 0 else None


def resolve_machine_asset_node(
    db: Session,
    *,
    asset_node_id: int | None = None,
    site: str | None = None,
    zone: str | None = None,
    line: str | None = None,
    component: str | None = None,
) -> AssetNode | None:
    if asset_node_id:
        return db.query(AssetNode).filter(AssetNode.id == asset_node_id).first()
    return ensure_asset_path(db, site=site, zone=zone, line=line, component=component)


def serialize_asset_node(node: AssetNode) -> AssetNodeOut:
    return AssetNodeOut(
        id=node.id,
        name=node.name,
        node_type=node.node_type,
        parent_id=node.parent_id,
        path=build_asset_path(node),
        machine_count=len(node.machines),
        child_count=len(node.children),
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def can_move_asset_node(db: Session, node: AssetNode, parent_id: int | None) -> bool:
    if parent_id is None:
        return True
    if parent_id == node.id:
        return False
    parent = db.query(AssetNode).filter(AssetNode.id == parent_id).first()
    while parent is not None:
        if parent.id == node.id:
            return False
        parent = parent.parent
    return True


def serialize_machine(machine: Machine) -> MachineOut:
    return MachineOut(
        id=machine.id,
        name=machine.name,
        machine_type=machine.machine_type,
        asset_node_id=machine.asset_node_id,
        site=machine.site,
        zone=machine.zone,
        line=machine.line,
        component=machine.component,
        asset_path=build_asset_path(machine.asset_node),
        status=machine.status,
        notes=machine.notes,
        created_at=machine.created_at,
        updated_at=machine.updated_at,
    )


def build_asset_tree(db: Session) -> list[AssetTreeNode]:
    nodes = db.query(AssetNode).order_by(AssetNode.node_type.asc(), AssetNode.name.asc()).all()
    children_map: dict[int | None, list[AssetNode]] = defaultdict(list)
    for node in nodes:
        children_map[node.parent_id].append(node)

    def build(node: AssetNode) -> AssetTreeNode:
        return AssetTreeNode(
            id=node.id,
            name=node.name,
            node_type=node.node_type,
            children=[build(child) for child in children_map.get(node.id, [])],
        )

    return [build(node) for node in children_map.get(None, [])]
