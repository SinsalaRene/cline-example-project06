"""
Network Topology Management Service.

This module implements the service layer for network topology management,
including Virtual Networks, Subnets, Network Security Groups, NSG Rules,
External Network Devices, and Network Connections.

Service methods operate on database sessions and return Pydantic schema
instances. Error handling follows the application convention of raising
HTTPException with proper error codes.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session, joinedload

from app.models.network import (
    Access,
    ConnectionType,
    Direction,
    ExternalNetworkDevice,
    NetworkConnection,
    NetworkSecurityGroup,
    NSGRule,
    Protocol as ModelProtocol,
    Subnet,
    SyncStatus,
    VirtualNetwork,
    ConnectionType as ModelConnectionType,
    DeviceType,
    subnet_device_connections,
)
from app.schemas.network import (
    Access as SchemaAccess,
    ConnectionType as SchemaConnectionType,
    Direction as SchemaDirection,
    ExternalDeviceCreate,
    ExternalDeviceSchema,
    ExternalDeviceUpdate,
    ImpactAnalysisSchema,
    NSGCreate,
    NSGRuleCreate,
    NSGRuleSchema,
    NSGRuleUpdate,
    NSGSchema,
    NSGSyncResponse,
    NetworkConnectionCreate,
    NetworkConnectionSchema,
    Protocol as SchemaProtocol,
    SubnetCreate,
    SubnetSchema,
    SubnetUpdate,
    SyncStatus as SchemaSyncStatus,
    TopologyGraphSchema,
    VirtualNetworkCreate,
    VirtualNetworkSchema,
    VirtualNetworkUpdate,
)

logger = logging.getLogger(__name__)


def _uuid_str(value: Any) -> Optional[str]:
    """Convert a value to string UUID or None."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    return str(value)


def _now_utc() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def _subnet_from_row(row: Subnet) -> SubnetSchema:
    """Convert a Subnet ORM row to a SubnetSchema response."""
    return SubnetSchema(
        id=row.id,
        name=row.name,
        address_prefix=row.address_prefix,
        vnet_id=row.vnet_id,
        nsg_id=row.nsg_id,
        description=row.description,
        tags=row.tags or {},
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _vnet_from_row(row: VirtualNetwork) -> VirtualNetworkSchema:
    """Convert a VirtualNetwork ORM row to a VirtualNetworkSchema response."""
    return VirtualNetworkSchema(
        id=row.id,
        name=row.name,
        address_space=row.address_space,
        location=row.location,
        resource_group=row.resource_group,
        subscription_id=row.subscription_id,
        tags=row.tags or {},
        is_synced=row.is_synced,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _nsg_from_row(row: NetworkSecurityGroup, include_rules: bool = False) -> NSGSchema:
    """Convert a NetworkSecurityGroup ORM row to an NSGSchema response."""
    rules = []
    if include_rules and hasattr(row, "rules"):
        for r in row.rules:
            rules.append(NsgRuleSchema.from_row(r))
    return NSGSchema(
        id=row.id,
        name=row.name,
        location=row.location,
        vnet_id=row.vnet_id,
        resource_group=row.resource_group,
        subscription_id=row.subscription_id,
        tags=row.tags or {},
        sync_status=row.sync_status.value if isinstance(row.sync_status, Enum) else str(row.sync_status),
        azure_nsg_id=row.azure_nsg_id,
        last_synced_at=row.last_synced_at,
        rules=rules,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _external_device_from_row(row: ExternalNetworkDevice) -> ExternalDeviceSchema:
    """Convert an ExternalNetworkDevice ORM row to an ExternalDeviceSchema response."""
    device_type = row.device_type
    if isinstance(device_type, Enum):
        device_type = device_type.value

    # Handle subnets eagerly loaded via joinedload
    subnets_list = []
    if hasattr(row, "_subnets_loaded"):
        subnets_list = row._subnets_loaded
    elif hasattr(row, "subnets") and isinstance(getattr(row, "subnets"), list):
        subnets_list = getattr(row, "subnets")

    return ExternalDeviceSchema(
        id=row.id,
        name=row.name,
        ip_address=row.ip_address,
        device_type=device_type,
        vendor=row.vendor,
        model=row.model,
        serial_number=row.serial_number,
        contact_name=row.contact_name,
        contact_email=row.contact_email,
        contact_phone=row.contact_phone,
        notes=row.notes,
        tags=row.tags or {},
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _connection_from_row(row: NetworkConnection) -> NetworkConnectionSchema:
    """Convert a NetworkConnection ORM row to a NetworkConnectionSchema response."""
    conn_type = row.connection_type
    if isinstance(conn_type, Enum):
        conn_type = conn_type.value
    return NetworkConnectionSchema(
        id=row.id,
        source_id=row.source_id,
        source_type=row.source_type,
        destination_id=row.destination_id,
        destination_type=row.destination_type,
        connection_type=conn_type,
        description=row.description,
        created_at=row.created_at,
    )


class NsgRuleSchema:
    """Helper to convert NSGRule ORM rows to NSGRuleSchema."""

    @staticmethod
    def from_row(row: NSGRule) -> NSGRuleSchema:
        """Convert NSGRule ORM instance to NSGRuleSchema."""
        direction = row.direction
        access = row.access
        protocol = row.protocol

        if isinstance(direction, Enum):
            direction = direction.value
        if isinstance(access, Enum):
            access = access.value
        if isinstance(protocol, Enum):
            protocol = protocol.value

        return NSGRuleSchema(
            id=row.id,
            nsg_id=row.nsg_id,
            name=row.name,
            priority=row.priority,
            direction=direction,
            protocol=protocol,
            source_address_prefix=row.source_address_prefix,
            destination_address_prefix=row.destination_address_prefix,
            source_port_range=row.source_port_range,
            destination_port_range=row.destination_port_range,
            access=access,
            source_ip_group=row.source_ip_group,
            destination_ip_group=row.destination_ip_group,
            service_tag=row.service_tag,
            is_enabled=row.is_enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class NetworkService:
    """Service layer for network topology management operations.

    All public methods accept a SQLAlchemy Session as the first argument
    and return Pydantic schema instances.

    Design notes:
        - Topology graph queries use eager loading to avoid N+1 queries
        - Impact analysis compares rule sets and resolves entity relationships
        - Azure sync delegates to AzureSyncService
    """

    # -------------------------------------------------------------------
    # Topology Graph
    # -------------------------------------------------------------------

    def get_topology_graph(self, db: Session) -> TopologyGraphSchema:
        """Return the complete network topology with all nodes and edges.

        Loads all VNets, Subnets, NSGs, NSG Rules, External Devices,
        and Connections in minimal queries.
        """
        vnets = db.query(VirtualNetwork).all()
        subnets = db.query(Subnet).all()
        nsgs = db.query(NetworkSecurityGroup).all()
        rules = db.query(NSGRule).all()
        devices = db.query(ExternalNetworkDevice).all()
        connections = db.query(NetworkConnection).all()

        return TopologyGraphSchema(
            virtual_networks=[_vnet_from_row(v) for v in vnets],
            subnets=[_subnet_from_row(s) for s in subnets],
            nsgs=[_nsg_from_row(n, include_rules=False) for n in nsgs],
            nsg_rules=[NsgRuleSchema.from_row(r) for r in rules],
            external_devices=[_external_device_from_row(d) for d in devices],
            connections=[_connection_from_row(c) for c in connections],
        )

    # -------------------------------------------------------------------
    # Virtual Networks
    # -------------------------------------------------------------------

    def get_vnets(self, db: Session, vnet_id: Optional[uuid.UUID] = None, resource_group: Optional[str] = None) -> List[VirtualNetworkSchema]:
        """List Virtual Networks with optional filtering."""
        query = db.query(VirtualNetwork)
        if vnet_id:
            query = query.filter(VirtualNetwork.id == vnet_id)
        if resource_group:
            query = query.filter(VirtualNetwork.resource_group.ilike(resource_group))
        return [_vnet_from_row(v) for v in query.all()]

    def get_vnet(self, db: Session, vnet_id: uuid.UUID) -> VirtualNetworkSchema:
        """Get a single Virtual Network by ID, raise 404 if not found."""
        vnet = db.query(VirtualNetwork).filter(VirtualNetwork.id == vnet_id).first()
        if not vnet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Virtual network not found: {vnet_id}",
            )
        return _vnet_from_row(vnet)

    def create_vnet(self, db: Session, data: VirtualNetworkCreate) -> VirtualNetworkSchema:
        """Create a new Virtual Network."""
        # Check for duplicate name
        existing = db.query(VirtualNetwork).filter(VirtualNetwork.name == data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Virtual network already exists: {data.name}",
            )
        now = _now_utc()
        vnet = VirtualNetwork(
            id=uuid.uuid4(),
            name=data.name,
            address_space=data.address_space,
            location=data.location,
            resource_group=data.resource_group,
            subscription_id=data.subscription_id,
            tags=data.tags,
            is_synced=False,
            created_at=now,
            updated_at=now,
        )
        db.add(vnet)
        db.commit()
        db.refresh(vnet)
        return _vnet_from_row(vnet)

    def update_vnet(self, db: Session, vnet_id: uuid.UUID, data: VirtualNetworkUpdate) -> VirtualNetworkSchema:
        """Update an existing Virtual Network."""
        vnet = db.query(VirtualNetwork).filter(VirtualNetwork.id == vnet_id).first()
        if not vnet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Virtual network not found: {vnet_id}",
            )
        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(vnet, key, value)
        vnet.updated_at = _now_utc()
        db.commit()
        db.refresh(vnet)
        return _vnet_from_row(vnet)

    def delete_vnet(self, db: Subnet, vnet_id: uuid.UUID) -> bool:
        """Delete a Virtual Network and all its children (via CASCADE)."""
        vnet = db.query(VirtualNetwork).filter(VirtualNetwork.id == vnet_id).first()
        if not vnet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Virtual network not found: {vnet_id}",
            )
        db.delete(vnet)
        db.commit()
        return True

    # -------------------------------------------------------------------
    # Subnets
    # -------------------------------------------------------------------

    def get_subnets(self, db: Session, vnet_id: Optional[uuid.UUID] = None, subnet_id: Optional[uuid.UUID] = None) -> List[SubnetSchema]:
        """List subnets with optional VNet filter or single subnet retrieval."""
        query = db.query(Subnet)
        if vnet_id:
            query = query.filter(Subnet.vnet_id == vnet_id)
        if subnet_id:
            query = query.filter(Subnet.id == subnet_id)
        return [_subnet_from_row(s) for s in query.all()]

    def get_subnet(self, db: Session, subnet_id: uuid.UUID) -> SubnetSchema:
        """Get a single Subnet by ID."""
        subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()
        if not subnet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subnet not found: {subnet_id}",
            )
        return _subnet_from_row(subnet)

    def create_subnet(self, db: Session, data: SubnetCreate) -> SubnetSchema:
        """Create a new Subnet."""
        # Verify parent VNet exists
        vnet = db.query(VirtualNetwork).filter(VirtualNetwork.id == data.vnet_id).first()
        if not vnet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent virtual network not found: {data.vnet_id}",
            )
        # Check for duplicate name
        existing = db.query(Subnet).filter(Subnet.name == data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subnet already exists: {data.name}",
            )
        now = _now_utc()
        subnet = Subnet(
            id=uuid.uuid4(),
            name=data.name,
            address_prefix=data.address_prefix,
            vnet_id=data.vnet_id,
            nsg_id=None,
            description=data.description,
            tags=data.tags,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(subnet)
        db.commit()
        db.refresh(subnet)
        return _subnet_from_row(subnet)

    def delete_subnet(self, db: Session, subnet_id: uuid.UUID) -> bool:
        """Delete a Subnet."""
        subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()
        if not subnet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subnet not found: {subnet_id}",
            )
        db.delete(subnet)
        db.commit()
        return True

    # -------------------------------------------------------------------
    # Network Security Groups
    # -------------------------------------------------------------------

    def get_nsgs(self, db: Session, vnet_id: Optional[uuid.UUID] = None, nsg_id: Optional[uuid.UUID] = None) -> List[NSGSchema]:
        """List NSGs with optional VNet filter or single NSG retrieval."""
        if nsg_id:
            nsg = db.query(NetworkSecurityGroup).filter(
                NetworkSecurityGroup.id == nsg_id
            ).options(joinedload(NetworkSecurityGroup.rules)).first()
            if not nsg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"NSG not found: {nsg_id}",
                )
            return [_nsg_from_row(nsg, include_rules=True)]

        query = db.query(NetworkSecurityGroup).options(joinedload(NetworkSecurityGroup.rules))
        if vnet_id:
            query = query.filter(NetworkSecurityGroup.vnet_id == vnet_id)
        result = []
        for nsg in query.all():
            result.append(_nsg_from_row(nsg, include_rules=True))
        return result

    def get_nsg(self, db: Session, nsg_id: uuid.UUID) -> NSGSchema:
        """Get a single NSG by ID with its rules."""
        nsg = db.query(NetworkSecurityGroup).filter(
            NetworkSecurityGroup.id == nsg_id
        ).options(joinedload(NetworkSecurityGroup.rules)).first()
        if not nsg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NSG not found: {nsg_id}",
            )
        return _nsg_from_row(nsg, include_rules=True)

    def create_nsg(self, db: Session, data: NSGCreate) -> NSGSchema:
        """Create a new Network Security Group."""
        # Verify parent VNet exists
        vnet = db.query(VirtualNetwork).filter(VirtualNetwork.id == data.vnet_id).first()
        if not vnet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent virtual network not found: {data.vnet_id}",
            )
        now = _now_utc()
        nsg = NetworkSecurityGroup(
            id=uuid.uuid4(),
            name=data.name,
            location=data.location,
            vnet_id=data.vnet_id,
            resource_group=data.resource_group,
            subscription_id=data.subscription_id,
            tags=data.tags,
            sync_status=SyncStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        db.add(nsg)
        db.commit()
        db.refresh(nsg)
        return _nsg_from_row(nsg, include_rules=True)

    def update_nsg(self, db: Session, nsg_id: uuid.UUID, data: NSGUpdate) -> NSGSchema:
        """Update an existing Network Security Group."""
        nsg = db.query(NetworkSecurityGroup).filter(
            NetworkSecurityGroup.id == nsg_id
        ).options(joinedload(NetworkSecurityGroup.rules)).first()
        if not nsg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NSG not found: {nsg_id}",
            )
        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            if key == "sync_status":
                # Convert string to enum
                try:
                    setattr(nsg, key, SyncStatus(value))
                except ValueError:
                    logger.warning(f"Invalid sync_status value: {value}")
            else:
                setattr(nsg, key, value)
        nsg.updated_at = _now_utc()
        db.commit()
        db.refresh(nsg)
        return _nsg_from_row(nsg, include_rules=True)

    def delete_nsg(self, db: Session, nsg_id: uuid.UUID) -> bool:
        """Delete a Network Security Group and all its rules (via CASCADE)."""
        nsg = db.query(NetworkSecurityGroup).filter(NetworkSecurityGroup.id == nsg_id).first()
        if not nsg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NSG not found: {nsg_id}",
            )
        db.delete(nsg)
        db.commit()
        return True

    # -------------------------------------------------------------------
    # NSG Rules
    # -------------------------------------------------------------------

    def get_nsg_rules(self, db: Session, nsg_id: uuid.UUID) -> List[NSGRuleSchema]:
        """Get all NSG rules for an NSG, ordered by priority."""
        nsg = db.query(NetworkSecurityGroup).filter(NetworkSecurityGroup.id == nsg_id).first()
        if not nsg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NSG not found: {nsg_id}",
            )
        rules = db.query(NSGRule).filter(
            NSGRule.nsg_id == nsg_id
        ).order_by(NSGRule.priority.asc()).all()
        return [NsgRuleSchema.from_row(r) for r in rules]

    def create_nsg_rule(self, db: Session, nsg_id: uuid.UUID, data: NSGRuleCreate) -> NSGRuleSchema:
        """Create a new NSG rule within an NSG."""
        # Verify NSG exists
        nsg = db.query(NetworkSecurityGroup).filter(NetworkSecurityGroup.id == nsg_id).first()
        if not nsg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NSG not found: {nsg_id}",
            )
        # Check for priority conflict
        existing = db.query(NSGRule).filter(
            NSGRule.nsg_id == nsg_id,
            NSGRule.priority == data.priority,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A rule with priority {data.priority} already exists",
            )
        now = _now_utc()
        rule = NSGRule(
            id=uuid.uuid4(),
            nsg_id=nsg_id,
            name=data.name,
            priority=data.priority,
            direction=data.direction.value if isinstance(data.direction, Enum) else data.direction,
            protocol=data.protocol.value if isinstance(data.protocol, Enum) else data.protocol,
            source_address_prefix=data.source_address_prefix,
            destination_address_prefix=data.destination_address_prefix,
            source_port_range=data.source_port_range,
            destination_port_range=data.destination_port_range,
            access=data.access.value if isinstance(data.access, Enum) else data.access,
            source_ip_group=data.source_ip_group,
            destination_ip_group=data.destination_ip_group,
            service_tag=data.service_tag,
            is_enabled=data.is_enabled,
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return NsgRuleSchema.from_row(rule)

    def update_nsg_rule(self, db: Session, rule_id: uuid.UUID, data: NSGRuleUpdate) -> NSGRuleSchema:
        """Update an existing NSG rule."""
        rule = db.query(NSGRule).filter(NSGRule.id == rule_id).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NSG rule not found: {rule_id}",
            )
        # Check for priority conflict if priority is changing
        update_fields = data.model_dump(exclude_unset=True)
        if "priority" in update_fields:
            existing = db.query(NSGRule).filter(
                NSGRule.nsg_id == rule.nsg_id,
                NSGRule.priority == data.priority,
                NSGRule.id != rule_id,
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A rule with priority {data.priority} already exists",
                )
        for key, value in update_fields.items():
            setattr(rule, key, value)
        rule.updated_at = _now_utc()
        db.commit()
        db.refresh(rule)
        return NsgRuleSchema.from_row(rule)

    def delete_nsg_rule(self, db: Session, rule_id: uuid.UUID) -> bool:
        """Delete an NSG rule."""
        rule = db.query(NSGRule).filter(NSGRule.id == rule_id).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NSG rule not found: {rule_id}",
            )
        db.delete(rule)
        db.commit()
        return True

    def reorder_nsg_rules(self, db: Session, nsg_id: uuid.UUID, rule_ids: List[uuid.UUID]) -> List[NSGRuleSchema]:
        """Reorder NSG rules by assigning sequential priorities.

        Args:
            nsg_id: The NSG to reorder rules for
            rule_ids: List of rule IDs in the desired order

        Returns:
            List of updated NSGRuleSchema instances

        Raises:
            HTTPException: If NSG not found or priority conflicts
        """
        nsg = db.query(NetworkSecurityGroup).filter(NetworkSecurityGroup.id == nsg_id).first()
        if not nsg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NSG not found: {nsg_id}",
            )

        # Fetch all rules for this NSG
        existing_rules = {r.id: r for r in db.query(NSGRule).filter(NSGRule.nsg_id == nsg_id).all()}
        existing_ids = set(existing_rules.keys())

        # Validate that all provided rule IDs exist
        for rule_id in rule_ids:
            if rule_id not in existing_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Rule not found: {rule_id}",
                )

        # Assign new priorities (100, 200, 300, ...)
        base_priority = 100
        for idx, rule_id in enumerate(rule_ids):
            rule = existing_rules[rule_id]
            rule.priority = base_priority + (idx * 100)
            rule.updated_at = _now_utc()

        db.commit()

        # Return updated rules
        updated_rules = db.query(NSGRule).filter(NSGRule.nsg_id == nsg_id).order_by(NSGRule.priority.asc()).all()
        return [NsgRuleSchema.from_row(r) for r in updated_rules]

    # -------------------------------------------------------------------
    # External Network Devices
    # -------------------------------------------------------------------

    def get_external_devices(
        self,
        db: Session,
        device_id: Optional[uuid.UUID] = None,
        device_type: Optional[str] = None,
        vendor: Optional[str] = None,
    ) -> List[ExternalDeviceSchema]:
        """List external network devices with optional filtering."""
        query = db.query(ExternalNetworkDevice)
        if device_id:
            query = query.filter(ExternalNetworkDevice.id == device_id)
        if device_type:
            query = query.filter(ExternalNetworkDevice.device_type == device_type)
        if vendor:
            query = query.filter(ExternalNetworkDevice.vendor.ilike(vendor))
        return [_external_device_from_row(d) for d in query.all()]

    def create_external_device(self, db: Session, data: ExternalDeviceCreate) -> ExternalDeviceSchema:
        """Create a new external network device."""
        existing = db.query(ExternalNetworkDevice).filter(ExternalNetworkDevice.name == data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"External device already exists: {data.name}",
            )
        now = _now_utc()
        device = ExternalNetworkDevice(
            id=uuid.uuid4(),
            name=data.name,
            ip_address=data.ip_address,
            device_type=data.device_type.value if isinstance(data.device_type, Enum) else data.device_type,
            vendor=data.vendor,
            model=data.model,
            serial_number=data.serial_number,
            contact_name=data.contact_name,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            notes=data.notes,
            tags=data.tags,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return _external_device_from_row(device)

    def update_external_device(self, db: Session, device_id: uuid.UUID, data: ExternalDeviceUpdate) -> ExternalDeviceSchema:
        """Update an existing external network device."""
        device = db.query(ExternalNetworkDevice).filter(ExternalNetworkDevice.id == device_id).first()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"External device not found: {device_id}",
            )
        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            if key == "device_type" and isinstance(value, str):
                try:
                    setattr(device, key, DeviceType(value))
                except ValueError:
                    logger.warning(f"Invalid device_type value: {value}")
            else:
                setattr(device, key, value)
        device.updated_at = _now_utc()
        db.commit()
        db.refresh(device)
        return _external_device_from_row(device)

    def delete_external_device(self, db: Session, device_id: uuid.UUID) -> bool:
        """Delete an external network device."""
        device = db.query(ExternalNetworkDevice).filter(ExternalNetworkDevice.id == device_id).first()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"External device not found: {device_id}",
            )
        db.delete(device)
        db.commit()
        return True

    # -------------------------------------------------------------------
    # Network Connections
    # -------------------------------------------------------------------

    def get_connections(
        self,
        db: Session,
        source_id: Optional[uuid.UUID] = None,
        source_type: Optional[str] = None,
        dest_id: Optional[uuid.UUID] = None,
        dest_type: Optional[str] = None,
    ) -> List[NetworkConnectionSchema]:
        """List network connections with optional filtering."""
        query = db.query(NetworkConnection)
        if source_id:
            query = query.filter(NetworkConnection.source_id == source_id)
        if source_type:
            query = query.filter(NetworkConnection.source_type == source_type)
        if dest_id:
            query = query.filter(NetworkConnection.destination_id == dest_id)
        if dest_type:
            query = query.filter(NetworkConnection.destination_type == dest_type)
        return [_connection_from_row(c) for c in query.all()]

    def create_connection(self, db: Session, data: NetworkConnectionCreate) -> NetworkConnectionSchema:
        """Create a new network connection."""
        now = _now_utc()
        conn = NetworkConnection(
            id=uuid.uuid4(),
            source_id=data.source_id,
            source_type=data.source_type,
            destination_id=data.destination_id,
            destination_type=data.destination_type,
            connection_type=data.connection_type.value if isinstance(data.connection_type, Enum) else data.connection_type,
            description=data.description,
            created_at=now,
        )
        db.add(conn)
        db.commit()
        db.refresh(conn)
        return _connection_from_row(conn)

    def delete_connection(self, db: Session, connection_id: uuid.UUID) -> bool:
        """Delete a network connection."""
        conn = db.query(NetworkConnection).filter(NetworkConnection.id == connection_id).first()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network connection not found: {connection_id}",
            )
        db.delete(conn)
        db.commit()
        return True

    # -------------------------------------------------------------------
    # Impact Analysis
    # -------------------------------------------------------------------

    def analyze_impact(self, db: Session, nsg_id: uuid.UUID, updated_rules: List[Dict[str, Any]]) -> ImpactAnalysisSchema:
        """Analyze the impact of NSG rule changes on subnets and external devices.

        Compares the current rules with the proposed updated rules and identifies:
        - Which subnets are affected by the change
        - Which external devices are reachable after the change
        - Which rules were added, removed, or modified

        Args:
            nsg_id: The NSG being analyzed
            updated_rules: List of rule dicts representing the proposed state

        Returns:
            ImpactAnalysisSchema with affected entities and rule diff
        """
        # Fetch current NSG and its rules
        nsg = db.query(NetworkSecurityGroup).filter(NetworkSecurityGroup.id == nsg_id).first()
        if not nsg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NSG not found: {nsg_id}",
            )

        # Get current rules
        current_rules = db.query(NSGRule).filter(NSGRule.nsg_id == nsg_id).order_by(NSGRule.priority.asc()).all()
        current_rules_data = [NsgRuleSchema.from_row(r).model_dump() for r in current_rules]

        # Create rule lookup by ID for comparison
        current_rule_ids = {r.id for r in current_rules}
        updated_rule_ids = {rule.get("id") for rule in updated_rules if rule.get("id")}
        new_rule_data = [rule for rule in updated_rules if not rule.get("id")]

        # Determine added, removed, and modified rules
        added_ids = updated_rule_ids - current_rule_ids
        removed_ids = current_rule_ids - updated_rule_ids
        common_ids = current_rule_ids & updated_rule_ids

        added_rules = [NsgRuleSchema.from_row(r) for r in current_rules if r.id in added_ids]
        removed_rules = [NsgRuleSchema.from_row(r) for r in current_rules if r.id in removed_ids]

        modified_rule_ids = set()
        for rid in common_ids:
            current_dict = next((r.model_dump() for r in current_rules if r.id == rid), None)
            updated_dict = next((ru for ru in updated_rules if ru.get("id") == rid), None)
            if current_dict and updated_dict and current_dict != updated_dict:
                modified_rule_ids.add(rid)

        changed_ids = set(added_ids) | set(removed_ids) | modified_rule_ids

        # Identify affected subnets - subnets associated with this NSG
        affected_subnets = db.query(Subnet).filter(
            Subnet.nsg_id == nsg_id,
            Subnet.is_active == True,  # noqa: E712
        ).all()

        # Identify reachable external devices - devices connected to affected subnets
        if affected_subnets:
            affected_subnet_ids = {s.id for s in affected_subnets}
            # Use the association table to find connected devices
            connected_devices = db.query(ExternalNetworkDevice).join(
                subnet_device_connections,
                ExternalNetworkDevice.id == subnet_device_connections.c.device_id,
            ).filter(
                subnet_device_connections.c.subnet_id.in_(affected_subnet_ids)
            ).all()
        else:
            connected_devices = []

        # Build the "after rules" list
        after_rules = []
        for rule in current_rules:
            updated_dict = next((ru for ru in updated_rules if ru.get("id") == str(rule.id)), None)
            if updated_dict:
                # Update the rule with new data
                for key, value in updated_dict.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                after_rules.append(NsgRuleSchema.from_row(rule))
            else:
                # Rule still exists
                after_rules.append(NsgRuleSchema.from_row(rule))

        # Add newly created rules
        for rule_data in new_rule_data:
            # Create a mock rule for schema purposes
            from app.models.network import NSGRule as NSGRuleModel
            mock_rule = NSGRuleModel(
                id=uuid.UUID(rule_data.get("id", uuid.uuid4())),
                nsg_id=nsg_id,
                name=rule_data.get("name", "unknown"),
                priority=rule_data.get("priority", 0),
                direction=rule_data.get("direction"),
                protocol=rule_data.get("protocol"),
                source_address_prefix=rule_data.get("source_address_prefix"),
                destination_address_prefix=rule_data.get("destination_address_prefix"),
                source_port_range=rule_data.get("source_port_range"),
                destination_port_range=rule_data.get("destination_port_range"),
                access=rule_data.get("access"),
                is_enabled=rule_data.get("is_enabled", True),
            )
            after_rules.append(NsgRuleSchema.from_row(mock_rule))

        return ImpactAnalysisSchema(
            nsg_id=nsg_id,
            nsg_name=nsg.name,
            before_rules=[NsgRuleSchema.from_row(r) for r in current_rules],
            after_rules=after_rules,
            affected_subnets=[_subnet_from_row(s) for s in affected_subnets],
            affected_external_devices=[_external_device_from_row(d) for d in connected_devices],
            changed_rule_ids=list(changed_ids),
            added_rules=added_rules,
            removed_rules=removed_rules,
        )

    # -------------------------------------------------------------------
    # Azure Sync
    # -------------------------------------------------------------------

    def sync_nsg_to_azure(self, db: Session, nsg_id: uuid.UUID) -> NSGSyncResponse:
        """Sync an NSG configuration to Azure via AzureSyncService.

        Delegates the actual Azure API call to AzureSyncService.

        Args:
            nsg_id: The NSG to sync

        Returns:
            NSGSyncResponse with sync result
        """
        from app.services.azure_sync_service import AzureSyncService

        nsg = db.query(NetworkSecurityGroup).filter(NetworkSecurityGroup.id == nsg_id).first()
        if not nsg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NSG not found: {nsg_id}",
            )

        sync_service = AzureSyncService()

        try:
            result = sync_service.sync_nsg(nsg)
            # Update local state
            if result.get("success"):
                nsg.sync_status = SyncStatus.APPLIED
                nsg.last_synced_at = _now_utc()
                db.commit()
                db.refresh(nsg)
                return NSGSyncResponse(
                    success=True,
                    message="NSG synced successfully to Azure",
                    sync_status=SyncStatus.APPLIED.value,
                    last_synced_at=nsg.last_synced_at,
                )
            else:
                nsg.sync_status = SyncStatus.FAILED
                nsg.last_synced_at = _now_utc()
                db.commit()
                db.refresh(nsg)
                return NSGSyncResponse(
                    success=False,
                    message=result.get("error", "Sync failed"),
                    sync_status=SyncStatus.FAILED.value,
                    last_synced_at=nsg.last_synced_at,
                )
        except Exception as e:
            logger.error(f"Failed to sync NSG {nsg_id} to Azure: {e}", exc_info=True)
            nsg.sync_status = SyncStatus.FAILED
            db.commit()
            return NSGSyncResponse(
                success=False,
                message=str(e),
                sync_status=SyncStatus.FAILED.value,
            )


# ============================================================================
# Module exports
# ============================================================================

__all__ = ["NetworkService"]