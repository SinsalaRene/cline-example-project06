"""
Firewall service for Azure Firewall integration and management.

Refactored to use class-based dependency injection pattern for proper
FastAPI integration with dependency injection support.
"""

import json
import logging
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.firewall_rule import FirewallRule, Workload, FirewallRuleStatus

logger = logging.getLogger(__name__)


class FirewallService:
    """Service for firewall rule management with dependency injection.

    This service follows the DI pattern where dependencies (Session) are
    injected at the method level, enabling proper testing and lifecycle management.

    Usage in FastAPI:
        @app.get("/rules")
        def get_rules(db: Session = Depends(get_db)):
            service = FirewallService()
            return service.get_firewall_rules(db, user_id=current_user.id)
    """

    def __init__(self, logger_name: str = __name__):
        """Initialize the FirewallService."""
        self._logger = logging.getLogger(logger_name)
        self._logger.debug("FirewallService initialized")

    def get_firewall_rules(
        self,
        db: Session,
        user_id: UUID,
        workload_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Get firewall rules with filtering and pagination.

        Args:
            db: SQLAlchemy database session.
            user_id: UUID of the user requesting rules.
            workload_id: Optional UUID to filter by workload.
            status: Optional status string to filter rules.
            page: Page number for pagination (1-based).
            page_size: Number of items per page.

        Returns:
            Dictionary containing paginated rules list and metadata.

        Raises:
            ValueError: If page or page_size are invalid.
            Exception: Database connection or query errors.
        """
        self._logger.info("get_firewall_rules called for user %s", user_id)

        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")
        if page_size < 1:
            raise ValueError(f"page_size must be >= 1, got {page_size}")

        query = db.query(FirewallRule).filter(FirewallRule.created_by == user_id)

        if workload_id:
            query = query.filter(FirewallRule.workload_id == workload_id)
        if status:
            query = query.filter(FirewallRule.status == status)

        total = query.count()
        self._logger.info("Found %d firewall rules for user %s", total, user_id)

        query = query.order_by(desc(FirewallRule.created_at))

        skip = (page - 1) * page_size
        items = query.offset(skip).limit(page_size).all()

        self._logger.debug("Returning %d items for page %d", len(items), page)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def get_firewall_rule(self, db: Session, rule_id: UUID) -> FirewallRule:
        """Get a single firewall rule by ID.

        Args:
            db: SQLAlchemy database session.
            rule_id: UUID of the firewall rule to retrieve.

        Returns:
            FirewallRule object if found.

        Raises:
            ValueError: If the rule is not found.
        """
        self._logger.info("get_firewall_rule called for rule_id %s", rule_id)
        rule = db.query(FirewallRule).filter(FirewallRule.id == rule_id).first()
        if not rule:
            msg = f"Firewall rule {rule_id} not found"
            self._logger.warning(msg)
            raise ValueError(msg)
        self._logger.debug("Retrieved firewall rule %s", rule_id)
        return rule

    def create_firewall_rule(
        self,
        db: Session,
        rule_collection_name: str,
        priority: int,
        action: str,
        protocol: str,
        source_addresses: Optional[list[str]] = None,
        destination_fqdns: Optional[list[str]] = None,
        source_ip_groups: Optional[list[str]] = None,
        destination_ports: Optional[list[int]] = None,
        description: Optional[str] = None,
        workload_id: Optional[UUID] = None,
        azure_resource_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> FirewallRule:
        """Create a new firewall rule.

        Args:
            db: SQLAlchemy database session.
            rule_collection_name: Name of the rule collection.
            priority: Priority of the rule (lower = higher priority).
            action: Action to take (Allow/Deny).
            protocol: Protocol type (Tcp/Udp/Any).
            source_addresses: Optional list of source addresses.
            destination_fqdns: Optional list of destination FQDNs.
            source_ip_groups: Optional list of source IP groups.
            destination_ports: Optional list of destination ports.
            description: Optional description of the rule.
            workload_id: Optional UUID of associated workload.
            azure_resource_id: Optional Azure resource ID for synced rules.
            user_id: UUID of the creating user.

        Returns:
            The created FirewallRule object.

        Raises:
            ValueError: If validation fails.
            Exception: Database commit or connection errors.
        """
        self._logger.info("create_firewall_rule called: collection=%s, priority=%d, user=%s",
                          rule_collection_name, priority, user_id)

        if not rule_collection_name or not rule_collection_name.strip():
            raise ValueError("rule_collection_name is required")
        if not action or action not in ("Allow", "Deny"):
            raise ValueError("action must be 'Allow' or 'Deny'")
        if not protocol or protocol not in ("Tcp", "Udp", "Any"):
            raise ValueError("protocol must be 'Tcp', 'Udp', or 'Any'")
        if priority < 100 or priority > 4096:
            raise ValueError("priority must be between 100 and 4096")

        rule = FirewallRule(
            rule_collection_name=rule_collection_name,
            priority=priority,
            action=action,
            protocol=protocol,
            source_addresses=json.dumps(source_addresses) if source_addresses else None,
            destination_fqdns=json.dumps(destination_fqdns) if destination_fqdns else None,
            source_ip_groups=json.dumps(source_ip_groups) if source_ip_groups else None,
            destination_ports=json.dumps(destination_ports) if destination_ports else None,
            description=description,
            workload_id=workload_id,
            azure_resource_id=azure_resource_id,
            created_by=user_id,
        )

        try:
            db.add(rule)
            db.commit()
            db.refresh(rule)
        except Exception:
            db.rollback()
            self._logger.exception("Failed to create firewall rule %s", rule_collection_name)
            raise

        self._logger.info("Created firewall rule %s with id %s", rule_collection_name, rule.id)
        return rule

    def update_firewall_rule(
        self,
        db: Session,
        rule_id: UUID,
        user_id: UUID,
        **kwargs
    ) -> FirewallRule:
        """Update an existing firewall rule.

        Args:
            db: SQLAlchemy database session.
            rule_id: UUID of the rule to update.
            user_id: UUID of the user performing the update.
            **kwargs: Fields to update.

        Returns:
            Updated FirewallRule object.

        Raises:
            ValueError: If the rule is not found.
        """
        self._logger.info("update_firewall_rule called for rule_id %s by user %s", rule_id, user_id)
        rule = db.query(FirewallRule).filter(FirewallRule.id == rule_id).first()
        if not rule:
            msg = f"Firewall rule {rule_id} not found"
            self._logger.warning(msg)
            raise ValueError(msg)

        updatable_fields = {"rule_collection_name", "priority", "action", "protocol",
                          "source_addresses", "destination_fqdns", "source_ip_groups",
                          "destination_ports", "description", "workload_id", "status"}

        changed_fields = []
        for key, value in kwargs.items():
            if key in updatable_fields and hasattr(rule, key) and value is not None:
                old_value = getattr(rule, key)
                if old_value != value:
                    changed_fields.append(key)
                    setattr(rule, key, value)

        rule.updated_at = datetime.now(timezone.utc)

        try:
            db.commit()
            db.refresh(rule)
        except Exception:
            db.rollback()
            self._logger.exception("Failed to update firewall rule %s", rule_id)
            raise

        if changed_fields:
            self._logger.info("Updated fields for rule %s: %s", rule_id, changed_fields)
        return rule

    def delete_firewall_rule(self, db: Session, rule_id: UUID) -> bool:
        """Delete a firewall rule.

        Args:
            db: SQLAlchemy database session.
            rule_id: UUID of the rule to delete.

        Returns:
            True if deleted successfully.

        Raises:
            ValueError: If the rule is not found.
        """
        self._logger.info("delete_firewall_rule called for rule_id %s", rule_id)
        rule = db.query(FirewallRule).filter(FirewallRule.id == rule_id).first()
        if not rule:
            msg = f"Firewall rule {rule_id} not found"
            self._logger.warning(msg)
            raise ValueError(msg)

        try:
            db.delete(rule)
            db.commit()
        except Exception:
            db.rollback()
            self._logger.exception("Failed to delete firewall rule %s", rule_id)
            raise

        self._logger.info("Deleted firewall rule %s", rule_id)
        return True

    def import_firewall_rules_from_azure(self, db: Session, rules_data: list[dict]) -> list:
        """Import firewall rules from Azure.

        Args:
            db: SQLAlchemy database session.
            rules_data: List of dicts containing rule data from Azure.

        Returns:
            List of created FirewallRule objects.

        Raises:
            Exception: Database commit or connection errors.
        """
        self._logger.info("import_firewall_rules_from_azure called with %d rules", len(rules_data))
        imported = []
        errors = []

        for i, rule_data in enumerate(rules_data):
            try:
                if not rule_data.get("rule_collection_name") or not rule_data.get("priority"):
                    self._logger.warning("Skipping rule %d: missing required fields", i)
                    errors.append({"index": i, "error": "Missing required fields"})
                    continue

                source_addrs = rule_data.get("source_addresses")
                dest_fqdns = rule_data.get("destination_fqdns")
                source_ipgs = rule_data.get("source_ip_groups")
                dest_ports = rule_data.get("destination_ports")
                rule = FirewallRule(
                    rule_collection_name=rule_data.get("rule_collection_name"),
                    priority=rule_data.get("priority"),
                    action=rule_data.get("action"),
                    protocol=rule_data.get("protocol"),
                    source_addresses=json.dumps(source_addrs) if source_addrs else None,
                    destination_fqdns=json.dumps(dest_fqdns) if dest_fqdns else None,
                    source_ip_groups=json.dumps(source_ipgs) if source_ipgs else None,
                    destination_ports=json.dumps(dest_ports) if dest_ports else None,
                    description=rule_data.get("description"),
                    azure_resource_id=rule_data.get("azure_resource_id"),
                )
                db.add(rule)
                imported.append(rule)
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
                self._logger.error("Error importing rule %d: %s", i, e)

        if imported:
            try:
                db.commit()
                self._logger.info("Successfully imported %d rules from Azure", len(imported))
            except Exception:
                db.rollback()
                self._logger.exception("Failed to commit imported Azure rules")
                raise
        else:
            self._logger.warning("No rules imported from Azure due to errors: %s", errors)

        return imported


class WorkloadService:
    """Service for workload management with dependency injection."""

    def __init__(self, logger_name: str = __name__):
        """Initialize the WorkloadService."""
        self._logger = logging.getLogger(logger_name)
        self._logger.debug("WorkloadService initialized")

    def get_workloads(self, db: Session) -> list:
        """Get all workloads.

        Args:
            db: SQLAlchemy database session.

        Returns:
            List of Workload objects.
        """
        self._logger.info("get_workloads called")
        workloads = db.query(Workload).all()
        self._logger.info("Found %d workloads", len(workloads))
        return workloads

    def get_workload(self, db: Session, workload_id: UUID) -> Workload:
        """Get a single workload by ID.

        Args:
            db: SQLAlchemy database session.
            workload_id: UUID of the workload to retrieve.

        Returns:
            Workload object if found.

        Raises:
            ValueError: If the workload is not found.
        """
        self._logger.info("get_workload called for workload_id %s", workload_id)
        workload = db.query(Workload).filter(Workload.id == workload_id).first()
        if not workload:
            msg = f"Workload {workload_id} not found"
            self._logger.warning(msg)
            raise ValueError(msg)
        self._logger.debug("Retrieved workload %s", workload_id)
        return workload

    def create_workload(
        self,
        db: Session,
        name: str,
        description: Optional[str] = None,
        owner_id: Optional[UUID] = None,
        resource_groups: Optional[list[str]] = None,
        subscriptions: Optional[list[str]] = None,
    ) -> Workload:
        """Create a new workload.

        Args:
            db: SQLAlchemy database session.
            name: Name of the workload (required).
            description: Optional description.
            owner_id: Optional UUID of the owner.
            resource_groups: Optional list of Azure resource groups.
            subscriptions: Optional list of Azure subscription IDs.

        Returns:
            The created Workload object.

        Raises:
            ValueError: If name is empty.
            Exception: Database commit or connection errors.
        """
        self._logger.info("create_workload called: name=%s", name)

        if not name or not name.strip():
            raise ValueError("workload name is required")

        workload = Workload(
            name=name,
            description=description,
            owner_id=owner_id,
            resource_groups=resource_groups,
            subscriptions=subscriptions,
        )

        try:
            db.add(workload)
            db.commit()
            db.refresh(workload)
        except Exception:
            db.rollback()
            self._logger.exception("Failed to create workload %s", name)
            raise

        self._logger.info("Created workload %s with id %s", name, workload.id)
        return workload

    def update_workload(
        self,
        db: Session,
        workload_id: UUID,
        **kwargs
    ) -> Workload:
        """Update a workload.

        Args:
            db: SQLAlchemy database session.
            workload_id: UUID of the workload to update.
            **kwargs: Fields to update.

        Returns:
            Updated Workload object.

        Raises:
            ValueError: If the workload is not found.
        """
        self._logger.info("update_workload called for workload_id %s", workload_id)
        workload = db.query(Workload).filter(Workload.id == workload_id).first()
        if not workload:
            msg = f"Workload {workload_id} not found"
            self._logger.warning(msg)
            raise ValueError(msg)

        updatable_fields = {"name", "description", "owner_id", "resource_groups", "subscriptions"}

        changed_fields = []
        for key, value in kwargs.items():
            if key in updatable_fields and hasattr(workload, key) and value is not None:
                old_value = getattr(workload, key)
                if old_value != value:
                    changed_fields.append(key)
                    setattr(workload, key, value)

        try:
            db.commit()
            db.refresh(workload)
        except Exception:
            db.rollback()
            self._logger.exception("Failed to update workload %s", workload_id)
            raise

        if changed_fields:
            self._logger.info("Updated fields for workload %s: %s", workload_id, changed_fields)
        return workload

    def delete_workload(self, db: Session, workload_id: UUID) -> bool:
        """Delete a workload.

        Args:
            db: SQLAlchemy database session.
            workload_id: UUID of the workload to delete.

        Returns:
            True if deleted successfully.

        Raises:
            ValueError: If the workload is not found.
        """
        self._logger.info("delete_workload called for workload_id %s", workload_id)
        workload = db.query(Workload).filter(Workload.id == workload_id).first()
        if not workload:
            msg = f"Workload {workload_id} not found"
            self._logger.warning(msg)
            raise ValueError(msg)

        try:
            db.delete(workload)
            db.commit()
        except Exception:
            db.rollback()
            self._logger.exception("Failed to delete workload %s", workload_id)
            raise

        self._logger.info("Deleted workload %s", workload_id)
        return True