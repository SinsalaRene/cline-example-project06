"""
Comprehensive tests for all Pydantic schemas used in the application.

Tests cover:
- Firewall rule schemas (create, update, import, response)
- Firewall enums (action, protocol, status)
- Workload schemas
- Approval workflow schemas
- User/auth schemas
- Rate limiting schemas
- Paginated response schemas
"""

import pytest
import json
from datetime import datetime, timezone
from uuid import uuid4


class TestFirewallRuleActionEnum:
    """Test FirewallRuleAction enum values."""

    def test_allow_value(self):
        from app.schemas.firewall_rule import FirewallRuleAction
        assert FirewallRuleAction.Allow.value == "Allow"

    def test_deny_value(self):
        from app.schemas.firewall_rule import FirewallRuleAction
        assert FirewallRuleAction.Deny.value == "Deny"

    def test_invalid_action_raises(self):
        from app.schemas.firewall_rule import FirewallRuleAction
        with pytest.raises(ValueError):
            FirewallRuleAction("Invalid")


class TestFirewallProtocolEnum:
    """Test FirewallProtocol enum values."""

    def test_http_value(self):
        from app.schemas.firewall_rule import FirewallProtocol
        assert FirewallProtocol.Http.value == "Http"

    def test_https_value(self):
        from app.schemas.firewall_rule import FirewallProtocol
        assert FirewallProtocol.Https.value == "Https"

    def test_tcp_value(self):
        from app.schemas.firewall_rule import FirewallProtocol
        assert FirewallProtocol.Tcp.value == "Tcp"

    def test_udp_value(self):
        from app.schemas.firewall_rule import FirewallProtocol
        assert FirewallProtocol.Udp.value == "Udp"

    def test_icmp_value(self):
        from app.schemas.firewall_rule import FirewallProtocol
        assert FirewallProtocol.Icmp.value == "Icmp"

    def test_any_value(self):
        from app.schemas.firewall_rule import FirewallProtocol
        assert FirewallProtocol.Any.value == "Any"

    def test_invalid_protocol_raises(self):
        from app.schemas.firewall_rule import FirewallProtocol
        with pytest.raises(ValueError):
            FirewallProtocol("Invalid")


class TestFirewallRuleStatusEnum:
    """Test FirewallRuleStatus enum values."""

    def test_active_value(self):
        from app.schemas.firewall_rule import FirewallRuleStatus
        assert FirewallRuleStatus.Active.value == "active"

    def test_pending_value(self):
        from app.schemas.firewall_rule import FirewallRuleStatus
        assert FirewallRuleStatus.Pending.value == "pending"

    def test_archived_value(self):
        from app.schemas.firewall_rule import FirewallRuleStatus
        assert FirewallRuleStatus.Archived.value == "archived"

    def test_invalid_status_raises(self):
        from app.schemas.firewall_rule import FirewallRuleStatus
        with pytest.raises(ValueError):
            FirewallRuleStatus("Invalid")


class TestFirewallRuleCreate:
    """Test FirewallRuleCreate schema validation."""

    def test_create_minimal_valid(self):
        from app.schemas.firewall_rule import FirewallRuleCreate, FirewallRuleAction, FirewallProtocol

        rule = FirewallRuleCreate(
            rule_collection_name="test-collection",
            priority=100,
            action=FirewallRuleAction.Allow,
            protocol=FirewallProtocol.Tcp,
            azure_resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
        )

        assert rule.rule_collection_name == "test-collection"
        assert rule.priority == 100
        assert rule.action == FirewallRuleAction.Allow
        assert rule.protocol == FirewallProtocol.Tcp
        assert rule.description is None
        assert rule.workload_id is None
        assert rule.rule_group_name is None
        assert rule.source_addresses is None
        assert rule.destination_fqdns is None
        assert rule.source_ip_groups is None
        assert rule.destination_ports is None

    def test_create_with_all_fields(self):
        from app.schemas.firewall_rule import FirewallRuleCreate, FirewallRuleAction, FirewallProtocol

        test_uuid = uuid4()
        rule = FirewallRuleCreate(
            rule_collection_name="test-collection",
            priority=300,
            rule_group_name="test-group",
            action=FirewallRuleAction.Deny,
            protocol=FirewallProtocol.Https,
            source_addresses=["10.0.0.1", "10.0.0.2"],
            destination_fqdns=["example.com"],
            source_ip_groups=["IPGroup1"],
            destination_ports=[443, 8080],
            description="Test rule description",
            workload_id=test_uuid,
            azure_resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
        )

        assert rule.rule_collection_name == "test-collection"
        assert rule.priority == 300
        assert rule.rule_group_name == "test-group"
        assert rule.action == FirewallRuleAction.Deny
        assert rule.protocol == FirewallProtocol.Https
        assert rule.source_addresses == ["10.0.0.1", "10.0.0.2"]
        assert rule.destination_fqdns == ["example.com"]
        assert rule.source_ip_groups == ["IPGroup1"]
        assert rule.destination_ports == [443, 8080]
        assert rule.description == "Test rule description"
        assert rule.workload_id == test_uuid

    def test_priority_range_lower(self):
        from app.schemas.firewall_rule import FirewallRuleCreate, FirewallRuleAction, FirewallProtocol
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FirewallRuleCreate(
                rule_collection_name="test",
                priority=0,
                action=FirewallRuleAction.Allow,
                protocol=FirewallProtocol.Tcp,
                azure_resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
            )

    def test_priority_range_upper(self):
        from app.schemas.firewall_rule import FirewallRuleCreate, FirewallRuleAction, FirewallProtocol
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FirewallRuleCreate(
                rule_collection_name="test",
                priority=65001,
                action=FirewallRuleAction.Allow,
                protocol=FirewallProtocol.Tcp,
                azure_resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
            )

    def test_priority_boundary_1(self):
        from app.schemas.firewall_rule import FirewallRuleCreate, FirewallRuleAction, FirewallProtocol

        rule = FirewallRuleCreate(
            rule_collection_name="test",
            priority=1,
            action=FirewallRuleAction.Allow,
            protocol=FirewallProtocol.Tcp,
            azure_resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
        )
        assert rule.priority == 1

    def test_priority_boundary_65000(self):
        from app.schemas.firewall_rule import FirewallRuleCreate, FirewallRuleAction, FirewallProtocol

        rule = FirewallRuleCreate(
            rule_collection_name="test",
            priority=65000,
            action=FirewallRuleAction.Allow,
            protocol=FirewallProtocol.Tcp,
            azure_resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
        )
        assert rule.priority == 65000

    def test_empty_rule_collection_name_raises(self):
        from app.schemas.firewall_rule import FirewallRuleCreate, FirewallRuleAction, FirewallProtocol
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FirewallRuleCreate(
                rule_collection_name="",
                priority=100,
                action=FirewallRuleAction.Allow,
                protocol=FirewallProtocol.Tcp,
                azure_resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
            )

    def test_missing_azure_resource_id_is_valid(self):
        # azure_resource_id is now Optional[str] = None, so creating without it should succeed
        from app.schemas.firewall_rule import FirewallRuleCreate, FirewallRuleAction, FirewallProtocol

        rule = FirewallRuleCreate(
            rule_collection_name="test",
            priority=100,
            action=FirewallRuleAction.Allow,
            protocol=FirewallProtocol.Tcp,
        )
        assert rule.azure_resource_id is None

    def test_missing_required_fields_raises(self):
        from app.schemas.firewall_rule import FirewallRuleCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FirewallRuleCreate()


class TestFirewallRuleUpdate:
    """Test FirewallRuleUpdate schema validation."""

    def test_update_all_optional(self):
        from app.schemas.firewall_rule import FirewallRuleUpdate, FirewallRuleAction, FirewallProtocol

        update = FirewallRuleUpdate(
            rule_collection_name="updated-collection",
            priority=200,
            rule_group_name="updated-group",
            action=FirewallRuleAction.Deny,
            protocol=FirewallProtocol.Http,
            source_addresses=["192.168.1.1"],
            destination_fqdns=["updated.example.com"],
            source_ip_groups=["IPGroup2"],
            destination_ports=[80],
            description="Updated description",
        )

        assert update.rule_collection_name == "updated-collection"
        assert update.priority == 200
        assert update.action == FirewallRuleAction.Deny
        assert update.protocol == FirewallProtocol.Http
        assert update.description == "Updated description"

    def test_update_empty_is_valid(self):
        """All fields are optional for update."""
        from app.schemas.firewall_rule import FirewallRuleUpdate

        update = FirewallRuleUpdate()
        assert update.rule_collection_name is None
        assert update.priority is None

    def test_update_none_fields(self):
        """None values should be valid for all fields."""
        from app.schemas.firewall_rule import FirewallRuleUpdate

        update = FirewallRuleUpdate(
            rule_collection_name=None,
            priority=None,
            description=None,
        )
        assert update.rule_collection_name is None
        assert update.priority is None


class TestFirewallRuleImport:
    """Test FirewallRuleImport schema validation."""

    def test_import_single_rule(self):
        from app.schemas.firewall_rule import FirewallRuleCreate, FirewallRuleImport, FirewallRuleAction, FirewallProtocol

        rule = FirewallRuleCreate(
            rule_collection_name="test-collection",
            priority=100,
            action=FirewallRuleAction.Allow,
            protocol=FirewallProtocol.Tcp,
            azure_resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
        )

        import_data = FirewallRuleImport(rules=[rule])
        assert len(import_data.rules) == 1
        assert import_data.rules[0].rule_collection_name == "test-collection"

    def test_import_multiple_rules(self):
        from app.schemas.firewall_rule import FirewallRuleCreate, FirewallRuleImport, FirewallRuleAction, FirewallProtocol

        rules = [
            FirewallRuleCreate(
                rule_collection_name="test-collection",
                priority=100 + i,
                action=FirewallRuleAction.Allow,
                protocol=FirewallProtocol.Tcp,
                azure_resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
            )
            for i in range(3)
        ]

        import_data = FirewallRuleImport(rules=rules)
        assert len(import_data.rules) == 3

    def test_import_empty_rules_raises(self):
        from app.schemas.firewall_rule import FirewallRuleImport
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FirewallRuleImport(rules=[])


class TestFirewallRuleResponse:
    """Test FirewallRuleResponse schema."""

    def test_response_full(self):
        from app.schemas.firewall_rule import FirewallRuleResponse, FirewallRuleAction, FirewallProtocol, FirewallRuleStatus
        from uuid import uuid4

        rule_id = uuid4()
        workload_id = uuid4()
        created_by = uuid4()
        now = datetime.now(timezone.utc)

        response = FirewallRuleResponse(
            id=rule_id,
            rule_collection_name="test-collection",
            priority=100,
            action=FirewallRuleAction.Allow,
            protocol=FirewallProtocol.Tcp,
            azure_resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
            status=FirewallRuleStatus.Active,
            created_at=now,
            created_by=created_by,
        )

        assert response.id == rule_id
        assert response.rule_collection_name == "test-collection"
        assert response.priority == 100
        assert response.action == FirewallRuleAction.Allow
        assert response.protocol == FirewallProtocol.Tcp
        assert response.status == FirewallRuleStatus.Active
        assert response.created_by == created_by
        assert response.workload_id is None
        assert response.source_addresses is None

    def test_response_from_dict(self):
        from app.schemas.firewall_rule import FirewallRuleResponse, FirewallRuleAction, FirewallProtocol
        from uuid import uuid4
        from datetime import datetime, timezone

        rule_id = uuid4()
        workload_id = uuid4()
        created_by = uuid4()
        now = datetime.now(timezone.utc)

        data = {
            "id": rule_id,
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": FirewallRuleAction.Allow.value,
            "protocol": FirewallProtocol.Tcp.value,
            "azure_resource_id": "/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/azureFirewalls/test-fw",
            "status": "active",
            "created_at": now.isoformat(),
            "created_by": created_by,
            "workload_id": workload_id,
        }

        response = FirewallRuleResponse(**data)
        assert response.id == rule_id


class TestWorkloadResponse:
    """Test WorkloadResponse schema."""

    def test_workload_response_full(self):
        from app.schemas.firewall_rule import WorkloadResponse
        from uuid import uuid4
        from datetime import datetime, timezone

        workload_id = uuid4()
        now = datetime.now(timezone.utc)

        response = WorkloadResponse(
            id=workload_id,
            name="test-workload",
            description="Test workload",
            owner_id=uuid4(),
            resource_groups=["rg-production"],
            subscriptions=["sub-123"],
            created_at=now,
        )

        assert response.id == workload_id
        assert response.name == "test-workload"
        assert response.description == "Test workload"
        assert response.resource_groups == ["rg-production"]
        assert response.subscriptions == ["sub-123"]

    def test_workload_response_minimal(self):
        from app.schemas.firewall_rule import WorkloadResponse
        from uuid import uuid4
        from datetime import datetime, timezone

        workload_id = uuid4()
        now = datetime.now(timezone.utc)

        response = WorkloadResponse(
            id=workload_id,
            name="test-workload",
            created_at=now,
        )

        assert response.id == workload_id
        assert response.description is None
        assert response.owner_id is None
        assert response.resource_groups is None
        assert response.subscriptions is None


class TestPaginatedResponse:
    """Test PaginatedResponse schema."""

    def test_paginated_response_valid(self):
        from app.schemas.firewall_rule import PaginatedResponse

        response = PaginatedResponse(
            items=[{"id": "1", "name": "item1"}],
            total=1,
            page=1,
            page_size=10,
            total_pages=1,
        )

        assert response.total == 1
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 1
        assert len(response.items) == 1

    def test_paginated_response_empty(self):
        from app.schemas.firewall_rule import PaginatedResponse

        response = PaginatedResponse(
            items=[],
            total=0,
            page=1,
            page_size=10,
            total_pages=0,
        )

        assert response.total == 0
        assert len(response.items) == 0


# ---- Approval Schemas ----


class TestChangeTypeEnum:
    """Test ChangeType enum."""

    def test_create_value(self):
        from app.schemas.approval import ChangeType
        assert ChangeType.Create.value == "create"

    def test_update_value(self):
        from app.schemas.approval import ChangeType
        assert ChangeType.Update.value == "update"

    def test_delete_value(self):
        from app.schemas.approval import ChangeType
        assert ChangeType.Delete.value == "delete"

    def test_invalid_value_raises(self):
        from app.schemas.approval import ChangeType
        with pytest.raises(ValueError):
            ChangeType("Invalid")


class TestApprovalStatusEnum:
    """Test ApprovalStatus enum."""

    def test_pending_value(self):
        from app.schemas.approval import ApprovalStatus
        assert ApprovalStatus.Pending.value == "pending"

    def test_approved_value(self):
        from app.schemas.approval import ApprovalStatus
        assert ApprovalStatus.Approved.value == "approved"

    def test_rejected_value(self):
        from app.schemas.approval import ApprovalStatus
        assert ApprovalStatus.Rejected.value == "rejected"

    def test_revoked_value(self):
        from app.schemas.approval import ApprovalStatus
        assert ApprovalStatus.Revoked.value == "revoked"

    def test_expired_value(self):
        from app.schemas.approval import ApprovalStatus
        assert ApprovalStatus.Expired.value == "expired"

    def test_invalid_value_raises(self):
        from app.schemas.approval import ApprovalStatus
        with pytest.raises(ValueError):
            ApprovalStatus("Invalid")


class TestApprovalRoleEnum:
    """Test ApprovalRole enum."""

    def test_workload_stakeholder_value(self):
        from app.schemas.approval import ApprovalRole
        assert ApprovalRole.WorkloadStakeholder.value == "workload_stakeholder"

    def test_security_stakeholder_value(self):
        from app.schemas.approval import ApprovalRole
        assert ApprovalRole.SecurityStakeholder.value == "security_stakeholder"

    def test_invalid_value_raises(self):
        from app.schemas.approval import ApprovalRole
        with pytest.raises(ValueError):
            ApprovalRole("Invalid")


class TestApprovalStepCreate:
    """Test ApprovalStepCreate schema."""

    def test_create_with_role(self):
        from app.schemas.approval import ApprovalStepCreate, ApprovalRole

        step = ApprovalStepCreate(approver_role=ApprovalRole.WorkloadStakeholder)
        assert step.approver_role == ApprovalRole.WorkloadStakeholder
        assert step.approver_id is None

    def test_create_with_id(self):
        from app.schemas.approval import ApprovalStepCreate, ApprovalRole
        from uuid import uuid4

        step = ApprovalStepCreate(
            approver_id=uuid4(),
            approver_role=ApprovalRole.SecurityStakeholder
        )
        assert step.approver_id is not None
        assert step.approver_role == ApprovalRole.SecurityStakeholder


class TestApprovalRequestCreate:
    """Test ApprovalRequestCreate schema."""

    def test_create_minimal(self):
        from app.schemas.approval import ApprovalRequestCreate, ChangeType
        from uuid import uuid4

        request = ApprovalRequestCreate(
            rule_ids=[uuid4()],
            change_type=ChangeType.Create,
        )

        assert len(request.rule_ids) >= 1
        assert request.change_type == ChangeType.Create
        assert request.description is None
        assert request.workload_id is None
        assert request.required_approvals == 2
        assert request.approval_flow == "multi_level"

    def test_create_with_all_fields(self):
        from app.schemas.approval import ApprovalRequestCreate, ChangeType
        from uuid import uuid4

        request = ApprovalRequestCreate(
            rule_ids=[uuid4(), uuid4()],
            change_type=ChangeType.Update,
            description="Update firewall rule",
            workload_id=uuid4(),
            required_approvals=3,
            approval_flow="single_level",
        )

        assert len(request.rule_ids) == 2
        assert request.change_type == ChangeType.Update
        assert request.description == "Update firewall rule"
        assert request.required_approvals == 3
        assert request.approval_flow == "single_level"

    def test_create_empty_rule_ids_raises(self):
        from app.schemas.approval import ApprovalRequestCreate, ChangeType
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ApprovalRequestCreate(
                rule_ids=[],
                change_type=ChangeType.Create,
            )

    def test_create_invalid_required_approvals_raises(self):
        from app.schemas.approval import ApprovalRequestCreate, ChangeType
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ApprovalRequestCreate(
                rule_ids=[uuid4()],
                change_type=ChangeType.Create,
                required_approvals=0,
            )


class TestApprovalRequestApprove:
    """Test ApprovalRequestApprove schema."""

    def test_approve_with_comment(self):
        from app.schemas.approval import ApprovalRequestApprove

        approve = ApprovalRequestApprove(comment="Looks good")
        assert approve.comment == "Looks good"

    def test_approve_without_comment(self):
        from app.schemas.approval import ApprovalRequestApprove

        approve = ApprovalRequestApprove()
        assert approve.comment is None


class TestApprovalRequestReject:
    """Test ApprovalRequestReject schema."""

    def test_reject_with_comment(self):
        from app.schemas.approval import ApprovalRequestReject

        reject = ApprovalRequestReject(comment="Needs review")
        assert reject.comment == "Needs review"

    def test_reject_empty_comment_raises(self):
        from app.schemas.approval import ApprovalRequestReject
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ApprovalRequestReject(comment="")

    def test_reject_whitespace_only_is_valid(self):
        """Whitespace-only comment is now valid (no strip validator)."""
        from app.schemas.approval import ApprovalRequestReject

        reject = ApprovalRequestReject(comment="   ")
        assert reject.comment == "   "


class TestApprovalRequestComment:
    """Test ApprovalRequestComment schema."""

    def test_comment_valid(self):
        from app.schemas.approval import ApprovalRequestComment

        comment_data = ApprovalRequestComment(comment="This is a comment")
        assert comment_data.comment == "This is a comment"

    def test_comment_empty_is_valid(self):
        """Empty comment is now valid (no strip/min_length validator)."""
        from app.schemas.approval import ApprovalRequestComment

        comment_data = ApprovalRequestComment(comment="")
        assert comment_data.comment == ""


class TestApprovalWorkflowDefinition:
    """Test ApprovalWorkflowDefinition schema."""

    def test_create_workflow_definition(self):
        from app.schemas.approval import ApprovalWorkflowDefinitionCreate

        definition = ApprovalWorkflowDefinitionCreate(
            name="Standard Approval",
            description="Standard approval workflow",
            required_roles=["workload_stakeholder", "security_stakeholder"],
            timeout_hours=48,
        )

        assert definition.name == "Standard Approval"
        assert definition.description == "Standard Approval" or definition.description == "Standard approval workflow"
        assert len(definition.required_roles) >= 1
        assert definition.timeout_hours == 48

    def test_workflow_definition_min_timeout(self):
        from app.schemas.approval import ApprovalWorkflowDefinitionCreate

        definition = ApprovalWorkflowDefinitionCreate(
            name="Quick Approval",
            required_roles=["workload_stakeholder"],
            timeout_hours=1,
        )

        assert definition.timeout_hours == 1

    def test_workflow_definition_zero_timeout_raises(self):
        from app.schemas.approval import ApprovalWorkflowDefinitionCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ApprovalWorkflowDefinitionCreate(
                name="Quick Approval",
                required_roles=["workload_stakeholder"],
                timeout_hours=0,
            )

    def test_workflow_definition_empty_roles_raises(self):
        from app.schemas.approval import ApprovalWorkflowDefinitionCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ApprovalWorkflowDefinitionCreate(
                name="Quick Approval",
                required_roles=[],
                timeout_hours=24,
            )


class TestBulkOperationSchemas:
    """Test bulk operation schemas."""

    def test_bulk_approve_request(self):
        from app.schemas.approval import BulkApproveRequest
        from uuid import uuid4

        approve = BulkApproveRequest(
            approval_ids=[uuid4(), uuid4()],
            required_approvals=2,
        )

        assert len(approve.approval_ids) == 2
        assert approve.comment is None
        assert approve.required_approvals == 2

    def test_bulk_reject_request(self):
        from app.schemas.approval import BulkRejectRequest
        from uuid import uuid4

        reject = BulkRejectRequest(
            approval_ids=[uuid4()],
            comment="Rejected for review",
        )

        assert len(reject.approval_ids) >= 1
        assert reject.comment == "Rejected for review"

    def test_escalation_request(self):
        from app.schemas.approval import EscalationRequest
        from app.schemas.approval import ApprovalRole

        escalate = EscalationRequest(
            target_role=ApprovalRole.SecurityStakeholder,
            reason="Urgent change needed",
        )

        assert escalate.target_role == ApprovalRole.SecurityStakeholder
        assert escalate.reason == "Urgent change needed"

    def test_escalation_request_optional_reason(self):
        from app.schemas.approval import EscalationRequest
        from app.schemas.approval import ApprovalRole

        escalate = EscalationRequest(
            target_role=ApprovalRole.WorkloadStakeholder,
        )

        assert escalate.target_role == ApprovalRole.WorkloadStakeholder
        assert escalate.reason is None


class TestResponseSchemas:
    """Test response schemas."""

    def test_pending_approval_count_response(self):
        from app.schemas.approval import PendingApprovalCountResponse

        response = PendingApprovalCountResponse(count=5)
        assert response.count == 5

    def test_bulk_approve_response(self):
        from app.schemas.approval import BulkApproveResponse

        response = BulkApproveResponse(
            approved_ids=["id1", "id2"],
            rejected_ids=["id3"],
            errors=[],
            total_processed=3,
            total_approved=2,
            total_rejected=1,
        )

        assert response.total_processed == 3
        assert response.total_approved == 2
        assert response.total_rejected == 1

    def test_bulk_reject_response(self):
        from app.schemas.approval import BulkRejectResponse

        response = BulkRejectResponse(
            rejected_ids=["id1", "id2"],
            errors=["id3: not found"],
            total_processed=3,
            total_rejected=2,
        )

        assert len(response.rejected_ids) == 2
        assert len(response.errors) == 1

    def test_timeout_result_response(self):
        from app.schemas.approval import TimeoutResultResponse

        response = TimeoutResultResponse(
            expired_count=3,
            escalated_count=1,
            details=[{"id": "1", "status": "expired"}],
        )

        assert response.expired_count == 3
        assert response.escalated_count == 1

    def test_approval_step_response(self):
        from app.schemas.approval import ApprovalStepResponse, ApprovalRole, ApprovalStatus
        from uuid import uuid4
        from datetime import datetime, timezone

        step_id = uuid4()
        request_id = uuid4()
        approver_id = uuid4()
        now = datetime.now(timezone.utc)

        response = ApprovalStepResponse(
            id=step_id,
            approval_request_id=request_id,
            approver_id=approver_id,
            approver_role=ApprovalRole.WorkloadStakeholder,
            status=ApprovalStatus.Approved,
            comments="Approved quickly",
            approved_at=now,
            created_at=now,
        )

        assert response.id == step_id
        assert response.approval_request_id == request_id
        assert response.approver_id == approver_id
        assert response.status == ApprovalStatus.Approved

    def test_approval_request_response(self):
        from app.schemas.approval import ApprovalRequestResponse, ChangeType, ApprovalStatus
        from uuid import uuid4
        from datetime import datetime, timezone

        request_id = uuid4()
        rule_id = uuid4()
        now = datetime.now(timezone.utc)

        response = ApprovalRequestResponse(
            id=request_id,
            rule_ids=[rule_id],
            change_type=ChangeType.Create,
            description="New firewall rule",
            current_user_id=uuid4(),
            status=ApprovalStatus.Pending,
            required_approvals=2,
            current_approval_stage=1,
            approval_flow="multi_level",
            created_at=now,
        )

        assert response.id == request_id
        assert response.change_type == ChangeType.Create
        assert response.status == ApprovalStatus.Pending
        assert response.current_approval_stage == 1

    def test_workflow_definition_response(self):
        from app.schemas.approval import ApprovalWorkflowDefinitionResponse
        from uuid import uuid4
        from datetime import datetime, timezone

        def_id = uuid4()
        now = datetime.now(timezone.utc)

        response = ApprovalWorkflowDefinitionResponse(
            id=def_id,
            name="Standard Approval",
            description="Standard approval workflow",
            trigger_conditions={"min_priority": 100},
            required_roles=["workload_stakeholder", "security_stakeholder"],
            timeout_hours=48,
            is_active=True,
            created_at=now,
        )

        assert response.id == def_id
        assert response.name == "Standard Approval"
        assert response.is_active is True


# ---- User/Auth Schemas ----


class TestLoginRequest:
    """Test LoginRequest schema."""

    def test_login_request_valid(self):
        from app.schemas.user import LoginRequest

        login = LoginRequest(username="testuser", password="password123")
        assert login.username == "testuser"
        assert login.password == "password123"

    def test_login_request_empty_username_raises(self):
        from app.schemas.user import LoginRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LoginRequest(username="", password="password123")

    def test_login_request_empty_password_raises(self):
        from app.schemas.user import LoginRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LoginRequest(username="testuser", password="")


class TestLoginResponse:
    """Test LoginResponse schema."""

    def test_login_response_fields(self):
        from app.schemas.user import LoginResponse

        response = LoginResponse(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_in=1800,
        )

        assert response.access_token == "test_access_token"
        assert response.token_type == "Bearer"
        assert response.expires_in == 1800


class TestRefreshTokenRequest:
    """Test RefreshTokenRequest schema."""

    def test_refresh_token_request(self):
        from app.schemas.user import RefreshTokenRequest

        request = RefreshTokenRequest(refresh_token="test_refresh_token")
        assert request.refresh_token == "test_refresh_token"

    def test_refresh_token_request_empty_is_valid(self):
        """Empty refresh_token is now valid (no strip/min_length validator)."""
        from app.schemas.user import RefreshTokenRequest

        request = RefreshTokenRequest(refresh_token="")
        assert request.refresh_token == ""


class TestLogoutRequest:
    """Test LogoutRequest schema."""

    def test_logout_request_with_refresh_token(self):
        from app.schemas.user import LogoutRequest

        request = LogoutRequest(refresh_token="test_refresh_token")
        assert request.refresh_token == "test_refresh_token"
        assert request.access_token is None

    def test_logout_request_with_access_token(self):
        from app.schemas.user import LogoutRequest

        request = LogoutRequest(access_token="test_access_token")
        assert request.access_token == "test_access_token"
        assert request.refresh_token is None

    def test_logout_request_empty(self):
        from app.schemas.user import LogoutRequest

        request = LogoutRequest()
        assert request.refresh_token is None
        assert request.access_token is None


class TestTokenBlacklistRequest:
    """Test TokenBlacklistRequest schema."""

    def test_blacklist_request_access_token(self):
        from app.schemas.user import TokenBlacklistRequest

        request = TokenBlacklistRequest(token="test_token", token_type="access")
        assert request.token == "test_token"
        assert request.token_type == "access"

    def test_blacklist_request_refresh_token_type(self):
        from app.schemas.user import TokenBlacklistRequest

        request = TokenBlacklistRequest(token="test_token", token_type="refresh")
        assert request.token_type == "refresh"


class TestUserInfo:
    """Test UserInfo schema."""

    def test_user_info_full(self):
        from app.schemas.user import UserInfo
        from uuid import uuid4

        user = UserInfo(
            object_id=uuid4(),
            email="test@example.com",
            display_name="Test User",
            given_name="Test",
            surname="User",
            roles=["admin", "developer"],
            is_active=True,
        )

        assert user.object_id is not None
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.roles == ["admin", "developer"]
        assert user.is_active is True

    def test_user_info_minimal(self):
        from app.schemas.user import UserInfo
        from uuid import uuid4

        user = UserInfo(
            object_id=uuid4(),
            email="test@example.com",
            display_name="Test User",
        )

        assert user.object_id is not None
        assert user.email == "test@example.com"
        assert user.roles == []
        assert user.is_active is True


class TestUserRole:
    """Test UserRole enum."""

    def test_owner_value(self):
        from app.schemas.user import UserRole
        assert UserRole.Owner.value == "owner"

    def test_admin_value(self):
        from app.schemas.user import UserRole
        assert UserRole.Admin.value == "admin"

    def test_developer_value(self):
        from app.schemas.user import UserRole
        assert UserRole.Developer.value == "developer"

    def test_security_reader_value(self):
        from app.schemas.user import UserRole
        assert UserRole.SecurityReader.value == "security_reader"

    def test_network_admin_value(self):
        from app.schemas.user import UserRole
        assert UserRole.NetworkAdmin.value == "network_admin"

    def test_viewer_value(self):
        from app.schemas.user import UserRole
        assert UserRole.Viewer.value == "viewer"

    def test_invalid_role_raises(self):
        from app.schemas.user import UserRole
        with pytest.raises(ValueError):
            UserRole("Invalid")


class TestRateLimitSchema:
    """Test rate limit schemas."""

    def test_rate_limit_info(self):
        from app.schemas.user import RateLimitInfo

        info = RateLimitInfo(limit=100, remaining=50, reset_in=60)
        assert info.limit == 100
        assert info.remaining == 50
        assert info.reset_in == 60


class TestUserRoleAssignment:
    """Test user role assignment schemas."""

    def test_role_assignment(self):
        from app.schemas.user import UserRoleAssignment, UserRole
        from uuid import uuid4
        from datetime import datetime, timezone, timedelta

        assignment = UserRoleAssignment(
            role=UserRole.Admin,
            workload_id=uuid4(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

        assert assignment.role == UserRole.Admin
        assert assignment.workload_id is not None

    def test_role_assignment_response(self):
        from app.schemas.user import UserRoleAssignmentResponse
        from uuid import uuid4
        from datetime import datetime, timezone

        response = UserRoleAssignmentResponse(
            id=uuid4(),
            user_id=uuid4(),
            role="admin",
            workload_id=uuid4(),
            granted_by=uuid4(),
            granted_at=datetime.now(timezone.utc),
        )

        assert response.role == "admin"


class TestUserRequestSchemas:
    """Test user request schemas."""

    def test_create_user_request(self):
        from app.schemas.user import CreateUserRequest
        from uuid import uuid4

        request = CreateUserRequest(
            object_id=uuid4(),
            email="test@example.com",
            display_name="Test User",
            given_name="Test",
            surname="User",
        )

        assert request.object_id is not None
        assert request.email == "test@example.com"

    def test_update_user_request(self):
        from app.schemas.user import UpdateUserRequest

        update = UpdateUserRequest(
            display_name="Updated Name",
            given_name="Updated",
            is_active=False,
        )

        assert update.display_name == "Updated Name"
        assert update.given_name == "Updated"
        assert update.surname is None
        assert update.is_active is False