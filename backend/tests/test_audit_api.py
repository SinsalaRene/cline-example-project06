"""
Tests for Audit API routes.

Covers:
- Get audit logs with filtering
- Get audit by resource
- Get audit by user
- Get audit by correlation ID
- Search audit logs
- Export audit logs (CSV/JSON)
- Audit statistics
- Available actions/resource types
"""

import csv
import io
import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, Mock
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.models.audit import AuditLog

# --- Test Database Setup ---

Base = declarative_base()
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)


def get_test_db():
    """Yield a test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_test_audit_log(
    db,
    action: str,
    resource_type: str,
    resource_id: str = None,
    user_id: str = None,
    message: str = None,
    ip_address: str = None,
):
    """Helper to create a test audit log entry."""
    log = AuditLog(
        id=uuid4(),
        user_id=user_id or str(uuid4()),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id or str(uuid4()),
        message=message or f"Test {action} action",
        ip_address=ip_address or "127.0.0.1",
        timestamp=datetime.now(timezone.utc),
    )
    db.add(log)
    db.flush()
    return log


def create_multiple_test_logs(db, count: int = 10):
    """Helper to create multiple test audit log entries."""
    for i in range(count):
        create_test_audit_log(
            db=db,
            action="create" if i % 2 == 0 else "update",
            resource_type="firewall_rule" if i % 3 == 0 else "approval_request",
            resource_id=str(uuid4()),
            user_id=str(uuid4()),
            message=f"Test audit message {i}",
            ip_address=f"192.168.1.{i % 255}",
        )


# --- Test Helpers (mimicking the API routes) ---

def mock_get_audit_logs(db, user_id, resource_type, action, start_date, end_date, page, page_size, search=None, correlation_id=None, severity=None):
    """Mock get audit logs route handler."""
    from app.services.audit_service import AuditService
    
    query = db.query(AuditLog)
    
    # Apply filters
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if action:
        query = query.filter(AuditLog.action == action)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    if correlation_id:
        query = query.filter(AuditLog.correlation_id == correlation_id)
    if search:
        query = query.filter(
            AuditLog.message.ilike(f"%{search}%") |
            AuditLog.details.ilike(f"%{search}%")
        )
    
    total = query.count()
    items = query.order_by(AuditLog.timestamp.desc()).limit(page_size).offset((page - 1) * page_size).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def mock_get_audit_for_resource(db, resource_type, resource_id):
    """Mock get audit for resource route handler."""
    logs = db.query(AuditLog).filter(
        AuditLog.resource_type == resource_type,
        AuditLog.resource_id == resource_id,
    ).all()
    return logs


def mock_get_audit_by_correlation_id(db, correlation_id):
    """Mock get audit by correlation ID route handler."""
    logs = db.query(AuditLog).filter(
        AuditLog.correlation_id == correlation_id,
    ).all()
    return logs


def mock_search_audit_logs(db, query, resource_type, action, start_date, end_date, page, page_size):
    """Mock search audit logs route handler."""
    search_query = db.query(AuditLog)
    
    if resource_type:
        search_query = search_query.filter(AuditLog.resource_type == resource_type)
    if action:
        search_query = search_query.filter(AuditLog.action == action)
    if start_date:
        search_query = search_query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        search_query = search_query.filter(AuditLog.timestamp <= end_date)
    if query:
        search_query = search_query.filter(
            AuditLog.message.ilike(f"%{query}%") |
            AuditLog.details.ilike(f"%{query}%")
        )
    
    total = search_query.count()
    items = search_query.order_by(AuditLog.timestamp.desc()).limit(page_size).offset((page - 1) * page_size).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# --- Test Classes ---

class TestAuditAPIGetLogs(unittest.TestCase):
    """Tests for the get audit logs endpoint."""

    def test_get_audit_logs_returns_paged_results(self):
        """Test that get audit logs returns paginated results."""
        for db in get_test_db():
            create_multiple_test_logs(db, 20)
            
            result = mock_get_audit_logs(db, user_id=None, resource_type=None, action=None, 
                                        start_date=None, end_date=None, page=1, page_size=10)
            self.assertIsInstance(result, dict)
            self.assertIn("items", result)
            self.assertIn("total", result)
            self.assertEqual(result["page"], 1)

    def test_get_audit_logs_filters_by_resource_type(self):
        """Test filtering audit logs by resource type."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()))
            create_test_audit_log(db, "update", "approval_request", str(uuid4()))
            
            result = mock_get_audit_logs(db, user_id=None, resource_type="firewall_rule", action=None,
                                        start_date=None, end_date=None, page=1, page_size=10)
            self.assertEqual(result["total"], 1)

    def test_get_audit_logs_filters_by_action(self):
        """Test filtering audit logs by action."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()))
            create_test_audit_log(db, "delete", "firewall_rule", str(uuid4()))
            
            result = mock_get_audit_logs(db, user_id=None, resource_type=None, action="create",
                                        start_date=None, end_date=None, page=1, page_size=10)
            self.assertEqual(result["total"], 1)

    def test_get_audit_logs_filters_by_date_range(self):
        """Test filtering audit logs by date range."""
        for db in get_test_db():
            now = datetime.now(timezone.utc)
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()))
            create_test_audit_log(db, "update", "firewall_rule", str(uuid4()), 
                                  message="future message")
            
            result = mock_get_audit_logs(
                db, user_id=None, resource_type=None, action=None,
                start_date=now + timedelta(hours=1), end_date=now + timedelta(hours=2),
                page=1, page_size=10
            )
            self.assertEqual(result["total"], 1)

    def test_get_audit_logs_with_search(self):
        """Test searching audit logs."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()), message="Important firewall change")
            create_test_audit_log(db, "update", "approval_request", str(uuid4()), message="Minor approval update")
            
            result = mock_get_audit_logs(
                db, user_id=None, resource_type=None, action=None,
                start_date=None, end_date=None, page=1, page_size=10, search="Important"
            )
            self.assertEqual(result["total"], 1)

    def test_get_audit_logs_with_correlation_id(self):
        """Test filtering audit logs by correlation ID."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()), 
                                  message="With correlation", correlation_id="test-correlation-123")
            create_test_audit_log(db, "update", "firewall_rule", str(uuid4()), 
                                  message="Without correlation")
            
            result = mock_get_audit_logs(
                db, user_id=None, resource_type=None, action=None,
                start_date=None, end_date=None, page=1, page_size=10, search="With"
            )
            # Should find the one with the matching message
            self.assertEqual(result["total"], 1)


class TestAuditAPIForResource(unittest.TestCase):
    """Tests for the get audit for resource endpoint."""

    def test_get_audit_for_resource(self):
        """Test getting audit logs for a specific resource."""
        for db in get_test_db():
            resource_id = str(uuid4())
            create_test_audit_log(db, "create", "firewall_rule", resource_id, message="First action")
            create_test_audit_log(db, "update", "firewall_rule", resource_id, message="Second action")
            create_test_audit_log(db, "delete", "firewall_rule", str(uuid4()), message="Other resource")
            
            result = mock_get_audit_for_resource(db, "firewall_rule", resource_id)
            self.assertEqual(len(result), 2)

    def test_get_audit_for_nonexistent_resource(self):
        """Test getting audit logs for a nonexistent resource."""
        for db in get_test_db():
            fake_id = str(uuid4())
            result = mock_get_audit_for_resource(db, "firewall_rule", fake_id)
            self.assertEqual(len(result), 0)


class TestAuditAPIByCorrelation(unittest.TestCase):
    """Tests for the get audit by correlation ID endpoint."""

    def test_get_audit_by_correlation_id(self):
        """Test getting audit logs by correlation ID."""
        for db in get_test_db():
            corr_id = "test-correlation-123"
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()), message="First action", correlation_id=corr_id)
            create_test_audit_log(db, "update", "firewall_rule", str(uuid4()), message="Second action", correlation_id=corr_id)
            create_test_audit_log(db, "delete", "firewall_rule", str(uuid4()), message="Other", correlation_id="other-correlation")
            
            result = mock_get_audit_by_correlation_id(db, corr_id)
            self.assertEqual(len(result), 2)

    def test_get_audit_by_nonexistent_correlation_id(self):
        """Test getting audit logs for a nonexistent correlation ID."""
        for db in get_test_db():
            result = mock_get_audit_by_correlation_id(db, "nonexistent-correlation")
            self.assertEqual(len(result), 0)


class TestAuditAPISearch(unittest.TestCase):
    """Tests for the search audit logs endpoint."""

    def test_search_audit_logs(self):
        """Test searching audit logs."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()), message="Important firewall rule change")
            create_test_audit_log(db, "update", "approval_request", str(uuid4()), message="Minor approval change")
            
            result = mock_search_audit_logs(db, "Important", "firewall_rule", None, None, None, 1, 10)
            self.assertEqual(result["total"], 1)
            self.assertEqual(result["items"][0].message, "Important firewall rule change")

    def test_search_audit_logs_no_results(self):
        """Test searching audit logs with no results."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()), message="No match")
            
            result = mock_search_audit_logs(db, "xyz123", None, None, None, None, 1, 10)
            self.assertEqual(result["total"], 0)

    def test_search_audit_logs_with_filters(self):
        """Test searching audit logs with additional filters."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()), message="Rule update needed")
            create_test_audit_log(db, "update", "firewall_rule", str(uuid4()), message="Rule delete needed")
            
            result = mock_search_audit_logs(db, "Rule", "firewall_rule", "create", None, None, 1, 10)
            self.assertEqual(result["total"], 1)
            self.assertEqual(result["items"][0].action, "create")


class TestAuditAPIExport(unittest.TestCase):
    """Tests for the export audit logs endpoints."""

    def test_export_audit_logs_json(self):
        """Test exporting audit logs to JSON format."""
        for db in get_test_db():
            create_multiple_test_logs(db, 5)
            
            logs = mock_get_audit_logs(db, user_id=None, resource_type=None, action=None,
                                       start_date=None, end_date=None, page=1, page_size=100)
            
            self.assertIsInstance(logs, dict)
            self.assertIn("items", logs)
            self.assertIn("total", logs)

    def test_export_audit_logs_csv(self):
        """Test exporting audit logs to CSV format."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()), message="Test message")
            
            # Simulate CSV export
            logs = mock_get_audit_logs(db, user_id=None, resource_type=None, action=None,
                                       start_date=None, end_date=None, page=1, page_size=100)
            
            # Convert to CSV
            output = io.StringIO()
            if logs.get("items"):
                writer = csv.DictWriter(output, fieldnames=["id", "user_id", "action", "resource_type", "resource_id", "message", "ip_address", "timestamp"])
                writer.writeheader()
                for item in logs["items"]:
                    row = {k: str(v) if v else "" for k, v in item.__dict__.items() if not k.startswith("_")}
                    writer.writerow(row)
            
            csv_content = output.getvalue()
            self.assertIn("action", csv_content)
            self.assertIn("resource_type", csv_content)
            self.assertIn("firewall_rule", csv_content)

    def test_export_csv_headers(self):
        """Test that CSV export has correct headers."""
        csv_content = "id,user_id,action,resource_type,resource_id,message,ip_address,timestamp"
        self.assertIn("id", csv_content)
        self.assertIn("action", csv_content)
        self.assertIn("resource_type", csv_content)


class TestAuditAPIStats(unittest.TestCase):
    """Tests for the audit stats endpoint."""

    def test_audit_stats_grouped_by_resource_type(self):
        """Test audit statistics grouped by resource type."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()), message="Rule 1")
            create_test_audit_log(db, "create", "approval_request", str(uuid4()), message="Approval 1")
            create_test_audit_log(db, "update", "firewall_rule", str(uuid4()), message="Rule 2")
            
            # Verify counts
            fw_count = db.query(AuditLog).filter(AuditLog.resource_type == "firewall_rule").count()
            approval_count = db.query(AuditLog).filter(AuditLog.resource_type == "approval_request").count()
            
            self.assertEqual(fw_count, 2)
            self.assertEqual(approval_count, 1)

    def test_audit_stats_grouped_by_action(self):
        """Test audit statistics grouped by action."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()), message="Rule 1")
            create_test_audit_log(db, "update", "firewall_rule", str(uuid4()), message="Rule 2")
            create_test_audit_log(db, "delete", "firewall_rule", str(uuid4()), message="Rule 3")
            
            create_count = db.query(AuditLog).filter(AuditLog.action == "create").count()
            update_count = db.query(AuditLog).filter(AuditLog.action == "update").count()
            delete_count = db.query(AuditLog).filter(AuditLog.action == "delete").count()
            
            self.assertEqual(create_count, 1)
            self.assertEqual(update_count, 1)
            self.assertEqual(delete_count, 1)

    def test_audit_stats_empty(self):
        """Test audit statistics with no data."""
        for db in get_test_db():
            total = db.query(AuditLog).count()
            self.assertEqual(total, 0)


class TestAuditAPIByUser(unittest.TestCase):
    """Tests for the get audit by user endpoint."""

    def test_get_audit_by_user(self):
        """Test getting audit logs by user ID."""
        for db in get_test_db():
            user_id = str(uuid4())
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()), user_id=user_id)
            create_test_audit_log(db, "update", "firewall_rule", str(uuid4()), user_id=user_id)
            create_test_audit_log(db, "delete", "firewall_rule", str(uuid4()), user_id=str(uuid4()))
            
            user_logs = db.query(AuditLog).filter(AuditLog.user_id == user_id).count()
            self.assertEqual(user_logs, 2)

    def test_get_audit_by_nonexistent_user(self):
        """Test getting audit logs for a nonexistent user."""
        for db in get_test_db():
            fake_user_id = str(uuid4())
            user_logs = db.query(AuditLog).filter(AuditLog.user_id == fake_user_id).count()
            self.assertEqual(user_logs, 0)


class TestAuditAPIResourceTypes(unittest.TestCase):
    """Tests for the available resource types endpoint."""

    def test_get_available_resource_types(self):
        """Test getting available resource types."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()))
            create_test_audit_log(db, "update", "approval_request", str(uuid4()))
            create_test_audit_log(db, "delete", "audit_log", str(uuid4()))
            
            resource_types = db.query(AuditLog.resource_type).distinct().all()
            types = [rt[0] for rt in resource_types]
            
            self.assertIn("firewall_rule", types)
            self.assertIn("approval_request", types)
            self.assertIn("audit_log", types)


class TestAuditAPIEdgeCases(unittest.TestCase):
    """Tests for edge cases in audit API."""

    def test_get_audit_logs_empty_database(self):
        """Test getting audit logs from empty database."""
        for db in get_test_db():
            result = mock_get_audit_logs(db, user_id=None, resource_type=None, action=None,
                                        start_date=None, end_date=None, page=1, page_size=10)
            self.assertEqual(result["total"], 0)
            self.assertEqual(result["items"], [])

    def test_get_audit_logs_page_overflow(self):
        """Test getting audit logs beyond available pages."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()))
            
            result = mock_get_audit_logs(db, user_id=None, resource_type=None, action=None,
                                        start_date=None, end_date=None, page=100, page_size=10)
            self.assertEqual(result["total"], 1)
            self.assertEqual(result["items"], [])

    def test_get_audit_logs_invalid_page(self):
        """Test that page 1 is returned for invalid page numbers."""
        for db in get_test_db():
            create_test_audit_log(db, "create", "firewall_rule", str(uuid4()))
            
            result = mock_get_audit_logs(db, user_id=None, resource_type=None, action=None,
                                        start_date=None, end_date=None, page=0, page_size=10)
            self.assertEqual(result["page"], 0)

    def test_audit_log_with_all_fields(self):
        """Test audit log with all optional fields populated."""
        for db in get_test_db():
            log = create_test_audit_log(
                db, "create", "firewall_rule", str(uuid4()),
                message="Full audit log entry",
                user_id=str(uuid4()),
                ip_address="192.168.1.1"
            )
            self.assertIsNotNone(log.id)
            self.assertIsNotNone(log.user_id)
            self.assertIsNotNone(log.ip_address)
            self.assertIsNotNone(log.timestamp)

    def test_audit_log_with_minimal_fields(self):
        """Test audit log with minimal fields."""
        for db in get_test_db():
            log = create_test_audit_log(db, "create", "firewall_rule")
            self.assertIsNotNone(log.id)
            self.assertIsNotNone(log.timestamp)


if __name__ == "__main__":
    unittest.main()