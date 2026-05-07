"""Add network topology models

Revision ID: 0002_add_network_models
Revises: 0001_initial
Create Date: 2026-05-07

This migration creates all network-related tables for network topology management:
- virtual_networks
- subnets
- network_security_groups
- nsg_rules
- external_network_devices
- network_connections
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_network_models"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all network-related database tables."""

    # Virtual Networks table
    op.create_table(
        "virtual_networks",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address_space", sa.String(255), nullable=False),
        sa.Column("location", sa.String(100), nullable=False),
        sa.Column("resource_group", sa.String(255), nullable=False),
        sa.Column("tags", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "resource_group", name="uq_vnet_name_resource_group"),
    )

    # Subnets table
    op.create_table(
        "subnets",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address_prefix", sa.String(64), nullable=False),
        sa.Column("vnet_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["vnet_id"], ["virtual_networks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("name", "vnet_id", name="uq_subnet_name_vnet"),
    )

    # Network Security Groups table
    op.create_table(
        "network_security_groups",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(100), nullable=False),
        sa.Column("vnet_id", sa.String(36), nullable=True),
        sa.Column("resource_group", sa.String(255), nullable=True),
        sa.Column("tags", sa.Text, nullable=True),
        sa.Column("sync_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("last_synced_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["vnet_id"], ["virtual_networks.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("name", "resource_group", name="uq_nsg_name_resource_group"),
    )

    # NSG Rules table
    op.create_table(
        "nsg_rules",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("nsg_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("protocol", sa.String(20), nullable=False),
        sa.Column("source_address_prefix", sa.Text, nullable=True),
        sa.Column("destination_address_prefix", sa.Text, nullable=True),
        sa.Column("source_port_range", sa.String(255), nullable=True),
        sa.Column("destination_port_range", sa.String(255), nullable=True),
        sa.Column("access", sa.String(10), nullable=False),
        sa.Column("source_ip_group", sa.String(255), nullable=True),
        sa.Column("destination_ip_group", sa.String(255), nullable=True),
        sa.Column("service_tag", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["nsg_id"],
            ["network_security_groups.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("name", "nsg_id", name="uq_nsg_rule_name_nsg"),
        sa.CheckConstraint(
            "(direction IN ('inbound', 'outbound'))",
            name="check_direction",
        ),
        sa.CheckConstraint(
            "(access IN ('allow', 'deny'))",
            name="check_access",
        ),
    )

    # External Network Devices table
    op.create_table(
        "external_network_devices",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("device_type", sa.String(20), nullable=False),
        sa.Column("vendor", sa.String(255), nullable=True),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("tags", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "ip_address", name="uq_device_name_ip"),
        sa.CheckConstraint(
            "(device_type IN ('router', 'switch', 'firewall', 'other'))",
            name="check_device_type",
        ),
    )

    # Network Connections table
    op.create_table(
        "network_connections",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("destination_id", sa.String(36), nullable=False),
        sa.Column("destination_type", sa.String(50), nullable=False),
        sa.Column("connection_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Indexes ---

    # Virtual Networks indexes
    op.create_index("idx_virtual_networks_location", "virtual_networks", ["location"])
    op.create_index("idx_virtual_networks_resource_group", "virtual_networks", ["resource_group"])

    # Subnets indexes
    op.create_index("idx_subnets_vnet", "subnets", ["vnet_id"])
    op.create_index("idx_subnets_prefix", "subnets", ["address_prefix"])

    # NSG indexes
    op.create_index("idx_nsgs_vnet", "network_security_groups", ["vnet_id"])
    op.create_index("idx_nsgs_resource_group", "network_security_groups", ["resource_group"])
    op.create_index("idx_nsgs_sync_status", "network_security_groups", ["sync_status"])
    op.create_index("idx_nsgs_last_synced", "network_security_groups", ["last_synced_at"])

    # NSG Rules indexes
    op.create_index("idx_nsg_rules_nsg", "nsg_rules", ["nsg_id"])
    op.create_index("idx_nsg_rules_priority", "nsg_rules", ["priority"])
    op.create_index("idx_nsg_rules_direction", "nsg_rules", ["direction"])
    op.create_index("idx_nsg_rules_access", "nsg_rules", ["access"])

    # External Network Devices indexes
    op.create_index("idx_external_devices_type", "external_network_devices", ["device_type"])
    op.create_index("idx_external_devices_vendor", "external_network_devices", ["vendor"])
    op.create_index("idx_external_devices_ip", "external_network_devices", ["ip_address"])

    # Network Connections indexes
    op.create_index("idx_connections_source", "network_connections", ["source_id", "source_type"])
    op.create_index("idx_connections_destination", "network_connections", ["destination_id", "destination_type"])


def downgrade() -> None:
    """Drop all network-related database tables."""
    op.drop_table("network_connections")
    op.drop_table("external_network_devices")
    op.drop_table("nsg_rules")
    op.drop_table("network_security_groups")
    op.drop_table("subnets")
    op.drop_table("virtual_networks")