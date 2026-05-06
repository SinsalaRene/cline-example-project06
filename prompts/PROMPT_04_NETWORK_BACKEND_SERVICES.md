# PROMPT 4: Network Backend Services

## Context

You are working on an Azure Firewall Management application built with Angular (frontend) and FastAPI/Python (backend). The next phase is implementing network topology management. This prompt covers the backend services and API layer for network resources.

**Relevant backend files to create/update:**
- `backend/app/models/network.py` — SQLAlchemy models for network entities
- `backend/app/schemas/network.py` — Pydantic schemas for network entities
- `backend/app/services/network_service.py` — Service layer for network operations
- `backend/app/api/network.py` — API router for network endpoints
- `backend/app/api/firewall_rule.py` — Update if needed for NSG rule integration

**Known state:**
- Backend has models for: firewall_rule, approval, audit
- Backend has services for: firewall_service, approval_service, audit_service, azure_sync_service
- Backend has API endpoints for: rules, approvals, audit, health, metrics
- Azure integration via AzureResourceGroupClient for NSG sync

## Task

Create the backend foundation for network topology management:

### 1. Database Models (`backend/app/models/network.py`)
Create SQLAlchemy models for:
- `Subnet`: id, name, address_prefix, vnet_id, created_at, updated_at
- `VirtualNetwork`: id, name, address_space, location, resource_group, tags, created_at, updated_at
- `NetworkSecurityGroup`: id, name, location, vnet_id, resource_group, tags, created_at, updated_at, sync_status (pending/applied/failed), last_synced_at
- `NSGRule`: id, nsg_id, name, priority, direction (inbound/outbound), protocol, source_address_prefix, destination_address_prefix, source_port_range, destination_port_range, access (allow/deny), source_ip_group, destination_ip_group, service_tag, priority_min=100, priority_max=4096
- `ExternalNetworkDevice`: id, name, ip_address, device_type (router/switch/firewall/other), vendor, model, contact_name, contact_email, notes, tags, created_at, updated_at
- `NetworkConnection`: id, source_id, source_type, destination_id, destination_type, connection_type, description, created_at — represents links in the topology graph

Add proper relationships between all models and indexes on frequently queried fields.

### 2. Pydantic Schemas (`backend/app/schemas/network.py`)
Create response/request schemas for:
- SubnetSchema, VirtualNetworkSchema, NSGSchema, NSGRuleSchema
- ExternalNetworkDeviceSchema (create/update/response variants)
- NetworkConnectionSchema
- TopologyGraphSchema — aggregated response with all nodes and edges
- NSGRuleCreateSchema, NSGRuleUpdateSchema
- ExternalDeviceCreateSchema, ExternalDeviceUpdateSchema
- ImpactAnalysisSchema — {affected_subnets, affected_external_devices, before_rules, after_rules}

### 3. Service Layer (`backend/app/services/network_service.py`)
Implement:
- `get_topology_graph()` — returns complete network topology with all nodes and connections
- `get_vnets(filter?)`, `get_vnet(id)`
- `get_subnets(vnet_id?)`, `get_subnet(id)`
- `get_nsgs(vnet_id?)`, `get_nsg(id)`
- `get_nsg_rules(nsg_id)`, `create_nsg_rule(nsg_id, data)`, `update_nsg_rule(rule_id, data)`, `delete_nsg_rule(rule_id)`, `reorder_nsg_rules(nsg_id, rule_ids)`
- `get_external_devices()`, `create_external_device(data)`, `update_external_device(id, data)`, `delete_external_device(id)`
- `get_connections(source_id?, source_type?, dest_id?, dest_type?)`
- `create_connection(data)`, `delete_connection(id)`
- `analyze_impact(nsg_id, updated_rules)` — compares old rules vs new rules, returns affected subnets and reachable external devices
- `sync_nsg_to_azure(nsg_id)` — delegates to AzureSyncService

### 4. API Router (`backend/app/api/network.py`)
Create endpoints:
- `GET /network/topology` — full topology graph
- `GET /network/virtual-networks`, `GET /network/virtual-networks/{id}`, `POST /network/virtual-networks`, `PUT /network/virtual-networks/{id}`, `DELETE /network/virtual-networks/{id}`
- `GET /network/subnets`, `GET /network/subnets/{id}`, `POST /network/subnets`, `DELETE /network/subnets/{id}`
- `GET /network/nsgs`, `GET /network/nsgs/{id}`, `POST /network/nsgs`, `PUT /network/nsgs/{id}`, `DELETE /network/nsgs/{id}`
- `GET /network/nsgs/{id}/rules`, `POST /network/nsgs/{id}/rules`, `PUT /network/nsgs/rules/{rule_id}`, `DELETE /network/nsgs/rules/{rule_id}`, `PUT /network/nsgs/{id}/rules/reorder`
- `GET /network/external-devices`, `POST /network/external-devices`, `PUT /network/external-devices/{id}`, `DELETE /network/external-devices/{id}`
- `GET /network/connections`, `POST /network/connections`, `DELETE /network/connections/{id}`
- `POST /network/nsgs/{id}/analyze-impact` — run impact analysis
- `POST /network/nsgs/{id}/sync` — sync NSG to Azure

Add proper auth dependency via `get_current_user`.

### 5. Register Router
Register the new network router in `backend/app/main.py`.

### 6. Database Migration
Create an Alembic migration: `alembic/versions/NNN_add_network_models.py`
- Include all new network tables
- Add foreign key constraints
- Add indexes

## Quality Checks

1. [ ] All network models defined with proper SQLAlchemy columns and relationships
2. [ ] All Pydantic schemas define request/response types correctly
3. [ ] NetworkService implements all methods listed above
4. [ ] All API endpoints registered with proper auth
5. [ ] Alembic migration creates all new tables
6. [ ] Backend still compiles/runs without errors
7. [ ] Impact analysis correctly identifies affected subnets and external devices

## Skills

Before starting, load and activate these skills in order:

```
use_skill(skill_name="improve-codebase-architecture")
```

Use this skill to analyze the existing codebase patterns (models, schemas, services, API layer) and ensure the new network module follows the same architecture. It will help identify the best structure for new files.

```
use_skill(skill_name="tdd")
```

After loading the architecture skill, activate TDD. Write backend tests first for models, schemas, service methods, and API endpoints before implementing any code. Test all CRUD operations, relationship queries, and edge cases.

## Documentation Requirements

- Add module-level docstring to each new file
- Add inline comments for complex business logic in network_service.py
- Update `backend/app/services/README.md` to include network service documentation
