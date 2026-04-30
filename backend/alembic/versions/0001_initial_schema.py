"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01

This migration creates the initial database schema for the Azure Firewall Management application.
It defines all tables for workloads, firewall rules, approval workflows, and audit logging.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all database tables."""

    # Workloads table
    op.create_table(
        'workloads',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('owner_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # Firewall rules table
    op.create_table(
        'firewall_rules',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('rule_collection_name', sa.String(255), nullable=False),
        sa.Column('priority', sa.Integer, nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('protocol', sa.String(20), nullable=False),
        sa.Column('source_addresses', sa.Text, nullable=True),
        sa.Column('destination_fqdns', sa.Text, nullable=True),
        sa.Column('destination_ports', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='Pending'),
        sa.Column('workload_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workload_id'], ['workloads.id']),
    )

    # Approval requests table
    op.create_table(
        'approval_requests',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('rule_ids', sa.Text, nullable=False),
        sa.Column('change_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='Pending'),
        sa.Column('required_approvals', sa.Integer, nullable=False, server_default='1'),
        sa.Column('workload_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workload_id'], ['workloads.id']),
    )

    # Approval steps table
    op.create_table(
        'approval_steps',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('approval_request_id', sa.String(36), nullable=False),
        sa.Column('approver_role', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='Pending'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['approval_request_id'], ['approval_requests.id']),
    )

    # Approval workflow definitions table
    op.create_table(
        'approval_workflow_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('trigger_conditions', sa.Text, nullable=True),
        sa.Column('required_roles', sa.Text, nullable=True),
        sa.Column('timeout_hours', sa.Integer, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # Audit logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=False),
        sa.Column('old_value', sa.Text, nullable=True),
        sa.Column('new_value', sa.Text, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('object_id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('given_name', sa.String(255), nullable=True),
        sa.Column('surname', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('object_id'),
    )

    # User roles table
    op.create_table(
        'user_roles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('granted_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )

    # Create indexes
    op.create_index('idx_firewall_rules_priority', 'firewall_rules', ['priority'])
    op.create_index('idx_firewall_rules_workload', 'firewall_rules', ['workload_id'])
    op.create_index('idx_approval_requests_status', 'approval_requests', ['status'])
    op.create_index('idx_approval_steps_request', 'approval_steps', ['approval_request_id'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_user', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_users_object_id', 'users', ['object_id'])
    op.create_index('idx_user_roles_user', 'user_roles', ['user_id'])
    op.create_index('idx_user_roles_role', 'user_roles', ['role'])


def downgrade() -> None:
    """Drop all database tables."""
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('audit_logs')
    op.drop_table('approval_workflow_definitions')
    op.drop_table('approval_steps')
    op.drop_table('approval_requests')
    op.drop_table('firewall_rules')
    op.drop_table('workloads')