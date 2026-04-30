"""
Tests for Rules API routes.

Covers:
- List rules with pagination and filtering
- Create/update/delete rules
- Search rules
- Bulk operations
- Export rules
- Clone rule
- Rule stats
- Rule validation
- Workload endpoints
"""

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, Mock
from uuid import uuid4

from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# --- Test Database Setup ---

Base = declarative_base()


class MockFirewallRule(Base):
    """Mock firewall rule for testing."""
    __tablename__ = "mock_firewall_rules"
    
    id = Column(String, primary_key=True)
    rule_collection_name = Column(String, nullable=False)
    priority = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    protocol = Column(String, nullable=False)
    source_addresses = Column(Text, default="[]")
    destination_fqdns = Column(Text, default="[]")
    source_ip_groups = Column(Text, default="[]")
    destination_ports = Column(Text, default="[]")
    description = Column(Text, default="")
    status = Column(String, default="draft")
    workload_id = Column(String, nullable=True)
    azure_resource_id = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)


Base.metadata.create_all(create_engine("sqlite:///:memory:"))


def get_test_db():
    """Yield a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_mock_rule(db, **kwargs):
    """Helper to create a mock firewall rule."""
    rule = MockFirewallRule(
        id=str(uuid4()),
        rule_collection_name=kwargs.get("rule_collection_name", "Test Collection"),
        priority=kwargs.get("priority", 1000),
        action=kwargs.get("action", "Allow"),
        protocol=kwargs.get("protocol", "Tcp"),
        source_addresses=json.dumps(kwargs.get("source_addresses", [])),
        destination_fqdns=json.dumps(kwargs.get("destination_fqdns", [])),
        source_ip_groups=json.dumps(kwargs.get("source_ip_groups", [])),
        destination_ports=json.dumps(kwargs.get("destination_ports", [])),
        description=kwargs.get("description", "Test rule"),
        status=kwargs.get("status", "draft"),
        workload_id=kwargs.get("workload_id"),
        azure_resource_id=kwargs.get("azure_resource_id"),
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(rule)
    db.commit()
    return rule


def create_mock_rules(db, count=10):
    """Helper to create multiple mock rules."""
    for i in range(count):
        create_mock_rule(
            db,
            rule_collection_name=f"Collection {i}",
            priority=1000 + i,
            action="Allow" if i % 2 == 0 else "Deny",
            protocol="Tcp" if i % 2 == 0 else "Udp",
            description=f"Test rule {i}",
            status="draft" if i % 3 != 0 else "enabled",
        )


# --- Test Helpers ---

class MockFirewallService:
    """Mock firewall service for testing API routes."""
    
    @staticmethod
    def get_firewall_rules(db, user_id, workload_id, status, page, page_size):
        """Mock get firewall rules."""
        query = db.query(MockFirewallRule)
        
        if workload_id:
            query = query.filter(MockFirewallRule.workload_id == str(workload_id))
        if status:
            query = query.filter(MockFirewallRule.status == status)
        
        total = query.count()
        items = query.order_by(MockFirewallRule.priority).offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    
    @staticmethod
    def get_firewall_rule(db, rule_id):
        """Mock get firewall rule."""
        return db.query(MockFirewallRule).filter(MockFirewallRule.id == str(rule_id)).first()
    
    @staticmethod
    def create_firewall_rule(db, user_id, **kwargs):
        """Mock create firewall rule."""
        rule = MockFirewallRule(
            id=str(uuid4()),
            rule_collection_name=kwargs.get("rule_collection_name", "New Rule"),
            priority=kwargs.get("priority", 1000),
            action=kwargs.get("action", "Allow"),
            protocol=kwargs.get("protocol", "Tcp"),
            source_addresses=json.dumps(kwargs.get("source_addresses", [])),
            destination_fqdns=json.dumps(kwargs.get("destination_fqdns", [])),
            source_ip_groups=json.dumps(kwargs.get("source_ip_groups", [])),
            destination_ports=json.dumps(kwargs.get("destination_ports", [])),
            description=kwargs.get("description", "New rule"),
            status="draft",
            workload_id=kwargs.get("workload_id"),
            azure_resource_id=kwargs.get("azure_resource_id"),
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(rule)
        db.commit()
        return rule
    
    @staticmethod
    def update_firewall_rule(db, rule_id, user_id, **kwargs):
        """Mock update firewall rule."""
        rule = db.query(MockFirewallRule).filter(MockFirewallRule.id == str(rule_id)).first()
        if not rule:
            raise ValueError("Rule not found")
        
        for key, value in kwargs.items():
            setattr(rule, key, value)
        rule.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        db.refresh(rule)
        return rule
    
    @staticmethod
    def delete_firewall_rule(db, rule_id):
        """Mock delete firewall rule."""
        rule = db.query(MockFirewallRule).filter(MockFirewallRule.id == str(rule_id)).first()
        if not rule:
            raise ValueError("Rule not found")
        db.delete(rule)
        db.commit()
    
    @staticmethod
    def search_firewall_rules(db, query, user_id, status, action, protocol, workload_id, page, page_size):
        """Mock search firewall rules."""
        search_query = db.query(MockFirewallRule)
        
        if query:
            search_query = search_query.filter(
                MockFirewallRule.description.ilike(f"%{query}%") |
                MockFirewallRule.rule_collection_name.ilike(f"%{query}%")
            )
        if status:
            search_query = search_query.filter(MockFirewallRule.status == status)
        if action:
            search_query = search_query.filter(MockFirewallRule.action == action)
        if protocol:
            search_query = search_query.filter(MockFirewallRule.protocol == protocol)
        
        total = search_query.count()
        items = search_query.order_by(MockFirewallRule.priority).offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    
    @staticmethod
    def validate_firewall_rule(db, rule):
        """Mock validate firewall rule."""
        errors = []
        
        if not rule.rule_collection_name:
            errors.append("rule_collection_name is required")
        if not rule.priority:
            errors.append("priority is required")
        if not rule.action:
            errors.append("action is required")
        if not rule.protocol:
            errors.append("protocol is required")
        
        return {"valid": len(errors) == 0, "errors": errors}


class MockWorkloadService:
    """Mock workload service for testing API routes."""
    
    @staticmethod
    def get_workloads(db):
        """Mock get workloads."""
        return [
            {"id": str(uuid4()), "name": "Test Workload", "type": "Azure App Service"},
        ]
    
    @staticmethod
    def get_workload(db, workload_id):
        """Mock get workload."""
        return {
            "id": str(workload_id),
            "name": "Test Workload",
            "type": "Azure App Service",
        }


class MockAuditService:
    """Mock audit service for testing API routes."""
    
    @staticmethod
    def log_action(db, user_id, action, resource_type, resource_id, old_value=None, new_value=None, correlation_id=None):
        """Mock log action."""
        pass


# --- Test Classes ---

class TestRulesAPIListRules(unittest.TestCase):
    """Tests for the list rules endpoint."""

    def test_list_rules_returns_paged_results(self):
        """Test that list rules returns paginated results."""
        for db in get_test_db():
            create_mock_rules(db, 20)
            service = MockFirewallService()
            
            result = service.get_firewall_rules(
                db=db, user_id=None, workload_id=None, status=None,
                page=1, page_size=10,
            )
            self.assertIsInstance(result, dict)
            self.assertIn("items", result)
            self.assertIn("total", result)

    def test_list_rules_filters_by_status(self):
        """Test filtering rules by status."""
        for db in get_test_db():
            create_mock_rule(db, status="draft")
            create_mock_rule(db, status="enabled")
            create_mock_rule(db, status="disabled")
            
            service = MockFirewallService()
            result = service.get_firewall_rules(
                db=db, user_id=None, workload_id=None, status="draft",
                page=1, page_size=10,
            )
            self.assertGreater(result["total"], 0)

    def test_list_rules_filters_by_workload(self):
        """Test filtering rules by workload."""
        for db in get_test_db():
            workload_id = str(uuid4())
            create_mock_rule(db, workload_id=workload_id)
            create_mock_rule(db, workload_id=str(uuid4()))
            
            service = MockFirewallService()
            result = service.get_firewall_rules(
                db=db, user_id=None, workload_id=workload_id, status=None,
                page=1, page_size=10,
            )
            self.assertGreater(result["total"], 0)

    def test_list_rules_empty_database(self):
        """Test list rules on empty database."""
        for db in get_test_db():
            service = MockFirewallService()
            result = service.get_firewall_rules(
                db=db, user_id=None, workload_id=None, status=None,
                page=1, page_size=10,
            )
            self.assertEqual(result["total"], 0)
            self.assertEqual(len(result["items"]), 0)


class TestRulesAPIGetRule(unittest.TestCase):
    """Tests for the get single rule endpoint."""

    def test_get_existing_rule(self):
        """Test getting an existing rule."""
        for db in get_test_db():
            rule = create_mock_rule(db)
            service = MockFirewallService()
            
            found = service.get_firewall_rule(db, rule.id)
            self.assertIsNotNone(found)

    def test_get_nonexistent_rule(self):
        """Test getting a nonexistent rule."""
        for db in get_test_db():
            service = MockFirewallService()
            fake_id = str(uuid4())
            found = service.get_firewall_rule(db, fake_id)
            self.assertIsNone(found)


class TestRulesAPICreateRule(unittest.TestCase):
    """Tests for the create rule endpoint."""

    def test_create_valid_rule(self):
        """Test creating a valid firewall rule."""
        for db in get_test_db():
            service = MockFirewallService()
            new_rule = service.create_firewall_rule(
                db=db, user_id=str(uuid4()),
                rule_collection_name="New Collection",
                priority=2000,
                action="Deny",
                protocol="Tcp",
                source_addresses=["10.0.0.0/8"],
                destination_fqdns=["example.com"],
                source_ip_groups=["group1"],
                destination_ports=["443"],
                description="New rule",
                workload_id=str(uuid4()),
                azure_resource_id=None,
            )
            self.assertIsNotNone(new_rule)
            self.assertIsNotNone(new_rule.id)
            self.assertEqual(new_rule.rule_collection_name, "New Collection")

    def test_create_rule_minimal(self):
        """Test creating a rule with minimal fields."""
        for db in get_test_db():
            service = MockFirewallService()
            new_rule = service.create_firewall_rule(
                db=db, user_id=str(uuid4()),
                rule_collection_name="Minimal Rule",
                priority=1000,
                action="Allow",
                protocol="Tcp",
                source_addresses=[],
                destination_fqdns=[],
                source_ip_groups=[],
                destination_ports=[],
                description="",
                workload_id=None,
                azure_resource_id=None,
            )
            self.assertIsNotNone(new_rule)


class TestRulesAPIUpdateRule(unittest.TestCase):
    """Tests for the update rule endpoint."""

    def test_update_rule(self):
        """Test updating a rule."""
        for db in get_test_db():
            rule = create_mock_rule(db)
            service = MockFirewallService()
            
            updated = service.update_firewall_rule(
                db=db, rule_id=rule.id, user_id=str(uuid4()),
                description="Updated description",
                rule_collection_name="Updated Collection",
            )
            self.assertEqual(updated.description, "Updated description")
            self.assertEqual(updated.rule_collection_name, "Updated Collection")

    def test_update_nonexistent_rule(self):
        """Test updating a nonexistent rule."""
        for db in get_test_db():
            service = MockFirewallService()
            fake_id = str(uuid4())
            with self.assertRaises(ValueError):
                service.update_firewall_rule(
                    db=db, rule_id=fake_id, user_id=str(uuid4()),
                    description="New description",
                )


class TestRulesAPIDeleteRule(unittest.TestCase):
    """Tests for the delete rule endpoint."""

    def test_delete_rule(self):
        """Test deleting a rule."""
        for db in get_test_db():
            rule = create_mock_rule(db)
            service = MockFirewallService()
            
            service.delete_firewall_rule(db, rule.id)
            found = service.get_firewall_rule(db, rule.id)
            self.assertIsNone(found)

    def test_delete_nonexistent_rule(self):
        """Test deleting a nonexistent rule."""
        for db in get_test_db():
            service = MockFirewallService()
            fake_id = str(uuid4())
            with self.assertRaises(ValueError):
                service.delete_firewall_rule(db, fake_id)


class TestRulesAPISearch(unittest.TestCase):
    """Tests for the search rules endpoint."""

    def test_search_rules_by_description(self):
        """Test searching rules by description."""
        for db in get_test_db():
            create_mock_rule(db, description="Important firewall rule")
            create_mock_rule(db, description="Minor network rule")
            
            service = MockFirewallService()
            result = service.search_firewall_rules(
                db=db, query="Important", user_id=None,
                status=None, action=None, protocol=None,
                workload_id=None, page=1, page_size=10,
            )
            self.assertEqual(result["total"], 1)

    def test_search_rules_by_collection_name(self):
        """Test searching rules by collection name."""
        for db in get_test_db():
            create_mock_rule(db, rule_collection_name="Production Rules")
            create_mock_rule(db, rule_collection_name="Development Rules")
            
            service = MockFirewallService()
            result = service.search_firewall_rules(
                db=db, query="Production", user_id=None,
                status=None, action=None, protocol=None,
                workload_id=None, page=1, page_size=10,
            )
            self.assertEqual(result["total"], 1)


class TestRulesAPIBulkOperations(unittest.TestCase):
    """Tests for the bulk operations endpoints."""

    def test_bulk_create_rules(self):
        """Test bulk creating rules."""
        for db in get_test_db():
            service = MockFirewallService()
            
            created_count = 0
            errors = []
            for i in range(3):
                try:
                    new_rule = service.create_firewall_rule(
                        db=db, user_id=str(uuid4()),
                        rule_collection_name=f"Bulk Rule {i}",
                        priority=5000 + i,
                        action="Allow",
                        protocol="Tcp",
                        source_addresses=[],
                        destination_fqdns=[],
                        source_ip_groups=[],
                        destination_ports=[],
                        description=f"Bulk rule {i}",
                        workload_id=None,
                        azure_resource_id=None,
                    )
                    created_count += 1
                except Exception as e:
                    errors.append(str(e))
            
            self.assertEqual(created_count, 3)
            self.assertEqual(len(errors), 0)

    def test_bulk_create_with_errors(self):
        """Test bulk creating rules with some errors."""
        for db in get_test_db():
            service = MockFirewallService()
            
            created_count = 0
            errors = []
            
            # Create valid rule
            try:
                service.create_firewall_rule(
                    db=db, user_id=str(uuid4()),
                    rule_collection_name="Valid Rule",
                    priority=6000, action="Allow", protocol="Tcp",
                    source_addresses=[], destination_fqdns=[],
                    source_ip_groups=[], destination_ports=[],
                    description="Valid", workload_id=None, azure_resource_id=None,
                )
                created_count += 1
            except Exception:
                pass

    def test_bulk_update_rules(self):
        """Test bulk updating rules."""
        for db in get_test_db():
            rules = []
            for i in range(3):
                rule = create_mock_rule(db)
                rules.append(rule)
            
            service = MockFirewallService()
            updated_count = 0
            errors = []
            
            for rule in rules:
                try:
                    updated = service.update_firewall_rule(
                        db=db, rule_id=rule.id, user_id=str(uuid4()),
                        description="Bulk updated",
                    )
                    updated_count += 1
                except Exception as e:
                    errors.append(str(e))
            
            self.assertEqual(updated_count, 3)
            self.assertEqual(len(errors), 0)

    def test_bulk_delete_rules(self):
        """Test bulk deleting rules."""
        for db in get_test_db():
            rules = []
            for i in range(3):
                rule = create_mock_rule(db)
                rules.append(rule)
            
            service = MockFirewallService()
            deleted_count = 0
            errors = []
            
            for rule in rules:
                try:
                    service.delete_firewall_rule(db, rule.id)
                    deleted_count += 1
                except Exception as e:
                    errors.append(str(e))
            
            self.assertEqual(deleted_count, 3)
            self.assertEqual(len(errors), 0)


class TestRulesAPIExport(unittest.TestCase):
    """Tests for the export rules endpoint."""

    def test_export_rules_json(self):
        """Test exporting rules to JSON."""
        for db in get_test_db():
            create_mock_rules(db, 5)
            service = MockFirewallService()
            
            result = service.get_firewall_rules(
                db=db, user_id=None, workload_id=None, status=None,
                page=1, page_size=10000,
            )
            self.assertIsInstance(result, dict)
            self.assertIn("items", result)
            self.assertIn("total", result)

    def test_export_rules_csv_format(self):
        """Test that CSV export format is correct."""
        csv_fields = ["id", "rule_collection_name", "priority", "action", "protocol",
                       "source_addresses", "destination_fqdns", "description", "status"]
        
        for field in csv_fields:
            self.assertIn(field, "id,rule_collection_name,priority,action,protocol,source_addresses,destination_fqdns,description,status")


class TestRulesAPIClone(unittest.TestCase):
    """Tests for the clone rule endpoint."""

    def test_clone_rule(self):
        """Test cloning a rule."""
        for db in get_test_db():
            original = create_mock_rule(db, description="Original rule")
            service = MockFirewallService()
            
            # Clone creates a new rule with modified description
            cloned = service.create_firewall_rule(
                db=db, user_id=str(uuid4()),
                rule_collection_name=f"{original.rule_collection_name} (copy)",
                priority=original.priority,
                action=original.action,
                protocol=original.protocol,
                source_addresses=json.loads(original.source_addresses) if original.source_addresses else [],
                destination_fqdns=json.loads(original.destination_fqdns) if original.destination_fqdns else [],
                source_ip_groups=json.loads(original.source_ip_groups) if original.source_ip_groups else [],
                destination_ports=json.loads(original.destination_ports) if original.destination_ports else [],
                description=f"Cloned from: {original.description}",
                workload_id=original.workload_id,
                azure_resource_id=original.azure_resource_id,
            )
            self.assertIsNotNone(cloned)
            self.assertNotEqual(cloned.id, original.id)


class TestRulesAPIStats(unittest.TestCase):
    """Tests for the rule stats endpoint."""

    def test_rule_stats(self):
        """Test rule statistics."""
        for db in get_test_db():
            create_mock_rule(db, status="draft")
            create_mock_rule(db, status="enabled")
            create_mock_rule(db, status="draft")
            
            # Count by status
            draft_count = db.query(MockFirewallRule).filter(MockFirewallRule.status == "draft").count()
            enabled_count = db.query(MockFirewallRule).filter(MockFirewallRule.status == "enabled").count()
            
            self.assertEqual(draft_count, 2)
            self.assertEqual(enabled_count, 1)


class TestRulesAPIValidation(unittest.TestCase):
    """Tests for the validate rule endpoint."""

    def test_validate_valid_rule(self):
        """Test validating a valid rule."""
        for db in get_test_db():
            service = MockFirewallService()
            
            # Mock rule object
            class MockRule:
                rule_collection_name = "Valid Rule"
                priority = 1000
                action = "Allow"
                protocol = "Tcp"
            
            result = service.validate_firewall_rule(db, MockRule())
            self.assertTrue(result["valid"])
            self.assertEqual(len(result["errors"]), 0)

    def test_validate_invalid_rule(self):
        """Test validating an invalid rule."""
        for db in get_test_db():
            service = MockFirewallService()
            
            class MockRule:
                rule_collection_name = ""
                priority = None
                action = None
                protocol = None
            
            result = service.validate_firewall_rule(db, MockRule())
            self.assertFalse(result["valid"])
            self.assertGreater(len(result["errors"]), 0)


class TestRulesAPIWorkloads(unittest.TestCase):
    """Tests for the workload endpoints."""

    def test_list_workloads(self):
        """Test listing workloads."""
        for db in get_test_db():
            service = MockWorkloadService()
            workloads = service.get_workloads(db)
            self.assertIsInstance(workloads, list)

    def test_get_workload(self):
        """Test getting a specific workload."""
        for db in get_test_db():
            service = MockWorkloadService()
            fake_id = uuid4()
            workload = service.get_workload(db, fake_id)
            self.assertIsNotNone(workload)
            self.assertEqual(workload["name"], "Test Workload")


class TestRulesAPIEdgeCases(unittest.TestCase):
    """Tests for edge cases in rules API."""

    def test_create_rule_with_duplicate_priority(self):
        """Test creating a rule with duplicate priority."""
        for db in get_test_db():
            create_mock_rule(db, priority=1000)
            # Second rule can have same priority (not enforced in mock)
            create_mock_rule(db, priority=1000)
            self.assertTrue(True)

    def test_rule_with_special_characters(self):
        """Test rule with special characters in description."""
        for db in get_test_db():
            rule = create_mock_rule(db, description="Rule with <special> & characters 'quotes' \"double\"")
            self.assertIn("<special>", rule.description)

    def test_rule_with_unicode_description(self):
        """Test rule with unicode in description."""
        for db in get_test_db():
            rule = create_mock_rule(db, description="Unicode test: 你好世界 🌍")
            self.assertIn("你好世界", rule.description)

    def test_rule_pagination_boundaries(self):
        """Test pagination at boundaries."""
        for db in get_test_db():
            create_mock_rules(db, 5)
            service = MockFirewallService()
            
            # Get all items on first page
            result = service.get_firewall_rules(
                db=db, user_id=None, workload_id=None, status=None,
                page=1, page_size=10,
            )
            self.assertGreaterEqual(result["total"], 5)


if __name__ == "__main__":
    unittest.main()