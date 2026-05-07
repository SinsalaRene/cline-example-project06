"""
Network Topology Management API Endpoints.

This module defines FastAPI API routers for network topology management,
including Virtual Networks, Subnets, Network Security Groups, NSG Rules,
External Network Devices, and Network Connections.

All endpoints require authentication via the get_current_user dependency.
"""

from __future__ import annotations

import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.auth.auth_service import get_current_user
from app.database import get_db
from app.models.network import (
    DeviceType,
    ExternalNetworkDevice,
    NetworkConnection,
    NetworkSecurityGroup,
    Subnet,
    VirtualNetwork,
)
from app.schemas.network import (
    ImpactAnalysisSchema,
    NSGCreate,
    NSGRuleCreate,
    NSGRuleSchema,
    NSGRuleUpdate,
    NSGSchema,
    NSGSyncRequest,
    NSGSyncResponse,
    NetworkConnectionCreate,
    NetworkConnectionSchema,
    TopologyGraphSchema,
    ExternalDeviceCreate,
    ExternalDeviceSchema,
    ExternalDeviceUpdate,
    SubnetCreate,
    SubnetSchema,
    SubnetUpdate,
    VirtualNetworkCreate,
    VirtualNetworkSchema,
    VirtualNetworkUpdate,
)
from app.services.network_service import NetworkService

router = APIRouter(prefix="/network", tags=["Network"])


def _get_service(db: Session = Depends(get_db)) -> NetworkService:
    """Dependency to create a NetworkService instance."""
    return NetworkService()


def _require_current_user(user=Depends(get_current_user)) -> Any:
    """Require an authenticated user (wrapper for get_current_user)."""
    return user


# ============================================================================
# Topology Graph
# ============================================================================

@router.get(
    "/topology",
    response_model=TopologyGraphSchema,
    summary="Get full network topology graph",
    responses={401: {"description": "Unauthorized"}},
)
async def get_topology(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get the complete network topology including all nodes and edges."""
    service = NetworkService()
    return service.get_topology_graph(db)


# ============================================================================
# Virtual Networks
# ============================================================================

@router.get(
    "/virtual-networks",
    response_model=list[VirtualNetworkSchema],
    summary="List all virtual networks",
    responses={401: {"description": "Unauthorized"}},
)
async def list_virtual_networks(
    vnet_id: Optional[uuid.UUID] = Query(None, description="Filter by VNet ID"),
    resource_group: Optional[str] = Query(None, description="Filter by resource group"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List virtual networks with optional filtering."""
    service = NetworkService()
    return service.get_vnets(db, vnet_id=vnet_id, resource_group=resource_group)


@router.get(
    "/virtual-networks/{vnet_id}",
    response_model=VirtualNetworkSchema,
    summary="Get a virtual network by ID",
    responses={404: {"description": "Virtual network not found"}},
)
async def get_virtual_network(
    vnet_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get a single virtual network by ID."""
    service = NetworkService()
    return service.get_vnet(db, vnet_id)


@router.post(
    "/virtual-networks",
    response_model=VirtualNetworkSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new virtual network",
    responses={409: {"description": "Virtual network name conflict"}},
)
async def create_virtual_network(
    data: VirtualNetworkCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Create a new virtual network."""
    service = NetworkService()
    return service.create_vnet(db, data)


@router.put(
    "/virtual-networks/{vnet_id}",
    response_model=VirtualNetworkSchema,
    summary="Update a virtual network",
    responses={404: {"description": "Virtual network not found"}},
)
async def update_virtual_network(
    vnet_id: uuid.UUID,
    data: VirtualNetworkUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Update an existing virtual network."""
    service = NetworkService()
    return service.update_vnet(db, vnet_id, data)


@router.delete(
    "/virtual-networks/{vnet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a virtual network and all its children",
    responses={404: {"description": "Virtual network not found"}},
)
async def delete_virtual_network(
    vnet_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Delete a virtual network and all its children (CASCADE)."""
    service = NetworkService()
    service.delete_vnet(db, vnet_id)


# ============================================================================
# Subnets
# ============================================================================

@router.get(
    "/subnets",
    response_model=list[SubnetSchema],
    summary="List subnets",
    responses={401: {"description": "Unauthorized"}},
)
async def list_subnets(
    vnet_id: Optional[uuid.UUID] = Query(None, description="Filter by parent VNet ID"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List subnets with optional VNet filter."""
    service = NetworkService()
    return service.get_subnets(db, vnet_id=vnet_id)


@router.get(
    "/subnets/{subnet_id}",
    response_model=SubnetSchema,
    summary="Get a subnet by ID",
    responses={404: {"description": "Subnet not found"}},
)
async def get_subnet(
    subnet_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get a single subnet by ID."""
    service = NetworkService()
    return service.get_subnet(db, subnet_id)


@router.post(
    "/subnets",
    response_model=SubnetSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new subnet",
    responses={
        404: {"description": "Parent VNet not found"},
        409: {"description": "Subnet name conflict"},
    },
)
async def create_subnet(
    data: SubnetCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Create a new subnet within a virtual network."""
    service = NetworkService()
    return service.create_subnet(db, data)


@router.delete(
    "/subnets/{subnet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a subnet",
    responses={404: {"description": "Subnet not found"}},
)
async def delete_subnet(
    subnet_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Delete a subnet."""
    service = NetworkService()
    service.delete_subnet(db, subnet_id)


# ============================================================================
# Network Security Groups
# ============================================================================

@router.get(
    "/nsgs",
    response_model=list[NSGSchema],
    summary="List NSGs",
    responses={401: {"description": "Unauthorized"}},
)
async def list_nsgs(
    vnet_id: Optional[uuid.UUID] = Query(None, description="Filter by parent VNet ID"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List network security groups with optional VNet filter."""
    service = NetworkService()
    return service.get_nsgs(db, vnet_id=vnet_id)


@router.get(
    "/nsgs/{nsg_id}",
    response_model=NSGSchema,
    summary="Get an NSG by ID",
    responses={404: {"description": "NSG not found"}},
)
async def get_nsg(
    nsg_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get a single NSG with its rules."""
    service = NetworkService()
    return service.get_nsg(db, nsg_id)


@router.post(
    "/nsgs",
    response_model=NSGSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new NSG",
    responses={
        404: {"description": "Parent VNet not found"},
    },
)
async def create_nsg(
    data: NSGCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Create a new network security group."""
    service = NetworkService()
    return service.create_nsg(db, data)


@router.put(
    "/nsgs/{nsg_id}",
    response_model=NSGSchema,
    summary="Update an NSG",
    responses={404: {"description": "NSG not found"}},
)
async def update_nsg(
    nsg_id: uuid.UUID,
    data: NSGCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Update an existing NSG."""
    service = NetworkService()
    return service.update_nsg(db, nsg_id, data)


@router.delete(
    "/nsgs/{nsg_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an NSG and all its rules",
    responses={404: {"description": "NSG not found"}},
)
async def delete_nsg(
    nsg_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Delete an NSG and all its rules (CASCADE)."""
    service = NetworkService()
    service.delete_nsg(db, nsg_id)


# ============================================================================
# NSG Rules
# ============================================================================

@router.get(
    "/nsgs/{nsg_id}/rules",
    response_model=list[NSGRuleSchema],
    summary="Get all rules for an NSG",
    responses={
        404: {"description": "NSG not found"},
        401: {"description": "Unauthorized"},
    },
)
async def get_nsg_rules(
    nsg_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get all rules for an NSG, ordered by priority."""
    service = NetworkService()
    return service.get_nsg_rules(db, nsg_id)


@router.post(
    "/nsgs/{nsg_id}/rules",
    response_model=NSGRuleSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new NSG rule",
    responses={
        404: {"description": "NSG not found"},
        409: {"description": "Priority conflict"},
    },
)
async def create_nsg_rule(
    nsg_id: uuid.UUID,
    data: NSGRuleCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Create a new NSG rule within an NSG."""
    service = NetworkService()
    return service.create_nsg_rule(db, nsg_id, data)


@router.put(
    "/nsgs/rules/{rule_id}",
    response_model=NSGRuleSchema,
    summary="Update an NSG rule",
    responses={
        404: {"description": "NSG rule not found"},
        409: {"description": "Priority conflict"},
    },
)
async def update_nsg_rule(
    rule_id: uuid.UUID,
    data: NSGRuleUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Update an existing NSG rule."""
    service = NetworkService()
    return service.update_nsg_rule(db, rule_id, data)


@router.delete(
    "/nsgs/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an NSG rule",
    responses={404: {"description": "NSG rule not found"}},
)
async def delete_nsg_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Delete an NSG rule."""
    service = NetworkService()
    service.delete_nsg_rule(db, rule_id)


@router.put(
    "/nsgs/{nsg_id}/rules/reorder",
    response_model=list[NSGRuleSchema],
    summary="Reorder NSG rules by priority",
    responses={
        404: {"description": "NSG or rule not found"},
    },
)
async def reorder_nsg_rules(
    nsg_id: uuid.UUID,
    rule_ids: list[uuid.UUID] = Query(..., description="List of rule IDs in desired order"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Reorder NSG rules by assigning sequential priorities."""
    service = NetworkService()
    return service.reorder_nsg_rules(db, nsg_id, rule_ids)


# ============================================================================
# External Network Devices
# ============================================================================

@router.get(
    "/external-devices",
    response_model=list[ExternalDeviceSchema],
    summary="List external network devices",
    responses={401: {"description": "Unauthorized"}},
)
async def list_external_devices(
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List external network devices with optional filtering."""
    service = NetworkService()
    return service.get_external_devices(db, device_type=device_type, vendor=vendor)


@router.post(
    "/external-devices",
    response_model=ExternalDeviceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new external network device",
    responses={409: {"description": "Device name conflict"}},
)
async def create_external_device(
    data: ExternalDeviceCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Create a new external network device."""
    service = NetworkService()
    return service.create_external_device(db, data)


@router.put(
    "/external-devices/{device_id}",
    response_model=ExternalDeviceSchema,
    summary="Update an external network device",
    responses={404: {"description": "External device not found"}},
)
async def update_external_device(
    device_id: uuid.UUID,
    data: ExternalDeviceUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Update an existing external network device."""
    service = NetworkService()
    return service.update_external_device(db, device_id, data)


@router.delete(
    "/external-devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an external network device",
    responses={404: {"description": "External device not found"}},
)
async def delete_external_device(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Delete an external network device."""
    service = NetworkService()
    service.delete_external_device(db, device_id)


# ============================================================================
# Network Connections
# ============================================================================

@router.get(
    "/connections",
    response_model=list[NetworkConnectionSchema],
    summary="List network connections",
    responses={401: {"description": "Unauthorized"}},
)
async def list_connections(
    source_id: Optional[uuid.UUID] = Query(None, description="Filter by source entity ID"),
    source_type: Optional[str] = Query(None, description="Filter by source entity type"),
    dest_id: Optional[uuid.UUID] = Query(None, description="Filter by destination entity ID"),
    dest_type: Optional[str] = Query(None, description="Filter by destination entity type"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List network connections with optional filtering."""
    service = NetworkService()
    return service.get_connections(
        db,
        source_id=source_id,
        source_type=source_type,
        dest_id=dest_id,
        dest_type=dest_type,
    )


@router.post(
    "/connections",
    response_model=NetworkConnectionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new network connection",
)
async def create_connection(
    data: NetworkConnectionCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Create a new network connection."""
    service = NetworkService()
    return service.create_connection(db, data)


@router.delete(
    "/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a network connection",
    responses={404: {"description": "Network connection not found"}},
)
async def delete_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Delete a network connection."""
    service = NetworkService()
    service.delete_connection(db, connection_id)


# ============================================================================
# Impact Analysis
# ============================================================================

@router.post(
    "/nsgs/{nsg_id}/analyze-impact",
    response_model=ImpactAnalysisSchema,
    summary="Run impact analysis on NSG rule changes",
    responses={
        404: {"description": "NSG not found"},
    },
)
async def analyze_impact(
    nsg_id: uuid.UUID,
    updated_rules: list[dict[str, Any]] = [],
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Analyze the impact of NSG rule changes on subnets and external devices."""
    service = NetworkService()
    return service.analyze_impact(db, nsg_id, updated_rules)


# ============================================================================
# NSG Sync to Azure
# ============================================================================

@router.post(
    "/nsgs/{nsg_id}/sync",
    response_model=NSGSyncResponse,
    summary="Sync an NSG to Azure",
    responses={
        404: {"description": "NSG not found"},
    },
)
async def sync_nsg(
    nsg_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Sync an NSG configuration to Azure via AzureSyncService."""
    service = NetworkService()
    return service.sync_nsg_to_azure(db, nsg_id)


# ============================================================================
# Module exports
# ============================================================================

# Alias for external imports
network_router = router

__all__ = ["router", "network_router"]
