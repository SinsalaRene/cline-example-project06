"""
Azure Sync Service - Firewall rule synchronization, resource discovery, and firewall rule sync.

Provides:
- Synchronization of firewall rules between Azure and local database
- Azure resource discovery (firewall policies, rule collections, NAT rules)
- Firewall rule sync with conflict resolution and audit logging
- Firewall policy status monitoring
- Bidirectional sync support (Azure <-> local DB)
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.integrations.azure_client import (
    AzureClient,
    AzureClientError,
    AzureAuthenticationError,
    AzureResourceNotFoundError,
    AzureRuleValidationError,
    create_azure_client_from_settings,
)
from app.models.firewall_rule import FirewallRule, FirewallRuleStatus
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AzureResourceInfo:
    """Represents discovered Azure resource information."""

    resource_type: str  # 'firewall_policy', 'rule_collection', 'nat_collection', 'firewall'
    resource_name: str
    resource_id: Optional[str]
    resource_group: str
    subscription_id: str
    location: Optional[str]
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "resource_id": self.resource_id,
            "resource_group": self.resource_group,
            "subscription_id": self.subscription_id,
            "location": self.location,
            "tags": self.tags,
            "metadata": self.metadata,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
        }


@dataclass
class SyncResult:
    """Result of a synchronization operation."""

    success: bool
    rules_synced: int = 0
    rules_created: int = 0
    rules_updated: int = 0
    rules_deleted: int = 0
    rules_unchanged: int = 0
    errors: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    sync_start: Optional[datetime] = None
    sync_end: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        """Calculate sync duration in seconds."""
        if self.sync_start and self.sync_end:
            return (self.sync_end - self.sync_start).total_seconds()
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "rules_synced": self.rules_synced,
            "rules_created": self.rules_created,
            "rules_updated": self.rules_updated,
            "rules_deleted": self.rules_deleted,
            "rules_unchanged": self.rules_unchanged,
            "errors": self.errors,
            "conflicts": self.conflicts,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class FirewallRuleSync:
    """Represents a firewall rule sync operation details."""

    azure_rule_id: Optional[str]
    local_rule_id: Optional[str]
    rule_name: str
    collection_name: str
    priority: int
    action: str
    status: str
    conflict_type: Optional[str] = None
    resolution: Optional[str] = None


@dataclass
class FirewallPolicyStatus:
    """Status information for an Azure Firewall Policy."""

    policy_name: str
    resource_group: str
    subscription_id: str
    state: str  # 'active', 'inactive', 'syncing', 'error'
    total_rules: int = 0
    last_sync: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    error_message: Optional[str] = None
    rule_collections_count: int = 0
    nat_collections_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "policy_name": self.policy_name,
            "resource_group": self.resource_group,
            "subscription_id": self.subscription_id,
            "state": self.state,
            "total_rules": self.total_rules,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_sync_status": self.last_sync_status,
            "error_message": self.error_message,
            "rule_collections_count": self.rule_collections_count,
            "nat_collections_count": self.nat_collections_count,
        }


# =============================================================================
# Azure Sync Service
# =============================================================================

class AzureSyncError(Exception):
    """Base exception for Azure sync operations."""

    pass


class AzureSyncAuthenticationError(AzureSyncError):
    """Raised when Azure sync authentication fails."""

    pass


class AzureSyncResourceError(AzureSyncError):
    """Raised when Azure resource sync fails."""

    pass


class AzureSyncConflictError(AzureSyncError):
    """Raised when sync conflict occurs."""

    pass


class AzureSyncService:
    """Azure synchronization service for firewall rules and resources.

    Provides:
    - Synchronization of firewall rules between Azure and local database
    - Azure resource discovery
    - Firewall rule sync with conflict resolution
    - Firewall policy status monitoring

    Usage:
        sync_service = AzureSyncService(settings)
        result = await sync_service.sync_firewall_rules(policy_name="my-policy")
    """

    def __init__(self, settings: Optional[Any] = None):
        """Initialize the Azure sync service.

        Args:
            settings: Optional application settings for Azure configuration.
        """
        self._settings = settings
        self._azure_client: Optional[AzureClient] = None
        self._sync_interval_minutes: int = 30
        self._conflict_resolution: str = "azure_wins"  # or "local_wins", "manual"

        logger.info("AzureSyncService initialized")

    @property
    def azure_client(self) -> AzureClient:
        """Get the Azure client, creating it if necessary."""
        if self._azure_client is None:
            self._azure_client = create_azure_client_from_settings(self._settings)
            self._azure_client.authenticate()
        return self._azure_client

    @property
    def conflict_resolution(self) -> str:
        """Get the current conflict resolution strategy."""
        return self._conflict_resolution

    @conflict_resolution.setter
    def conflict_resolution(self, value: str):
        """Set the conflict resolution strategy."""
        if value not in ("azure_wins", "local_wins", "manual"):
            raise AzureSyncError(f"Invalid conflict resolution strategy: {value}")
        self._conflict_resolution = value
        logger.info("Conflict resolution strategy set to: %s", value)

    @property
    def sync_interval(self) -> int:
        """Get the sync interval in minutes."""
        return self._sync_interval_minutes

    @sync_interval.setter
    def sync_interval(self, value: int):
        """Set the sync interval in minutes."""
        if value <= 0:
            raise AzureSyncError("Sync interval must be positive")
        self._sync_interval_minutes = value
        logger.info("Sync interval set to: %d minutes", value)

    # ========================================================================
    # Resource Discovery
    # ========================================================================

    def discover_azure_resources(
        self,
        resource_group: Optional[str] = None,
        subscription_id: Optional[str] = None,
    ) -> List[AzureResourceInfo]:
        """Discover all Azure firewall-related resources.

        Args:
            resource_group: Optional resource group name to filter discovery.
            subscription_id: Optional subscription ID to use.

        Returns:
            List of AzureResourceInfo objects describing discovered resources.

        Raises:
            AzureSyncAuthenticationError: If authentication fails.
            AzureSyncResourceError: If resource discovery fails.
        """
        resources = []
        rg = resource_group or self._settings.azure_resource_group

        try:
            client = self.azure_client

            # Discover firewall policies
            policies = client.list_firewall_policies(rg)
            for policy in policies:
                resource_info = AzureResourceInfo(
                    resource_type="firewall_policy",
                    resource_name=policy.name or "unnamed-policy",
                    resource_id=getattr(policy, "id", None),
                    resource_group=rg,
                    subscription_id=subscription_id or self._settings.azure_subscription_id,
                    location=getattr(policy, "location", None),
                    tags=getattr(policy, "tags", {}) or {},
                    metadata={
                        "sku_tier": getattr(policy, "sku", {}),
                        "policy_id": getattr(policy, "policy_id", None),
                    },
                )
                resources.append(resource_info)

                # Discover rule collections within each policy
                rule_collections = self._discover_rule_collections(client, rg, policy.name or "")
                resources.extend(rule_collections)

            logger.info("Discovered %d Azure resources", len(resources))
            return resources

        except AzureAuthenticationError:
            raise AzureSyncAuthenticationError("Failed to authenticate with Azure")
        except (AzureAuthenticationError, AzureResourceNotFoundError) as e:
            raise AzureSyncResourceError(f"Resource discovery failed: {str(e)}")

    def _discover_rule_collections(
        self,
        client: AzureClient,
        resource_group: str,
        policy_name: str,
    ) -> List[AzureResourceInfo]:
        """Discover rule collections within a firewall policy."""
        resources = []

        try:
            rule_groups = client.get_rule_collection_groups(resource_group, policy_name)

            for group in rule_groups:
                group_name = getattr(group, "name", "unnamed-group")

                # Discover regular rule collections
                if hasattr(group, "rule_collections") and group.rule_collections:
                    for rc in group.rule_collections:
                        resource_info = AzureResourceInfo(
                            resource_type="rule_collection",
                            resource_name=getattr(rc, "name", "unnamed-collection"),
                            resource_id=getattr(rc, "id", None),
                            resource_group=resource_group,
                            subscription_id=self._settings.azure_subscription_id,
                            location=None,
                            tags={},
                            metadata={
                                "group_name": group_name,
                                "priority": getattr(rc, "priority", None),
                                "action": getattr(rc, "action", {}),
                                "rule_count": len(rc.rules) if hasattr(rc, "rules") else 0,
                            },
                        )
                        resources.append(resource_info)

                # Discover NAT collections
                if hasattr(group, "nat_collections") and group.nat_collections:
                    for nc in group.nat_collections:
                        resource_info = AzureResourceInfo(
                            resource_type="nat_collection",
                            resource_name=getattr(nc, "name", "unnamed-nat-collection"),
                            resource_id=getattr(nc, "id", None),
                            resource_group=resource_group,
                            subscription_id=self._settings.azure_subscription_id,
                            location=None,
                            tags={},
                            metadata={
                                "group_name": group_name,
                                "priority": getattr(nc, "priority", None),
                                "rule_count": len(nc.nat_rules) if hasattr(nc, "nat_rules") else 0,
                            },
                        )
                        resources.append(resource_info)

        except AzureResourceNotFoundError:
            logger.info("No rule collections found for policy '%s'", policy_name)
        except (AzureAuthenticationError, AzureResourceNotFoundError) as e:
            logger.error("Error discovering rule collections: %s", str(e))

        return resources

    def get_azure_firewall_status(
        self,
        resource_group: str,
        firewall_name: str,
    ) -> Dict[str, Any]:
        """Get the status of an Azure Firewall.

        Args:
            resource_group: Azure resource group name.
            firewall_name: Name of the Azure Firewall.

        Returns:
            Dictionary containing firewall status information.
        """
        try:
            client = self.azure_client
            return client.get_azure_firewall_status(resource_group, firewall_name)
        except (AzureAuthenticationError, AzureResourceNotFoundError) as e:
            logger.error("Error getting firewall status: %s", str(e))
            return {
                "name": firewall_name,
                "resource_group": resource_group,
                "state": "Error",
                "error": str(e),
            }

    # ========================================================================
    # Firewall Rule Synchronization
    # ========================================================================

    def sync_firewall_rules(
        self,
        db: Session,
        resource_group: Optional[str] = None,
        policy_name: Optional[str] = None,
        conflict_resolution: Optional[str] = None,
    ) -> SyncResult:
        """Synchronize firewall rules from Azure to local database.

        Performs a comprehensive sync:
        1. Fetches rules from Azure
        2. Validates rules
        3. Detects conflicts with local rules
        4. Resolves conflicts based on strategy
        5. Creates/updates/deletes rules in database

        Args:
            db: SQLAlchemy database session.
            resource_group: Optional Azure resource group name.
            policy_name: Optional Azure firewall policy name.
            conflict_resolution: Override conflict resolution strategy.

        Returns:
            SyncResult with sync details.

        Raises:
            AzureSyncAuthenticationError: If authentication fails.
            AzureSyncResourceError: If sync fails.
        """
        sync_start = datetime.now(timezone.utc)
        result = SyncResult(success=False, sync_start=sync_start)

        rg = resource_group or self._settings.azure_resource_group
        policy = policy_name or self._get_default_policy_name()
        resolution = conflict_resolution or self._conflict_resolution

        try:
            # Step 1: Fetch rules from Azure
            azure_rules = self._fetch_azure_rules(db, rg, policy)
            result.rules_synced = len(azure_rules)

            # Step 2: Get existing local rules
            local_rules = self._get_local_rules(db, rg, policy)

            # Step 3: Compare and detect changes
            changes = self._compare_rules(azure_rules, local_rules, resolution)

            # Step 4: Apply changes
            result.rules_created = self._create_local_rules(db, changes["to_create"])
            result.rules_updated = self._update_local_rules(db, changes["to_update"])
            result.rules_deleted = self._delete_local_rules(db, changes["to_delete"])
            result.rules_unchanged = self._count_unchanged(local_rules, changes)

            # Step 5: Resolve conflicts
            if changes["conflicts"]:
                result.conflicts = self._resolve_conflicts(db, changes["conflicts"], resolution)

            # Step 6: Validate synced rules
            validation_errors = self._validate_synced_rules(db)
            result.errors.extend(validation_errors)

            result.success = len(result.errors) == 0
            result.sync_end = datetime.now(timezone.utc)

            logger.info(
                "Sync completed: created=%d, updated=%d, deleted=%d, unchanged=%d, errors=%d",
                result.rules_created,
                result.rules_updated,
                result.rules_deleted,
                result.rules_unchanged,
                len(result.errors),
            )

            # Step 7: Log sync audit
            self._log_sync_audit(db, rg, policy, result)

            # Commit any pending changes
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                result.errors.append(f"Database commit error: {str(e)}")
                result.success = False

            return result

        except AzureAuthenticationError:
            result.errors.append("Azure authentication failed")
            result.sync_end = datetime.now(timezone.utc)
            raise
        except (AzureResourceNotFoundError, AzureRuleValidationError) as e:
            result.errors.append(f"Azure error: {str(e)}")
            result.sync_end = datetime.now(timezone.utc)
            raise AzureSyncResourceError(f"Sync failed: {str(e)}")
        except Exception as e:
            result.errors.append(f"Unexpected error: {str(e)}")
            result.sync_end = datetime.now(timezone.utc)
            raise AzureSyncResourceError(f"Sync failed unexpectedly: {str(e)}")

    def _fetch_azure_rules(
        self,
        db: Session,
        resource_group: str,
        policy_name: str,
    ) -> List[Dict[str, Any]]:
        """Fetch firewall rules from Azure."""
        client = self.azure_client
        try:
            azure_rules = client.get_firewall_rules_from_azure(resource_group, policy_name)
            logger.info("Fetched %d rules from Azure policy '%s'", len(azure_rules), policy_name)
            return azure_rules
        except (AzureAuthenticationError, AzureResourceNotFoundError) as e:
            logger.error("Failed to fetch rules from Azure: %s", str(e))
            return []

    def _get_local_rules(
        self,
        db: Session,
        resource_group: str,
        policy_name: str,
    ) -> Dict[str, FirewallRule]:
        """Get local rules indexed by rule key."""
        query = db.query(FirewallRule).filter(
            FirewallRule.status.in_([
                FirewallRuleStatus.Active.value,
                FirewallRuleStatus.Pending.value,
            ])
        )

        local_rules = {}
        for rule in query:
            rule_key = self._rule_key_from_model(rule)
            local_rules[rule_key] = rule

        logger.info("Found %d local rules", len(local_rules))
        return local_rules

    def _compare_rules(
        self,
        azure_rules: List[Dict[str, Any]],
        local_rules: Dict[str, FirewallRule],
        resolution: str,
    ) -> Dict[str, Any]:
        """Compare Azure rules with local rules and identify changes needed."""
        changes = {
            "to_create": [],
            "to_update": [],
            "to_delete": [],
            "conflicts": [],
        }

        # Build a lookup of local rules by Azure rule key
        azure_rules_by_key = {}
        for azure_rule in azure_rules:
            key = azure_rule.get("rule_name", "")
            azure_rules_by_key[key] = azure_rule

        # Check for new, updated, and conflicting Azure rules
        for azure_rule in azure_rules:
            key = azure_rule.get("rule_name", "")
            local_rule = local_rules.get(key)

            if local_rule is None:
                # New rule from Azure
                changes["to_create"].append(azure_rule)
            else:
                # Rule exists locally - check for differences
                if self._rules_differ(azure_rule, local_rule):
                    if resolution == "azure_wins":
                        changes["to_update"].append({
                            "local_rule": local_rule,
                            "azure_rule": azure_rule,
                            "resolution": "azure_wins",
                        })
                    elif resolution == "local_wins":
                        changes["to_delete"].append(local_rule)
                        changes["to_create"].append(azure_rule)
                    else:  # manual
                        changes["conflicts"].append({
                            "local_rule": local_rule,
                            "azure_rule": azure_rule,
                            "resolution_needed": resolution,
                        })

        # Check for rules that no longer exist in Azure
        for key, local_rule in local_rules.items():
            if key not in azure_rules_by_key:
                changes["to_delete"].append(local_rule)

        return changes

    def _rules_differ(self, azure_rule: Dict[str, Any], local_rule: FirewallRule) -> bool:
        """Check if Azure rule differs from local rule."""
        return (
            str(azure_rule.get("priority", "")) != str(getattr(local_rule, "priority", ""))
            or azure_rule.get("action", "") != str(getattr(local_rule, "action", ""))
            or azure_rule.get("protocol", "") != str(getattr(local_rule, "protocol", ""))
        )

    def _create_local_rules(
        self,
        db: Session,
        rules_to_create: List[Dict[str, Any]],
    ) -> int:
        """Create new rules in the local database."""
        created_count = 0

        for azure_rule in rules_to_create:
            try:
                rule = FirewallRule(
                    rule_collection_name=azure_rule.get("rule_collection_name", ""),
                    priority=azure_rule.get("priority", 100),
                    action=azure_rule.get("action", "Allow"),
                    protocol=azure_rule.get("protocol", "Tcp"),
                    source_addresses=azure_rule.get("source_addresses", None),
                    destination_fqdns=azure_rule.get("destination_fqdns", None),
                    destination_ports=azure_rule.get("destination_ports", None),
                    status=FirewallRuleStatus.Pending.value,
                    azure_resource_id=azure_rule.get("id"),
                )
                db.add(rule)
                db.flush()
                created_count += 1

            except Exception as e:
                logger.error("Failed to create rule: %s", str(e))
                db.rollback()

        return created_count

    def _update_local_rules(
        self,
        db: Session,
        rules_to_update: List[Dict[str, Any]],
    ) -> int:
        """Update existing rules in the local database."""
        updated_count = 0

        for update_info in rules_to_update:
            local_rule = update_info["local_rule"]
            azure_rule = update_info["azure_rule"]

            try:
                local_rule.priority = azure_rule.get("priority", local_rule.priority)
                local_rule.action = azure_rule.get("action", local_rule.action)
                local_rule.protocol = azure_rule.get("protocol", local_rule.protocol)
                local_rule.status = FirewallRuleStatus.Pending.value

                db.flush()
                updated_count += 1

            except Exception as e:
                logger.error("Failed to update rule: %s", str(e))
                db.rollback()

        return updated_count

    def _delete_local_rules(
        self,
        db: Session,
        rules_to_delete: List[FirewallRule],
    ) -> int:
        """Delete rules from the local database."""
        deleted_count = 0

        for rule in rules_to_delete:
            try:
                db.delete(rule)
                db.flush()
                deleted_count += 1

            except Exception as e:
                logger.error("Failed to delete rule: %s", str(e))
                db.rollback()

        return deleted_count

    def _count_unchanged(
        self,
        local_rules: Dict[str, FirewallRule],
        changes: Dict[str, Any],
    ) -> int:
        """Count rules that remain unchanged."""
        changed_keys = set()
        for rule_data in changes["to_create"]:
            changed_keys.add(rule_data.get("rule_collection_name", ""))
        for change in changes["to_update"]:
            changed_keys.add(change["local_rule"].rule_collection_name)
        for rule in changes["to_delete"]:
            if hasattr(rule, "rule_collection_name"):
                changed_keys.add(rule.rule_collection_name)

        unchanged = set(local_rules.keys()) - changed_keys
        return len(unchanged)

    def _resolve_conflicts(
        self,
        db: Session,
        conflicts: List[Dict[str, Any]],
        resolution: str,
    ) -> List[Dict[str, Any]]:
        """Resolve sync conflicts."""
        resolved_conflicts = []

        for conflict in conflicts:
            local_rule = conflict["local_rule"]
            azure_rule = conflict["azure_rule"]

            if resolution == "azure_wins":
                local_rule.priority = azure_rule.get("priority", local_rule.priority)
                local_rule.action = azure_rule.get("action", local_rule.action)
                local_rule.status = FirewallRuleStatus.Pending.value
                resolution_action = "azure_wins"
            elif resolution == "local_wins":
                resolution_action = "local_wins"
            else:
                resolution_action = "pending_review"

            resolved_conflicts.append({
                "rule_collection_name": getattr(local_rule, "rule_collection_name", ""),
                "resolution": resolution_action,
                "local_value": str(local_rule),
                "azure_value": str(azure_rule),
            })

        return resolved_conflicts

    def _validate_synced_rules(self, db: Session) -> List[str]:
        """Validate rules after synchronization."""
        errors = []
        client = self.azure_client

        try:
            rules = db.query(FirewallRule).filter(
                FirewallRule.status.in_([
                    FirewallRuleStatus.Pending.value,
                    FirewallRuleStatus.Active.value,
                ])
            ).all()

            for rule in rules:
                rule_data = {
                    "rule_collection_name": rule.rule_collection_name,
                    "priority": rule.priority,
                    "action": rule.action,
                    "protocol": rule.protocol,
                }
                is_valid, validation_errors = client.validate_firewall_rule(rule_data)

                if not is_valid:
                    errors.append(f"Rule '{rule.rule_collection_name}': {', '.join(validation_errors)}")

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return errors

    def _log_sync_audit(
        self,
        db: Session,
        resource_group: str,
        policy_name: str,
        result: SyncResult,
    ):
        """Log the sync operation to audit trail."""
        try:
            from app.models.audit import AuditLog, AuditAction as AuditActionEnum

            audit_entry = AuditLog(
                action=AuditActionEnum.Import.value,
                resource_type="firewall_rule",
                resource_id=policy_name,
                new_value=str({
                    "resource_group": resource_group,
                    "policy_name": policy_name,
                    "rules_synced": result.rules_synced,
                    "rules_created": result.rules_created,
                    "rules_updated": result.rules_updated,
                    "rules_deleted": result.rules_deleted,
                    "errors": result.errors,
                    "duration_seconds": result.duration_seconds,
                }),
                ip_address="azure-sync-service",
            )
            db.add(audit_entry)
            logger.info("Audit log created for sync of policy '%s'", policy_name)

        except Exception as e:
            logger.error("Failed to create audit log: %s", str(e))

    def _get_default_policy_name(self) -> str:
        """Get the default policy name from settings."""
        return getattr(self._settings, "azure_default_policy", None) or "default-policy"

    def _rule_key_from_model(self, rule: FirewallRule) -> str:
        """Generate a rule key from a FirewallRule model instance."""
        return f"{rule.rule_collection_name}"

    # ========================================================================
    # Policy Status
    # ========================================================================

    def get_policy_status(
        self,
        resource_group: str,
        policy_name: str,
    ) -> FirewallPolicyStatus:
        """Get the status of a firewall policy.

        Args:
            resource_group: Azure resource group name.
            policy_name: Firewall policy name.

        Returns:
            FirewallPolicyStatus with current status.
        """
        try:
            client = self.azure_client

            # Get policy details from Azure
            policy = client.get_firewall_policy(resource_group, policy_name)
            if not policy:
                return FirewallPolicyStatus(
                    policy_name=policy_name,
                    resource_group=resource_group,
                    subscription_id=self._settings.azure_subscription_id,
                    state="not_found",
                )

            # Get rule collection groups
            rule_groups = client.get_rule_collection_groups(resource_group, policy_name)

            total_rules = 0
            rule_collection_count = 0
            nat_collection_count = 0

            if rule_groups:
                for group in rule_groups:
                    if hasattr(group, "rule_collections") and group.rule_collections:
                        rule_collection_count += len(group.rule_collections)
                        for rc in group.rule_collections:
                            if hasattr(rc, "rules"):
                                total_rules += len(rc.rules) or 0
                    if hasattr(group, "nat_collections") and group.nat_collections:
                        nat_collection_count += len(group.nat_collections)
                        for nc in group.nat_collections:
                            if hasattr(nc, "nat_rules"):
                                total_rules += len(nc.nat_rules) or 0

            return FirewallPolicyStatus(
                policy_name=policy_name,
                resource_group=resource_group,
                subscription_id=self._settings.azure_subscription_id,
                state="active",
                total_rules=total_rules,
                last_sync=datetime.now(timezone.utc),
                rule_collections_count=rule_collection_count,
                nat_collections_count=nat_collection_count,
            )

        except AzureResourceNotFoundError:
            return FirewallPolicyStatus(
                policy_name=policy_name,
                resource_group=resource_group,
                subscription_id=self._settings.azure_subscription_id,
                state="not_found",
            )
        except (AzureAuthenticationError, AzureRuleValidationError) as e:
            return FirewallPolicyStatus(
                policy_name=policy_name,
                resource_group=resource_group,
                subscription_id=self._settings.azure_subscription_id,
                state="error",
                error_message=str(e),
            )

    def sync_policy_status(
        self,
        db: Session,
        resource_group: str,
        policy_name: str,
    ) -> Dict[str, Any]:
        """Sync and update policy status in the database.

        Args:
            db: SQLAlchemy database session.
            resource_group: Azure resource group name.
            policy_name: Firewall policy name.

        Returns:
            Dictionary with sync status results.
        """
        status = self.get_policy_status(resource_group, policy_name)

        try:
            from app.models.audit import AuditLog, AuditAction

            status_data = status.to_dict()
            audit_entry = AuditLog(
                action=AuditAction.Import.value,
                resource_type="firewall_policy",
                resource_id=policy_name,
                new_value=str(status_data),
                ip_address="azure-sync-service",
            )
            db.add(audit_entry)
            db.flush()

            logger.info("Policy status synced for '%s': %s", policy_name, status.state)
            return {"success": True, "status": status.state, "details": status_data}

        except Exception as e:
            logger.error("Failed to sync policy status: %s", str(e))
            return {"success": False, "error": str(e)}

    # ========================================================================
    # Firewall Rule Collection Sync
    # ========================================================================

    def sync_rule_collections(
        self,
        db: Session,
        resource_group: str,
        policy_name: str,
    ) -> SyncResult:
        """Synchronize rule collections from Azure to local database.

        Args:
            db: SQLAlchemy database session.
            resource_group: Azure resource group name.
            policy_name: Firewall policy name.

        Returns:
            SyncResult with sync details.
        """
        sync_start = datetime.now(timezone.utc)
        result = SyncResult(success=False, sync_start=sync_start)

        try:
            client = self.azure_client
            azure_rule_groups = client.get_rule_collection_groups(resource_group, policy_name)

            if not azure_rule_groups:
                result.success = True
                result.sync_end = datetime.now(timezone.utc)
                return result

            # Process each rule collection group
            for group in azure_rule_groups:
                group_name = getattr(group, "name", "unnamed-group")

                # Process rule collections
                if hasattr(group, "rule_collections") and group.rule_collections:
                    for rc in group.rule_collections:
                        rc_data = {
                            "name": getattr(rc, "name", ""),
                            "priority": getattr(rc, "priority", None),
                            "action": getattr(rc, "action", "Allow"),
                            "group_name": group_name,
                        }

                        # Sync each rule in the collection
                        if hasattr(rc, "rules") and rc.rules:
                            for azure_rule in rc.rules:
                                rule_data = client._create_azure_rule_dict(
                                    client._extract_rule_data(azure_rule, rc_data)
                                )

                                # Validate before inserting
                                is_valid, errors = client.validate_firewall_rule(rule_data)
                                if is_valid:
                                    self._upsert_rule(db, rule_data)
                                    result.rules_synced += 1
                                else:
                                    result.errors.extend(errors)

                # Process NAT collections
                if hasattr(group, "nat_collections") and group.nat_collections:
                    for nc in group.nat_collections:
                        nc_data = {
                            "name": getattr(nc, "name", ""),
                            "priority": getattr(nc, "priority", None),
                            "action": "DNAT",
                            "group_name": group_name,
                        }

                        if hasattr(nc, "nat_rules") and nc.nat_rules:
                            for azure_rule in nc.nat_rules:
                                rule_data = client._create_azure_rule_dict(
                                    client._extract_nat_rule_data(azure_rule, nc_data)
                                )

                                is_valid, errors = client.validate_firewall_rule(rule_data)
                                if is_valid:
                                    self._upsert_rule(db, rule_data)
                                    result.rules_synced += 1
                                else:
                                    result.errors.extend(errors)

            result.success = len(result.errors) == 0
            result.sync_end = datetime.now(timezone.utc)

            return result

        except (AzureAuthenticationError, AzureResourceNotFoundError, AzureRuleValidationError) as e:
            result.errors.append(f"Azure error: {str(e)}")
            result.sync_end = datetime.now(timezone.utc)
            raise AzureSyncResourceError(f"Rule collection sync failed: {str(e)}")

    def _upsert_rule(
        self,
        db: Session,
        rule_data: Dict[str, Any],
    ):
        """Upsert a rule into the database. Creates if not exists, updates if exists."""
        from app.models.firewall_rule import FirewallRule

        existing = db.query(FirewallRule).filter(
            FirewallRule.rule_collection_name == rule_data.get("name", ""),
        ).first()

        if existing:
            existing.priority = rule_data.get("priority", existing.priority)
            existing.action = rule_data.get("action", existing.action)
        else:
            new_rule = FirewallRule(
                rule_collection_name=rule_data.get("name", ""),
                priority=rule_data.get("priority", 100),
                action=rule_data.get("action", "Allow"),
                protocol=rule_data.get("protocol", "Tcp"),
                status=FirewallRuleStatus.Pending.value,
            )
            db.add(new_rule)

        db.flush()

    # ========================================================================
    # NAT Rule Sync
    # ========================================================================

    def sync_nat_rules(
        self,
        db: Session,
        resource_group: str,
        policy_name: str,
    ) -> SyncResult:
        """Synchronize NAT rules from Azure to local database.

        Args:
            db: SQLAlchemy database session.
            resource_group: Azure resource group name.
            policy_name: Firewall policy name.

        Returns:
            SyncResult with sync details.
        """
        sync_start = datetime.now(timezone.utc)
        result = SyncResult(success=False, sync_start=sync_start)

        try:
            client = self.azure_client
            azure_rule_groups = client.get_rule_collection_groups(resource_group, policy_name)

            if not azure_rule_groups:
                result.success = True
                result.sync_end = datetime.now(timezone.utc)
                return result

            nat_rules_synced = 0

            for group in azure_rule_groups:
                group_name = getattr(group, "name", "unnamed-group")

                if hasattr(group, "nat_collections") and group.nat_collections:
                    for nc in group.nat_collections:
                        nc_data = {
                            "collection_name": getattr(nc, "name", ""),
                            "collection_priority": getattr(nc, "priority", None),
                            "group_name": group_name,
                        }

                        if hasattr(nc, "nat_rules") and nc.nat_rules:
                            for azure_nat_rule in nc.nat_rules:
                                nat_rule_data = client._create_azure_rule_dict(
                                    client._extract_nat_rule_data(azure_nat_rule, nc_data)
                                )

                                is_valid, errors = client.validate_firewall_rule(nat_rule_data)
                                if is_valid:
                                    self._upsert_rule(db, nat_rule_data)
                                    nat_rules_synced += 1
                                else:
                                    result.errors.extend(errors)

            result.rules_synced = nat_rules_synced
            result.success = len(result.errors) == 0
            result.sync_end = datetime.now(timezone.utc)

            logger.info("Synced %d NAT rules", nat_rules_synced)
            return result

        except (AzureAuthenticationError, AzureResourceNotFoundError, AzureRuleValidationError) as e:
            result.errors.append(f"Azure error: {str(e)}")
            result.sync_end = datetime.now(timezone.utc)
            raise AzureSyncResourceError(f"NAT rule sync failed: {str(e)}")

    # ========================================================================
    # Firewall Rule Application Sync (push changes to Azure)
    # ========================================================================

    def apply_local_rules_to_azure(
        self,
        db: Session,
        resource_group: str,
        policy_name: str,
        rule_ids: Optional[List[str]] = None,
    ) -> SyncResult:
        """Apply local firewall rules to Azure.

        Pushes changes from local database to Azure.

        Args:
            db: SQLAlchemy database session.
            resource_group: Azure resource group name.
            policy_name: Firewall policy name.
            rule_ids: Optional list of rule IDs to sync.

        Returns:
            SyncResult with sync details.
        """
        sync_start = datetime.now(timezone.utc)
        result = SyncResult(success=False, sync_start=sync_start)

        try:
            client = self.azure_client

            # Get local rules to sync
            if rule_ids:
                local_rules = db.query(FirewallRule).filter(
                    FirewallRule.id.in_(rule_ids)
                ).all()
            else:
                local_rules = db.query(FirewallRule).filter(
                    FirewallRule.status.in_([
                        FirewallRuleStatus.Pending.value,
                        FirewallRuleStatus.Active.value,
                    ])
                ).all()

            # Convert to Azure-compatible format
            azure_rules = []
            for rule in local_rules:
                azure_rule_data = {
                    "name": rule.rule_collection_name or f"rule-{rule.id}",
                    "priority": rule.priority or 100,
                    "action": rule.action or "Allow",
                    "protocol": rule.protocol or "Tcp",
                    "source_addresses": getattr(rule, "source_addresses", []) or [],
                    "destination_fqdns": getattr(rule, "destination_fqdns", []) or [],
                    "destination_ports": getattr(rule, "destination_ports", []) or [],
                }
                azure_rules.append(azure_rule_data)

                # Validate
                is_valid, errors = client.validate_firewall_rule(azure_rule_data)
                if not is_valid:
                    result.errors.extend(errors)
                    continue

            if not azure_rules:
                result.success = True
                result.sync_end = datetime.now(timezone.utc)
                return result

            # Bulk create in Azure
            collection_name = getattr(local_rules[0], "rule_collection_name", "") if local_rules else ""
            azure_result = client.bulk_create_firewall_rules(
                resource_group, policy_name, azure_rules, collection_name
            )

            result.rules_synced = azure_result.get("success_count", 0)
            result.rules_created = azure_result.get("success_count", 0)
            result.errors = [e.get("error", "") for e in azure_result.get("errors", [])]
            result.success = len(result.errors) == 0
            result.sync_end = datetime.now(timezone.utc)

            logger.info("Applied %d rules to Azure", result.rules_synced)
            return result

        except (AzureAuthenticationError, AzureResourceNotFoundError, AzureRuleValidationError) as e:
            result.errors.append(f"Azure error: {str(e)}")
            result.sync_end = datetime.now(timezone.utc)
            raise AzureSyncResourceError(f"Apply to Azure failed: {str(e)}")


# Module-level convenience function
def create_azure_sync_service(settings: Optional[Any] = None) -> AzureSyncService:
    """Factory function to create an AzureSyncService instance.

    Args:
        settings: Optional application settings.

    Returns:
        Configured AzureSyncService instance.
    """
    return AzureSyncService(settings=settings)