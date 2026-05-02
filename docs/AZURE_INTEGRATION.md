# Azure Integration Guide

## Overview

This guide documents the Azure Integration Layer for the firewall management system. The Azure integration enables synchronization of firewall rules between Azure Firewall policies and the local database, resource discovery, firewall rule validation, and bidirectional sync support.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                           │
├─────────────────────────────────────────────────────────────────┤
│                   AzureSyncService                              │
│  - sync_firewall_rules() - Full sync cycle                     │
│  - discover_azure_resources() - Resource discovery             │
│  - get_policy_status() - Policy status monitoring              │
│  - sync_rule_collections() - Collection sync                   │
│  - sync_nat_rules() - NAT rule sync                            │
│  - apply_local_rules_to_azure() - Push local to Azure          │
├─────────────────────────────────────────────────────────────────┤
│                   AzureClient                                   │
│  - Authentication via Service Principal                          │
│  - Rule validation (IP, FQDN, priority, ports)                 │
│  - Duplicate detection                                           │
│  - Bulk operations                                               │
├─────────────────────────────────────────────────────────────────┤
│              Azure SDK (azure-mgmt-network)                     │
├─────────────────────────────────────────────────────────────────┤
│                   Azure Firewall Policy                         │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. AzureClient (`backend/app/integrations/azure_client.py`)

The Azure SDK client service that handles authentication and API communication with Azure.

#### Key Features
- Service Principal authentication
- Rule validation (IP addresses, FQDNs, priorities, ports)
- Duplicate detection for firewall rules
- Bulk operations for multiple rules
- Rate limiting support

#### Authentication

```python
from app.integrations.azure_client import (
    AzureClient,
    create_azure_client_from_settings,
)

# Using settings object
from app.config import Settings
settings = Settings()
client = create_azure_client_from_settings(settings)

# Manual creation
client = AzureClient(
    tenant_id=settings.azure_tenant_id,
    client_id=settings.azure_client_id,
    client_secret=settings.azure_client_secret,
    subscription_id=settings.azure_subscription_id,
    location=settings.azure_region,
)

# Authenticate
client.authenticate()
```

#### Authentication Flow

1. The client uses Azure's Service Principal authentication (client credentials flow)
2. Tokens are obtained via `DefaultAzureCredential` or manual service principal credentials
3. Token refresh is handled automatically

#### Custom Exception Classes

The Azure client defines specialized exception classes for error handling:

```python
from app.integrations.azure_client import (
    AzureClientError,           # Base exception
    AzureAuthenticationError,   # Auth failures
    AzureResourceNotFoundError, # Resource not found
    AzureRuleValidationError,   # Rule validation failed
    AzureRateLimitExceededError, # Rate limit hit
)
```

#### Rule Validation

```python
# Validate a firewall rule before creating/updating
is_valid, errors = client.validate_firewall_rule({
    "rule_collection_name": "my-collection",
    "priority": 100,
    "action": "Allow",
    "protocol": "Tcp",
    "source_addresses": ["10.0.0.0/24"],
    "destination_fqdns": ["example.com"],
    "destination_ports": [443],
})

# Validation checks:
# - Collection name: 3-80 characters, alphanumeric + hyphens
# - Priority: 100-4096 (must be unique within collection)
# - Action: "Allow" or "Deny"
# - Protocol: "Tcp", "Udp", "Icmp", "Any"
# - Source addresses: Valid IP/CIDR notation
# - Destination FQDNs: Valid FQDN format
# - Destination ports: 1-65535
```

#### Duplicate Detection

```python
# Check for duplicate rules
duplicates = client.check_duplicate_rules(
    new_rules=[{"rule_collection_name": "col", "priority": 100}],
    existing_rules=[{"rule_collection_name": "col", "priority": 100}],
)
# Returns list of conflicts
```

#### Bulk Operations

```python
# Bulk create firewall rules
result = client.bulk_create_firewall_rules(
    resource_group="my-rg",
    policy_name="my-policy",
    rules=rules_data,  # List of validated rule dicts
    collection_name="my-collection",
)

# Get firewall rules from Azure
azure_rules = client.get_firewall_rules_from_azure(
    resource_group="my-rg",
    policy_name="my-policy",
)
```

### 2. AzureSyncService (`backend/app/services/azure_sync_service.py`)

The sync service orchestrates synchronization between Azure and the local database.

#### Key Methods

##### `sync_firewall_rules()`

Performs a full synchronization cycle:

```python
from app.services.azure_sync_service import AzureSyncService

sync_service = AzureSyncService(settings)
result = sync_service.sync_firewall_rules(
    db=session,
    resource_group="my-resource-group",
    policy_name="my-policy",
    conflict_resolution="azure_wins",  # or "local_wins", "manual"
)

# Result contains:
# - success: bool
# - rules_synced: int
# - rules_created: int
# - rules_updated: int
# - rules_deleted: int
# - rules_unchanged: int
# - errors: List[str]
# - conflicts: List[dict]
# - duration_seconds: float
```

**Sync Cycle Steps:**
1. Fetch rules from Azure Firewall Policy
2. Get existing local rules from database
3. Compare Azure rules with local rules
4. Identify changes (create/update/delete)
5. Apply changes to local database
6. Validate synced rules
7. Log sync audit trail

##### `discover_azure_resources()`

Discovers all Azure firewall-related resources:

```python
resources = sync_service.discover_azure_resources(
    resource_group="my-resource-group",
    subscription_id="my-subscription-id",  # Optional
)

# Returns List[AzureResourceInfo]:
# - resource_type: 'firewall_policy', 'rule_collection', 'nat_collection'
# - resource_name, resource_id, resource_group
# - subscription_id, location, tags, metadata
```

##### `get_policy_status()`

Gets the status of a firewall policy:

```python
status = sync_service.get_policy_status(
    resource_group="my-resource-group",
    policy_name="my-policy",
)

# Returns FirewallPolicyStatus:
# - policy_name, resource_group, subscription_id
# - state: 'active', 'inactive', 'syncing', 'error', 'not_found'
# - total_rules, rule_collections_count, nat_collections_count
# - last_sync, last_sync_status, error_message
```

##### `sync_rule_collections()`

Synchronizes rule collections specifically:

```python
result = sync_service.sync_rule_collections(
    db=session,
    resource_group="my-resource-group",
    policy_name="my-policy",
)
```

##### `sync_nat_rules()`

Synchronizes NAT rules specifically:

```python
result = sync_service.sync_nat_rules(
    db=session,
    resource_group="my-resource-group",
    policy_name="my-policy",
)
```

##### `apply_local_rules_to_azure()`

Pushes local rules to Azure (reverse sync):

```python
result = sync_service.apply_local_rules_to_azure(
    db=session,
    resource_group="my-resource-group",
    policy_name="my-policy",
    rule_ids=["rule-1-id", "rule-2-id"],  # Optional - all if not specified
)
```

## Configuration

### Environment Variables

Set the following environment variables in `.env`:

```bash
# Azure Authentication
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id

# Azure Configuration
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_REGION=eastus
AZURE_DEFAULT_POLICY=default-policy

# Sync Configuration
AZURE_SYNC_INTERVAL_MINUTES=30
AZURE_CONFLICT_RESOLUTION=azure_wins  # or "local_wins", "manual"
```

### Settings Class

The `Settings` class in `backend/app/config.py` provides typed access to these values:

```python
from app.config import Settings

settings = Settings()
print(settings.azure_tenant_id)
print(settings.azure_subscription_id)
```

## Data Models

### AzureResourceInfo

```python
@dataclass
class AzureResourceInfo:
    resource_type: str  # 'firewall_policy', 'rule_collection', 'nat_collection'
    resource_name: str
    resource_id: Optional[str]
    resource_group: str
    subscription_id: str
    location: Optional[str]
    tags: Dict[str, str]
    metadata: Dict[str, Any]
    discovered_at: datetime
```

### SyncResult

```python
@dataclass
class SyncResult:
    success: bool
    rules_synced: int
    rules_created: int
    rules_updated: int
    rules_deleted: int
    rules_unchanged: int
    errors: List[str]
    conflicts: List[Dict[str, Any]]
    sync_start: Optional[datetime]
    sync_end: Optional[datetime]
```

### FirewallPolicyStatus

```python
@dataclass
class FirewallPolicyStatus:
    policy_name: str
    resource_group: str
    subscription_id: str
    state: str  # 'active', 'inactive', 'syncing', 'error'
    total_rules: int
    last_sync: Optional[datetime]
    last_sync_status: Optional[str]
    error_message: Optional[str]
    rule_collections_count: int
    nat_collections_count: int
```

## Conflict Resolution

The sync service supports three conflict resolution strategies:

| Strategy | Description |
|----------|-------------|
| `azure_wins` | Azure rules overwrite local rules |
| `local_wins` | Local rules are preserved, Azure rules are noted |
| `manual` | Conflicts are flagged for manual review |

Set via the `conflict_resolution` setter or parameter:

```python
service.conflict_resolution = "azure_wins"
```

## Usage Examples

### Basic Sync

```python
from app.services.azure_sync_service import AzureSyncService
from app.config import Settings

settings = Settings()
service = AzureSyncService(settings)

# Sync firewall rules
result = service.sync_firewall_rules(
    db=session,
    resource_group="prod-rg",
    policy_name="prod-firewall-policy",
)

if result.success:
    print(f"Synced {result.rules_synced} rules")
else:
    print(f"Errors: {result.errors}")
```

### Resource Discovery

```python
# Discover all firewall resources in a resource group
resources = service.discover_azure_resources(
    resource_group="prod-rg",
)

for resource in resources:
    print(f"{resource.resource_type}: {resource.resource_name}")
```

### Policy Monitoring

```python
# Check policy status
status = service.get_policy_status(
    resource_group="prod-rg",
    policy_name="prod-firewall-policy",
)

print(f"Policy: {status.policy_name}")
print(f"State: {status.state}")
print(f"Total rules: {status.total_rules}")
```

### Bidirectional Sync

```python
# Push local rules to Azure
result = service.apply_local_rules_to_azure(
    db=session,
    resource_group="prod-rg",
    policy_name="prod-firewall-policy",
)
```

## Testing

Run the Azure sync tests:

```bash
# Run all Azure sync tests
pytest backend/tests/test_azure_sync.py -v

# Run specific test class
pytest backend/tests/test_azure_sync.py::TestAzureSyncServiceInitialization -v

# Run with coverage
pytest backend/tests/test_azure_sync.py --cov=app.services.azure_sync_service --cov-report=term-missing
```

## Error Handling

All Azure sync operations raise specific exceptions:

| Exception | When Raised |
|-----------|-------------|
| `AzureSyncError` | Base sync error |
| `AzureSyncAuthenticationError` | Authentication failed |
| `AzureSyncResourceError` | Resource operation failed |
| `AzureSyncConflictError` | Conflict during sync |

```python
from app.services.azure_sync_service import AzureSyncError, AzureSyncAuthenticationError

try:
    service.sync_firewall_rules(db=session, ...)
except AzureSyncAuthenticationError:
    logger.error("Azure authentication failed")
except AzureSyncResourceError as e:
    logger.error(f"Sync resource error: {e}")
```

## Integration Points

### Database Models

The sync service interacts with:
- `FirewallRule` - Firewall rule records
- `AuditLog` - Sync audit trail

### Firewall Service Integration

The `FirewallService` uses `AzureClient` for validation:

```python
from app.services.firewall_service import FirewallService
from app.integrations.azure_client import AzureClient

# Validation
is_valid, errors = client.validate_firewall_rule(rule_data)
```

## Deployment

### Required Azure RBAC Permissions

The Service Principal needs:
- `Microsoft.Network/firewallPolicies/read` - Read access
- `Microsoft.Network/firewallPolicies/*` - Manage policies
- `Microsoft.Network/azureFirewalls/read` - Read firewall status

### Network Requirements

- Outbound HTTPS (443) to Azure Resource Manager
- Outbound access to Azure endpoints for firewall management