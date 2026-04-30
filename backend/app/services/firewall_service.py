"""
Firewall service for Azure Firewall integration and management.
"""

from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.firewall_rule import FirewallRule, Workload, FirewallRuleStatus


class FirewallService:
    """Service for firewall rule management."""
    
    @staticmethod
    def get_firewall_rules(
        db: Session,
        user_id: UUID,
        workload_id: UUID = None,
        status: str = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Get firewall rules with filtering and pagination."""
        query = db.query(FirewallRule).filter(FirewallRule.created_by == user_id)
        
        if workload_id:
            query = query.filter(FirewallRule.workload_id == workload_id)
        if status:
            query = query.filter(FirewallRule.status == status)
        
        total = query.count()
        query = query.order_by(desc(FirewallRule.created_at))
        
        skip = (page - 1) * page_size
        items = query.offset(skip).limit(page_size).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    
    @staticmethod
    def get_firewall_rule(db: Session, rule_id: UUID) -> FirewallRule:
        """Get a single firewall rule."""
        rule = db.query(FirewallRule).filter(FirewallRule.id == rule_id).first()
        if not rule:
            raise ValueError(f"Firewall rule {rule_id} not found")
        return rule
    
    @staticmethod
    def create_firewall_rule(
        db: Session,
        rule_collection_name: str,
        priority: int,
        action: str,
        protocol: str,
        source_addresses: list[str] = None,
        destination_fqdns: list[str] = None,
        source_ip_groups: list[str] = None,
        destination_ports: list[int] = None,
        description: str = None,
        workload_id: UUID = None,
        azure_resource_id: str = None,
        user_id: UUID = None,
    ) -> FirewallRule:
        """Create a new firewall rule."""
        rule = FirewallRule(
            rule_collection_name=rule_collection_name,
            priority=priority,
            action=action,
            protocol=protocol,
            source_addresses=source_addresses,
            destination_fqdns=destination_fqdns,
            source_ip_groups=source_ip_groups,
            destination_ports=destination_ports,
            description=description,
            workload_id=workload_id,
            azure_resource_id=azure_resource_id,
            created_by=user_id,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule
    
    @staticmethod
    def update_firewall_rule(
        db: Session,
        rule_id: UUID,
        user_id: UUID,
        **kwargs
    ) -> FirewallRule:
        """Update an existing firewall rule."""
        rule = db.query(FirewallRule).filter(FirewallRule.id == rule_id).first()
        if not rule:
            raise ValueError(f"Firewall rule {rule_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(rule, key) and value is not None:
                setattr(rule, key, value)
        
        rule.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(rule)
        return rule
    
    @staticmethod
    def delete_firewall_rule(db: Session, rule_id: UUID) -> bool:
        """Delete a firewall rule."""
        rule = db.query(FirewallRule).filter(FirewallRule.id == rule_id).first()
        if not rule:
            raise ValueError(f"Firewall rule {rule_id} not found")
        
        db.delete(rule)
        db.commit()
        return True
    
    @staticmethod
    def import_firewall_rules_from_azure(db: Session, rules_data: list[dict]) -> list:
        """Import firewall rules from Azure."""
        imported = []
        for rule_data in rules_data:
            rule = FirewallRule(
                rule_collection_name=rule_data.get("rule_collection_name"),
                priority=rule_data.get("priority"),
                action=rule_data.get("action"),
                protocol=rule_data.get("protocol"),
                source_addresses=rule_data.get("source_addresses"),
                destination_fqdns=rule_data.get("destination_fqdns"),
                source_ip_groups=rule_data.get("source_ip_groups"),
                destination_ports=rule_data.get("destination_ports"),
                description=rule_data.get("description"),
                azure_resource_id=rule_data.get("azure_resource_id"),
            )
            db.add(rule)
            imported.append(rule)
        
        db.commit()
        return imported


class WorkloadService:
    """Service for workload management."""
    
    @staticmethod
    def get_workloads(db: Session) -> list:
        """Get all workloads."""
        return db.query(Workload).all()
    
    @staticmethod
    def get_workload(db: Session, workload_id: UUID) -> Workload:
        """Get a single workload."""
        workload = db.query(Workload).filter(Workload.id == workload_id).first()
        if not workload:
            raise ValueError(f"Workload {workload_id} not found")
        return workload
    
    @staticmethod
    def create_workload(
        db: Session,
        name: str,
        description: str = None,
        owner_id: UUID = None,
        resource_groups: list[str] = None,
        subscriptions: list[str] = None,
    ) -> Workload:
        """Create a new workload."""
        workload = Workload(
            name=name,
            description=description,
            owner_id=owner_id,
            resource_groups=resource_groups,
            subscriptions=subscriptions,
        )
        db.add(workload)
        db.commit()
        db.refresh(workload)
        return workload
    
    @staticmethod
    def update_workload(
        db: Session,
        workload_id: UUID,
        **kwargs
    ) -> Workload:
        """Update a workload."""
        workload = db.query(Workload).filter(Workload.id == workload_id).first()
        if not workload:
            raise ValueError(f"Workload {workload_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(workload, key) and value is not None:
                setattr(workload, key, value)
        
        db.commit()
        db.refresh(workload)
        return workload
    
    @staticmethod
    def delete_workload(db: Session, workload_id: UUID) -> bool:
        """Delete a workload."""
        workload = db.query(Workload).filter(Workload.id == workload_id).first()
        if not workload:
            raise ValueError(f"Workload {workload_id} not found")
        
        db.delete(workload)
        db.commit()
        return True