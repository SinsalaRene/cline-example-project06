"""
Pydantic schema validation tests for all schema modules.

Tests cover:
- FirewallRule schemas (create, update, import, response, workload, paginated)
- Approval schemas (create, approve, reject, comment, response, workflow, bulk)
- User schemas (login, refresh, logout, token, user info, role, role assignment)
- Validation edge cases (required fields, defaults, enums, optional fields, types)
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pydantic import ValidationError

# Import all schema classes
from app.schemas.firewall_rule import (
    FirewallRuleCreate, FirewallRuleUpdate, FirewallRuleImport,
    FirewallRuleResponse, WorkloadResponse, PaginatedResponse,
    FirewallRuleAction, FirewallProtocol, FirewallRuleStatus,
)
from app.schemas.approval import (
    ChangeType, ApprovalStatus, ApprovalRole,
    ApprovalStepCreate, ApprovalRequestCreate, ApprovalRequestApprove,
    ApprovalRequestReject, ApprovalRequestComment,
    ApprovalStepResponse, ApprovalRequestResponse,
    ApprovalWorkflowDefinitionCreate, ApprovalWorkflowDefinitionResponse,
    BulkApproveRequest, BulkRejectRequest, EscalationRequest,
    PendingApprovalCountResponse, BulkApproveResponse, BulkRejectResponse,
    TimeoutResultResponse,
)
from app.schemas.user import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    LogoutRequest, TokenBlacklistRequest, UserInfo, UserRole,
    RateLimitInfo, UserRoleAssignment, UserRoleAssignmentResponse,
    CreateUserRequest, UpdateUserRequest,
)


# ============================================================
# FirewallRule Schemas Tests
# ============================================================

class TestFirewallRuleAction:
    """Tests for FirewallRuleAction enum."""

    def test_allow_value(self):
        assert FirewallRuleAction.Allow == "Allow"

    def test_deny_value(self):
        assert FirewallRuleAction.Deny == "Deny"

    def test_valid_member_count(self):
        members = list(FirewallRuleAction)
        assert len(members) == 2


class TestFirewallProtocol:
    """Tests for FirewallProtocol enum."""

    def test_http_value(self):
        assert FirewallProtocol.Http == "Http"

    def test_https_value(self):
        assert FirewallProtocol.Https == "Https"

    def test_tcp_value(self):
        assert FirewallProtocol.Tcp == "Tcp"

    def test_udp_value(self):
        assert FirewallProtocol.Udp == "Udp"

    def test_icmp_value(self):
        assert FirewallProtocol.Icmp == "Icmp"

    def test_any_value(self):
        assert FirewallProtocol.Any == "Any"

    def test_valid_member_count(self):
        members = list(FirewallProtocol)
        assert len(members) == 5


class TestFirewallRuleStatus:
    """Tests for FirewallRuleStatus enum."""

    def test_active_value(self):
        assert FirewallRuleStatus.Active == "active"

    def test_pending_value(self):
        assert FirewallRuleStatus.Pending == "pending"

    def test_archived_value(self):
        assert FirewallRuleStatus.Archived == "archived"

    def test_valid_member_count(self):
        members = list(FirewallRuleStatus)
        assert len(members) == 3


class TestFirewallRuleCreate:
    """Tests for FirewallRuleCreate schema."""

    def test_minimal_valid(self):
        rule = FirewallRuleCreate(
            rule_collection_name="fw-rule",
            priority=100,
            action="Allow",
            protocol="Tcp",
            azure_resource_id="azure-res-id",
        )
        assert rule.rule_collection_name == "fw-rule"
        assert rule.priority == 100
        assert rule.action == FirewallRuleAction.Allow
        assert rule.protocol == FirewallProtocol.Tcp
        assert rule.rule_group_name is None
        assert rule.source_addresses is None
        assert rule.destination_fqdns is None
        assert rule.source_ip_groups is None
        assert rule.destination_ports is None
        assert rule.description is None
        assert rule.workload_id is None
        assert rule.azure_resource_id == "azure-res-id"

    def test_full_valid(self):
        rule = FirewallRuleCreate(
            rule_collection_name="fw-rule",
            priority=50,
            rule_group_name="rg-1",
            action="Deny",
            protocol="Http",
            source_addresses=["10.0.0.1"],
            destination_fqdns=["example.com"],
            source_ip_groups=["ip-group-1"],
            destination_ports=[80, 443],
            description="Test rule",
            workload_id=uuid4(),
            azure_resource_id="azure-res-id",
        )
        assert rule.rule_collection_name == "fw-rule"
        assert rule.priority == 50
        assert rule.rule_group_name == "rg-1"
        assert rule.action == FirewallRuleAction.Deny
        assert rule.protocol == FirewallProtocol.Http
        assert rule.source_addresses == ["10.0.0.1"]
        assert rule.destination_fqdns == ["example.com"]
        assert rule.source_ip_groups == ["ip-group-1"]
        assert rule.destination_ports == [80, 443]
        assert rule.description == "Test rule"
        assert rule.azure_resource_id == "azure-res-id"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            FirewallRuleCreate()

        with pytest.raises(ValidationError):
            FirewallRuleCreate(rule_collection_name="fw-rule")

        with pytest.raises(ValidationError):
            FirewallRuleCreate(rule_collection_name="fw-rule", priority=100)

        with pytest.raises(ValidationError):
            FirewallRuleCreate(rule_collection_name="fw-rule", priority=100, action="Allow")

        with pytest.raises(ValidationError):
            FirewallRuleCreate(rule_collection_name="fw-rule", priority=100, action="Allow", protocol="Tcp")

        with pytest.raises(ValidationError):
            FirewallRuleCreate(rule_collection_name="fw-rule", priority=100, action="Allow", protocol="Tcp", azure_resource_id="az")

    def test_priority_range(self):
        r1 = FirewallRuleCreate(rule_collection_name="fw", priority=1, action="Allow", protocol="Tcp", azure_resource_id="az")
        assert r1.priority == 1
        r65000 = FirewallRuleCreate(rule_collection_name="fw", priority=65000, action="Allow", protocol="Tcp", azure_resource_id="az")
        assert r65000.priority == 65000

    def test_priority_too_low(self):
        with pytest.raises(ValidationError):
            FirewallRuleCreate(rule_collection_name="fw", priority=0, action="Allow", protocol="Tcp", azure_resource_id="az")

    def test_priority_too_high(self):
        with pytest.raises(ValidationError):
            FirewallRuleCreate(rule_collection_name="fw", priority=65001, action="Allow", protocol="Tcp", azure_resource_id="az")

    def test_rule_collection_name_min_length(self):
        with pytest.raises(ValidationError):
            FirewallRuleCreate(rule_collection_name="", priority=100, action="Allow", protocol="Tcp", azure_resource_id="az")

    def test_invalid_action(self):
        with pytest.raises(ValidationError):
            FirewallRuleCreate(rule_collection_name="fw", priority=100, action="Invalid", protocol="Tcp", azure_resource_id="az")

    def test_invalid_protocol(self):
        with pytest.raises(ValidationError):
            FirewallRuleCreate(rule_collection_name="fw", priority=100, action="Allow", protocol="Invalid", azure_resource_id="az")


class TestFirewallRuleUpdate:
    """Tests for FirewallRuleUpdate schema."""

    def test_all_optional(self):
        update = FirewallRuleUpdate()
        assert update.rule_collection_name is None
        assert update.priority is None
        assert update.rule_group_name is None
        assert update.action is None
        assert update.protocol is None
        assert update.source_addresses is None
        assert update.destination_fqdns is None
        assert update.source_ip_groups is None
        assert update.destination_ports is None
        assert update.description is None

    def test_partial_update(self):
        update = FirewallRuleUpdate(priority=200, description="updated")
        assert update.priority == 200
        assert update.description == "updated"
        assert update.rule_collection_name is None

    def test_valid_action(self):
        update = FirewallRuleUpdate(action="Deny")
        assert update.action == FirewallRuleAction.Deny

    def test_valid_protocol(self):
        update = FirewallRuleUpdate(protocol="Udp")
        assert update.protocol == FirewallProtocol.Udp


class TestFirewallRuleImport:
    """Tests for FirewallRuleImport schema."""

    def test_valid_import(self):
        rule_data = {
            "rule_collection_name": "fw-rule",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "azure_resource_id": "azure-res-id",
        }
        import_schema = FirewallRuleImport(rules=[rule_data])
        assert len(import_schema.rules) == 1
        assert import_schema.rules[0].rule_collection_name == "fw-rule"

    def test_multiple_rules(self):
        rules_data = [
            {
                "rule_collection_name": "fw-rule-1",
                "priority": 100,
                "action": "Allow",
                "protocol": "Tcp",
                "azure_resource_id": "azure-res-id-1",
            },
            {
                "rule_collection_name": "fw-rule-2",
                "priority": 200,
                "action": "Deny",
                "protocol": "Udp",
                "azure_resource_id": "azure-res-id-2",
            },
        ]
        import_schema = FirewallRuleImport(rules=rules_data)
        assert len(import_schema.rules) == 2
        assert import_schema.rules[0].rule_collection_name == "fw-rule-1"
        assert import_schema.rules[1].rule_collection_name == "fw-rule-2"

    def test_empty_rules(self):
        with pytest.raises(ValidationError):
            FirewallRuleImport(rules=[])


class TestFirewallRuleResponse:
    """Tests for FirewallRuleResponse schema."""

    def test_valid_response(self):
        rule_id = uuid4()
        created_by = uuid4()
        response = FirewallRuleResponse(
            id=rule_id,
            rule_collection_name="fw-rule",
            priority=100,
            action="Allow",
            protocol="Tcp",
            azure_resource_id="azure-res-id",
            status="active",
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
        )
        assert str(response.id) == str(rule_id)
        assert response.rule_collection_name == "fw-rule"
        assert response.action == FirewallRuleAction.Allow
        assert response.protocol == FirewallProtocol.Tcp
        assert response.status == FirewallRuleStatus.Active
        assert response.created_by == created_by
        assert response.updated_at is None

    def test_optional_fields_none(self):
        rule_id = uuid4()
        created_by = uuid4()
        response = FirewallRuleResponse(
            id=rule_id,
            rule_collection_name="fw-rule",
            priority=100,
            action="Allow",
            protocol="Tcp",
            azure_resource_id="azure-res-id",
            status="pending",
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
            rule_group_name=None,
            source_addresses=None,
            destination_fqdns=None,
            source_ip_groups=None,
            destination_ports=None,
            description=None,
            workload_id=None,
        )
        assert response.rule_group_name is None
        assert response.source_addresses is None
        assert response.destination_fqdns is None


class TestWorkloadResponse:
    """Tests for WorkloadResponse schema."""

    def test_valid_workload(self):
        workload = WorkloadResponse(
            id=uuid4(),
            name="TestWorkload",
            created_at=datetime.now(timezone.utc),
        )
        assert workload.name == "TestWorkload"
        assert workload.description is None
        assert workload.owner_id is None
        assert workload.resource_groups is None
        assert workload.subscriptions is None
        assert workload.updated_at is None

    def test_full_workload(self):
        workload = WorkloadResponse(
            id=uuid4(),
            name="TestWorkload",
            description="Test description",
            owner_id=uuid4(),
            resource_groups=["rg1", "rg2"],
            subscriptions=["sub-1"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert workload.description == "Test description"
        assert workload.owner_id is not None
        assert workload.resource_groups == ["rg1", "rg2"]
        assert workload.subscriptions == ["sub-1"]


class TestPaginatedResponse:
    """Tests for PaginatedResponse schema."""

    def test_valid_pagination(self):
        pagination = PaginatedResponse(
            items=[{"id": "1"}],
            total=1,
            page=1,
            page_size=10,
            total_pages=1,
        )
        assert pagination.total == 1
        assert pagination.page == 1
        assert pagination.page_size == 10
        assert pagination.total_pages == 1

    def test_empty_pagination(self):
        pagination = PaginatedResponse(
            items=[],
            total=0,
            page=1,
            page_size=10,
            total_pages=0,
        )
        assert pagination.items == []
        assert pagination.total == 0


# ============================================================
# Approval Schemas Tests
# ============================================================

class TestChangeType:
    """Tests for ChangeType enum."""

    def test_create_value(self):
        assert ChangeType.Create == "create"

    def test_update_value(self):
        assert ChangeType.Update == "update"

    def test_delete_value(self):
        assert ChangeType.Delete == "delete"

    def test_valid_member_count(self):
        members = list(ChangeType)
        assert len(members) == 3


class TestApprovalStatus:
    """Tests for ApprovalStatus enum."""

    def test_pending_value(self):
        assert ApprovalStatus.Pending == "pending"

    def test_approved_value(self):
        assert ApprovalStatus.Approved == "approved"

    def test_rejected_value(self):
        assert ApprovalStatus.Rejected == "rejected"

    def test_revoked_value(self):
        assert ApprovalStatus.Revoked == "revoked"

    def test_expired_value(self):
        assert ApprovalStatus.Expired == "expired"

    def test_valid_member_count(self):
        members = list(ApprovalStatus)
        assert len(members) == 5


class TestApprovalRole:
    """Tests for ApprovalRole enum."""

    def test_workload_stakeholder_value(self):
        assert ApprovalRole.WorkloadStakeholder == "workload_stakeholder"

    def test_security_stakeholder_value(self):
        assert ApprovalRole.SecurityStakeholder == "security_stakeholder"

    def test_valid_member_count(self):
        members = list(ApprovalRole)
        assert len(members) == 2


class TestApprovalStepCreate:
    """Tests for ApprovalStepCreate schema."""

    def test_minimal_valid(self):
        step = ApprovalStepCreate(approver_role="workload_stakeholder")
        assert step.approver_role == ApprovalRole.WorkloadStakeholder
        assert step.approver_id is None

    def test_full_valid(self):
        approver_id = uuid4()
        step = ApprovalStepCreate(approver_id=approver_id, approver_role="security_stakeholder")
        assert str(step.approver_id) == str(approver_id)
        assert step.approver_role == ApprovalRole.SecurityStakeholder

    def test_missing_approver_role(self):
        with pytest.raises(ValidationError):
            ApprovalStepCreate()


class TestApprovalRequestCreate:
    """Tests for ApprovalRequestCreate schema."""

    def test_minimal_valid(self):
        rule_ids = [uuid4() for _ in range(1)]
        create = ApprovalRequestCreate(rule_ids=rule_ids, change_type="create")
        assert len(create.rule_ids) == 1
        assert str(create.rule_ids[0]) == str(rule_ids[0])
        assert create.change_type == ChangeType.Create
        assert create.description is None
        assert create.workload_id is None
        assert create.required_approvals == 2
        assert create.approval_flow == "multi_level"

    def test_full_valid(self):
        rule_ids = [uuid4() for _ in range(3)]
        workload_id = uuid4()
        create = ApprovalRequestCreate(
            rule_ids=rule_ids,
            change_type="update",
            description="Test change",
            workload_id=workload_id,
            required_approvals=3,
            approval_flow="single_level",
        )
        assert len(create.rule_ids) == 3
        assert create.change_type == ChangeType.Update
        assert create.description == "Test change"
        assert str(create.workload_id) == str(workload_id)
        assert create.required_approvals == 3
        assert create.approval_flow == "single_level"

    def test_minimum_rule_ids(self):
        rule_ids = [uuid4()]
        create = ApprovalRequestCreate(rule_ids=rule_ids, change_type="create")
        assert len(create.rule_ids) == 1

    def test_empty_rule_ids(self):
        with pytest.raises(ValidationError):
            ApprovalRequestCreate(rule_ids=[], change_type="create")

    def test_required_approvals_min(self):
        rule_ids = [uuid4()]
        create = ApprovalRequestCreate(rule_ids=rule_ids, change_type="create", required_approvals=1)
        assert create.required_approvals == 1

    def test_required_approvals_too_low(self):
        rule_ids = [uuid4()]
        with pytest.raises(ValidationError):
            ApprovalRequestCreate(rule_ids=rule_ids, change_type="create", required_approvals=0)


class TestApprovalRequestApprove:
    """Tests for ApprovalRequestApprove schema."""

    def test_minimal_valid(self):
        approve = ApprovalRequestApprove()
        assert approve.comment is None

    def test_with_comment(self):
        approve = ApprovalRequestApprove(comment="Looks good")
        assert approve.comment == "Looks good"


class TestApprovalRequestReject:
    """Tests for ApprovalRequestReject schema."""

    def test_comment_required(self):
        with pytest.raises(ValidationError):
            ApprovalRequestReject()

        with pytest.raises(ValidationError):
            ApprovalRequestReject(comment="")

    def test_valid_reject(self):
        reject = ApprovalRequestReject(comment="Not approved")
        assert reject.comment == "Not approved"


class TestApprovalRequestComment:
    """Tests for ApprovalRequestComment schema."""

    def test_comment_required(self):
        with pytest.raises(ValidationError):
            ApprovalRequestComment()

        with pytest.raises(ValidationError):
            ApprovalRequestComment(comment="")

    def test_valid_comment(self):
        comment = ApprovalRequestComment(comment="Good to approve")
        assert comment.comment == "Good to approve"


class TestApprovalStepResponse:
    """Tests for ApprovalStepResponse schema."""

    def test_valid_response(self):
        approval_id = uuid4()
        approver_id = uuid4()
        response = ApprovalStepResponse(
            id=uuid4(),
            approval_request_id=approval_id,
            approver_id=approver_id,
            approver_role="workload_stakeholder",
            status="pending",
            comments=None,
            approved_at=None,
            created_at=datetime.now(timezone.utc),
        )
        assert str(response.approval_request_id) == str(approval_id)
        assert str(response.approver_id) == str(approver_id)
        assert response.status == ApprovalStatus.Pending
        assert response.comments is None
        assert response.approved_at is None

    def test_completed_response(self):
        created_at = datetime.now(timezone.utc)
        approved_at = datetime.now(timezone.utc)
        response = ApprovalStepResponse(
            id=uuid4(),
            approval_request_id=uuid4(),
            approver_id=uuid4(),
            approver_role="security_stakeholder",
            status="approved",
            comments="Approved",
            approved_at=approved_at,
            created_at=created_at,
        )
        assert response.status == ApprovalStatus.Approved
        assert response.comments == "Approved"
        assert response.approved_at is not None


class TestApprovalRequestResponse:
    """Tests for ApprovalRequestResponse schema."""

    def test_valid_response(self):
        response = ApprovalRequestResponse(
            id=uuid4(),
            rule_ids=[uuid4()],
            change_type="create",
            status="pending",
            required_approvals=2,
            current_approval_stage=1,
            approval_flow="multi_level",
            created_at=datetime.now(timezone.utc),
        )
        assert len(response.rule_ids) == 1
        assert response.change_type == ChangeType.Create
        assert response.status == ApprovalStatus.Pending
        assert response.current_user_id is None
        assert response.workload_id is None
        assert response.description is None
        assert response.completed_at is None
        assert response.approval_steps is None

    def test_with_optional_fields(self):
        workload_id = uuid4()
        created_at = datetime.now(timezone.utc)
        completed_at = datetime.now(timezone.utc)
        response = ApprovalRequestResponse(
            id=uuid4(),
            rule_ids=[uuid4()],
            change_type="update",
            description="Test change",
            current_user_id=uuid4(),
            status="approved",
            workload_id=workload_id,
            required_approvals=2,
            current_approval_stage=1,
            approval_flow="single_level",
            created_at=created_at,
            completed_at=completed_at,
            approval_steps=[],
        )
        assert response.description == "Test change"
        assert str(response.current_user_id) == str(response.current_user_id)
        assert str(response.workload_id) == str(workload_id)
        assert response.status == ApprovalStatus.Approved
        assert response.completed_at is not None


class TestApprovalWorkflowDefinition:
    """Tests for ApprovalWorkflowDefinitionCreate/Response schemas."""

    def test_create_minimal(self):
        workflow = ApprovalWorkflowDefinitionCreate(
            name="Test Workflow",
            required_roles=["workload_stakeholder"],
        )
        assert workflow.name == "Test Workflow"
        assert workflow.description is None
        assert workflow.trigger_conditions is None
        assert workflow.timeout_hours == 48
        assert workflow.required_roles == ["workload_stakeholder"]

    def test_create_full(self):
        workflow = ApprovalWorkflowDefinitionCreate(
            name="Test Workflow",
            description="Description",
            trigger_conditions={"action": "create"},
            required_roles=["workload_stakeholder", "security_stakeholder"],
            timeout_hours=24,
        )
        assert workflow.name == "Test Workflow"
        assert workflow.description == "Description"
        assert workflow.trigger_conditions == {"action": "create"}
        assert workflow.required_roles == ["workload_stakeholder", "security_stakeholder"]
        assert workflow.timeout_hours == 24

    def test_create_missing_name(self):
        with pytest.raises(ValidationError):
            ApprovalWorkflowDefinitionCreate()

    def test_create_empty_roles(self):
        with pytest.raises(ValidationError):
            ApprovalWorkflowDefinitionCreate(name="Test", required_roles=[])

    def test_response_valid(self):
        response = ApprovalWorkflowDefinitionResponse(
            id=uuid4(),
            name="Test Workflow",
            description="Description",
            trigger_conditions={"action": "create"},
            required_roles=["workload_stakeholder"],
            timeout_hours=24,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        assert response.name == "Test Workflow"
        assert response.is_active is True
        assert response.description == "Description"
        assert response.timeout_hours == 24


class TestBulkApprovalSchemas:
    """Tests for bulk approval/rejection schemas."""

    def test_bulk_approve_minimal(self):
        request = BulkApproveRequest(approval_ids=[uuid4()])
        assert len(request.approval_ids) == 1
        assert request.comment is None
        assert request.required_approvals == 2

    def test_bulk_approve_with_comment(self):
        request = BulkApproveRequest(approval_ids=[uuid4()], comment="Looks good")
        assert request.comment == "Looks good"

    def test_bulk_reject_with_comment(self):
        request = BulkRejectRequest(approval_ids=[uuid4()], comment="Not approved")
        assert len(request.approval_ids) == 1
        assert request.comment == "Not approved"

    def test_bulk_reject_missing_comment(self):
        with pytest.raises(ValidationError):
            BulkRejectRequest(approval_ids=[uuid4()])

    def test_bulk_reject_empty_comment(self):
        with pytest.raises(ValidationError):
            BulkRejectRequest(approval_ids=[uuid4()], comment="")

    def test_escalation_request(self):
        escalation = EscalationRequest(target_role="workload_stakeholder")
        assert escalation.target_role == ApprovalRole.WorkloadStakeholder
        assert escalation.reason is None

    def test_escalation_request_with_reason(self):
        escalation = EscalationRequest(target_role="security_stakeholder", reason="Urgent")
        assert escalation.target_role == ApprovalRole.SecurityStakeholder
        assert escalation.reason == "Urgent"


class TestResponseSchemas:
    """Tests for response-only schemas."""

    def test_pending_approval_count_response(self):
        response = PendingApprovalCountResponse(count=5)
        assert response.count == 5

    def test_bulk_approve_response(self):
        response = BulkApproveResponse(
            approved_ids=["id1", "id2"],
            rejected_ids=["id3"],
            errors=[],
            total_processed=3,
            total_approved=2,
            total_rejected=1,
        )
        assert response.approved_ids == ["id1", "id2"]
        assert response.rejected_ids == ["id3"]
        assert response.total_processed == 3
        assert response.total_approved == 2
        assert response.total_rejected == 1

    def test_bulk_reject_response(self):
        response = BulkRejectResponse(
            rejected_ids=["id1", "id2"],
            errors=[],
            total_processed=2,
            total_rejected=2,
        )
        assert response.rejected_ids == ["id1", "id2"]
        assert response.total_processed == 2

    def test_timeout_result_response(self):
        response = TimeoutResultResponse(
            expired_count=2,
            escalated_count=1,
            details=[{"id": "id1", "status": "expired"}],
        )
        assert response.expired_count == 2
        assert response.escalated_count == 1


# ============================================================
# User Schemas Tests
# ============================================================

class TestLoginRequest:
    """Tests for LoginRequest schema."""

    def test_minimal_valid(self):
        login = LoginRequest(username="user@example.com", password="password123")
        assert login.username == "user@example.com"
        assert login.password == "password123"

    def test_missing_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="password123")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="user@example.com")

    def test_empty_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="password123")

    def test_empty_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="user@example.com", password="")


class TestLoginResponse:
    """Tests for LoginResponse schema."""

    def test_valid(self):
        response = LoginResponse(
            access_token="token",
            refresh_token="refresh",
            expires_in=3600,
        )
        assert response.access_token == "token"
        assert response.refresh_token == "refresh"
        assert response.expires_in == 3600
        assert response.token_type == "Bearer"


class TestRefreshTokenRequest:
    """Tests for RefreshTokenRequest schema."""

    def test_valid(self):
        request = RefreshTokenRequest(refresh_token="refresh-token")
        assert request.refresh_token == "refresh-token"

    def test_missing_refresh_token(self):
        with pytest.raises(ValidationError):
            RefreshTokenRequest()


class TestRefreshTokenResponse:
    """Tests for RefreshTokenResponse schema."""

    def test_valid(self):
        response = RefreshTokenResponse(
            access_token="new-access",
            refresh_token="new-refresh",
            expires_in=3600,
        )
        assert response.access_token == "new-access"
        assert response.token_type == "Bearer"


class TestLogoutRequest:
    """Tests for LogoutRequest schema."""

    def test_minimal_valid(self):
        logout = LogoutRequest()
        assert logout.refresh_token is None
        assert logout.access_token is None

    def test_with_refresh_token(self):
        logout = LogoutRequest(refresh_token="refresh-token")
        assert logout.refresh_token == "refresh-token"


class TestTokenBlacklistRequest:
    """Tests for TokenBlacklistRequest schema."""

    def test_valid(self):
        request = TokenBlacklistRequest(token="token", token_type="access")
        assert request.token == "token"
        assert request.token_type == "access"

    def test_with_refresh_type(self):
        request = TokenBlacklistRequest(token="token", token_type="refresh")
        assert request.token_type == "refresh"


class TestUserInfo:
    """Tests for UserInfo schema."""

    def test_minimal_valid(self):
        object_id = uuid4()
        user = UserInfo(
            object_id=object_id,
            email="user@example.com",
            display_name="Test User",
        )
        assert str(user.object_id) == str(object_id)
        assert user.email == "user@example.com"
        assert user.display_name == "Test User"
        assert user.given_name is None
        assert user.surname is None
        assert user.roles == []
        assert user.is_active is True

    def test_full_valid(self):
        object_id = uuid4()
        given_name = "John"
        surname = "Doe"
        user = UserInfo(
            object_id=object_id,
            email="user@example.com",
            display_name="Test User",
            given_name=given_name,
            surname=surname,
            roles=["admin", "developer"],
            is_active=False,
        )
        assert str(user.object_id) == str(object_id)
        assert user.given_name == given_name
        assert user.surname == surname
        assert user.roles == ["admin", "developer"]
        assert user.is_active is False


class TestUserRole:
    """Tests for UserRole enum."""

    def test_owner(self):
        assert UserRole.Owner == "owner"

    def test_admin(self):
        assert UserRole.Admin == "admin"

    def test_developer(self):
        assert UserRole.Developer == "developer"

    def test_security_reader(self):
        assert UserRole.SecurityReader == "security_reader"

    def test_network_admin(self):
        assert UserRole.NetworkAdmin == "network_admin"

    def test_viewer(self):
        assert UserRole.Viewer == "viewer"


class TestRateLimitInfo:
    """Tests for RateLimitInfo schema."""

    def test_valid(self):
        info = RateLimitInfo(limit=100, remaining=99, reset_in=60)
        assert info.limit == 100
        assert info.remaining == 99
        assert info.reset_in == 60


class TestUserRoleAssignment:
    """Tests for UserRoleAssignment schema."""

    def test_minimal_valid(self):
        assignment = UserRoleAssignment(role="admin")
        assert assignment.role == UserRole.Admin
        assert assignment.workload_id is None
        assert assignment.expires_at is None

    def test_full_valid(self):
        workload_id = uuid4()
        expires_at = datetime.now(timezone.utc)
        assignment = UserRoleAssignment(
            role="developer",
            workload_id=workload_id,
            expires_at=expires_at,
        )
        assert assignment.role == UserRole.Developer
        assert str(assignment.workload_id) == str(workload_id)
        assert assignment.expires_at == expires_at


class TestUserRoleAssignmentResponse:
    """Tests for UserRoleAssignmentResponse schema."""

    def test_valid_response(self):
        response = UserRoleAssignmentResponse(
            id=uuid4(),
            user_id=uuid4(),
            role="admin",
            workload_id=uuid4(),
            granted_by=uuid4(),
            granted_at=datetime.now(timezone.utc),
        )
        assert response.role == "admin"
        assert str(response.id) == str(response.id)


class TestCreateUserRequest:
    """Tests for CreateUserRequest schema."""

    def test_minimal_valid(self):
        object_id = uuid4()
        request = CreateUserRequest(
            object_id=object_id,
            email="user@example.com",
            display_name="Test User",
        )
        assert str(request.object_id) == str(object_id)
        assert request.email == "user@example.com"
        assert request.display_name == "Test User"
        assert request.given_name is None
        assert request.surname is None

    def test_full_valid(self):
        object_id = uuid4()
        request = CreateUserRequest(
            object_id=object_id,
            email="user@example.com",
            display_name="Test User",
            given_name="John",
            surname="Doe",
        )
        assert request.given_name == "John"
        assert request.surname == "Doe"

    def test_missing_object_id(self):
        with pytest.raises(ValidationError):
            CreateUserRequest(email="user@example.com", display_name="Test User")


class TestUpdateUserRequest:
    """Tests for UpdateUserRequest schema."""

    def test_all_optional(self):
        update = UpdateUserRequest()
        assert update.display_name is None
        assert update.given_name is None
        assert update.surname is None
        assert update.is_active is None

    def test_partial_update(self):
        update = UpdateUserRequest(display_name="New Name")
        assert update.display_name == "New Name"
        assert update.given_name is None

    def test_update_active(self):
        update = UpdateUserRequest(is_active=False)
        assert update.is_active is False