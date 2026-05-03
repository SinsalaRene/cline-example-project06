"""
Mock Azure Client for local development.

Provides a realistic mock of the Azure SDK client that returns sample data
and simulates CRUD operations without requiring actual Azure credentials or API calls.

Activate mock mode by setting AZURE_MOCK_MODE=true in your .env file.

Usage:
    from app.integrations.mock_azure_client import MockAzureClient

    mock_client = MockAzureClient()
    policies = mock_client.list_firewall_policies("my-rg")
    rules = mock_client.get_firewall_rules_from_azure("my-rg", "my-policy")
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from copy import deepcopy

logger = logging.getLogger(__name__)


class MockAzureClient:
    """Mock Azure SDK client for local development.

    Provides realistic in-memory data that mirrors the structure of real
    Azure Firewall Policy resources. All CRUD operations modify in-memory
    state only.

    This client implements the same interface as AzureClient so that
    existing code works without modification.
    """

    def __init__(self, **kwargs):
        """Initialize the mock client with sample data.

        All parameters are ignored since this is a mock.
        """
        self._is_authenticated = True
        self._authenticated_at = datetime.now(timezone.utc)

        # In-memory store for policies
        self._policies: List[Dict[str, Any]] = [
            {
                "id": "subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Network/firewallPolicies/default-policy",
                "name": "default-policy",
                "location": "eastus",
                "tags": {},
                "sku": {"name": "Basic", "tier": "Basic"},
                "policy_id": "policy-001",
                "rule_collection_groups": [],
            },
            {
                "id": "subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Network/firewallPolicies/second-policy",
                "name": "second-policy",
                "location": "eastus",
                "tags": {"env": "test"},
                "sku": {"name": "Standard", "tield": "Standard"},
                "policy_id": "policy-002",
                "rule_collection_groups": [],
            },
        ]

        # In-memory store for rule collection groups
        self._rule_collection_groups: List[Dict[str, Any]] = [
            {
                "id": "rg-default-policy-group-001",
                "name": "default-group",
                "priority": 100,
                "firewall_policy_id": "policy-001",
                "rule_collections": [
                    {
                        "id": "rc-default-allow-100",
                        "name": "default-allow",
                        "priority": 100,
                        "action": "Allow",
                        "rules": [
                            {
                                "name": "allow-web-traffic",
                                "priority": 100,
                                "action": "Allow",
                                "protocols": [{"port": 443, "protocol": "Tcp"}],
                                "source_addresses": ["10.0.0.0/8", "192.168.0.0/16"],
                                "destination_fqdns": ["*.microsoft.com", "*.azure.com"],
                                "destination_ports": ["443"],
                            },
                            {
                                "name": "allow-dns-out",
                                "priority": 110,
                                "action": "Allow",
                                "protocols": [{"port": 53, "protocol": "Udp"}],
                                "source_addresses": ["10.0.0.0/8"],
                                "destination_fqdns": ["*"],
                                "destination_ports": ["53"],
                            },
                        ],
                    },
                    {
                        "id": "rc-default-deny-200",
                        "name": "default-deny",
                        "priority": 200,
                        "action": "Deny",
                        "rules": [
                            {
                                "name": "deny-all",
                                "priority": 200,
                                "action": "Deny",
                                "protocols": [{"port": "*", "protocol": "Any"}],
                                "source_addresses": ["0.0.0.0/0"],
                                "destination_fqdns": ["*"],
                                "destination_ports": ["*"],
                            },
                        ],
                    },
                ],
                "nat_collections": [
                    {
                        "id": "nat-default-100",
                        "name": "default-nat",
                        "priority": 100,
                        "nat_rules": [
                            {
                                "name": "nat-ssh-redirect",
                                "priority": 100,
                                "protocols": ["Tcp"],
                                "source_addresses": ["0.0.0.0/0"],
                                "destination_addresses": ["20.0.0.5"],
                                "target_addresses": ["10.0.1.5"],
                                "translate_port": "22",
                                "translate_address": "10.0.1.5",
                                "original_destination": ["20.0.0.5"],
                            },
                        ],
                    }
                ],
            },
        ]

        # Track mutations for CRUD simulation
        self._created_rules: List[Dict[str, Any]] = []
        self._deleted_rule_names: set = set()
        self._operation_log: List[Dict[str, Any]] = []

        # Rate limiting (mock - always succeeds)
        self._rate_limit_retries = 3
        self._rate_limit_delay = 0.001
        self._rate_limit_max_delay = 0.01

        logger.info("MockAzureClient initialized with sample data")

    # ------------------------------------------------------------------ #
    # Authentication
    # ------------------------------------------------------------------ #

    def authenticate(self) -> bool:
        """Mock authentication - always succeeds."""
        self._is_authenticated = True
        self._authenticated_at = datetime.now(timezone.utc)
        logger.info("MockAzureClient: authenticated successfully (mock)")
        return True

    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated (always True in mock)."""
        return self._is_authenticated

    @property
    def network_client(self):
        """Return self since mock implements the full interface."""
        return self

    # ------------------------------------------------------------------ #
    # Policy Operations
    # ------------------------------------------------------------------ #

    def get_firewall_policy(
        self, resource_group: str, policy_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get a firewall policy by name."""
        for policy in self._policies:
            if policy["name"] == policy_name:
                logger.info(
                    "MockAzureClient: Retrieved firewall policy '%s' (mock)",
                    policy_name,
                )
                return deepcopy(policy)
        logger.warning(
            "MockAzureClient: Firewall policy '%s' not found (mock)", policy_name
        )
        return None

    def list_firewall_policies(self, resource_group: str) -> List[Dict[str, Any]]:
        """List all firewall policies."""
        policies = [deepcopy(p) for p in self._policies]
        logger.info(
            "MockAzureClient: Listed %d firewall policies (mock)", len(policies)
        )
        return policies

    # ------------------------------------------------------------------ #
    # Rule Collection Group Operations
    # ------------------------------------------------------------------ #

    def get_rule_collection_groups(
        self, resource_group: str, policy_name: str
    ) -> List[Dict[str, Any]]:
        """Get all rule collection groups for a firewall policy."""
        # Find the policy
        policy = self.get_firewall_policy(resource_group, policy_name)
        if not policy:
            logger.info(
                "MockAzureClient: No rule collection groups found for policy '%s' (mock)",
                policy_name,
            )
            return []

        # Find the matching group
        groups = [
            deepcopy(g)
            for g in self._rule_collection_groups
            if g["firewall_policy_id"] == policy["policy_id"]
        ]
        logger.info(
            "MockAzureClient: Retrieved %d rule collection groups for policy '%s' (mock)",
            len(groups),
            policy_name,
        )
        return groups

    # ------------------------------------------------------------------ #
    # Rule Extraction (from Azure)
    # ------------------------------------------------------------------ #

    def get_firewall_rules_from_azure(
        self, resource_group: str, policy_name: str
    ) -> List[Dict[str, Any]]:
        """Get all firewall rules from a firewall policy (mock)."""
        all_rules = []
        groups = self.get_rule_collection_groups(resource_group, policy_name)

        for group in groups:
            group_data = {
                "group_id": group.get("id"),
                "group_name": group.get("name"),
                "group_priority": group.get("priority"),
            }

            # Process rule collections
            for rc in group.get("rule_collections", []):
                collection_data = {
                    "collection_name": rc.get("name"),
                    "collection_priority": rc.get("priority"),
                    "collection_action": rc.get("action"),
                }

                for rule in rc.get("rules", []):
                    if rule.get("name") in self._deleted_rule_names:
                        continue
                    rule_data = {
                        "rule_name": rule.get("name"),
                        "rule_collection_name": collection_data["collection_name"],
                        "rule_collection_priority": collection_data["collection_priority"],
                        "rule_collection_action": collection_data["collection_action"],
                        "priority": rule.get("priority"),
                        "action": collection_data["collection_action"],
                        "rule_type": "allow"
                        if collection_data["collection_action"] == "Allow"
                        else "deny",
                        "source_addresses": rule.get("source_addresses", []),
                        "destination_fqdns": rule.get("destination_fqdns", []),
                        "destination_ports": rule.get("destination_ports", []),
                        "protocol": (
                            rule.get("protocols", [{}])[0].get("protocol", "Tcp")
                            if rule.get("protocols")
                            else "Tcp"
                        ),
                    }
                    rule_data.update(group_data)
                    all_rules.append(rule_data)

            # Process NAT collections
            for nc in group.get("nat_collections", []):
                collection_data = {
                    "collection_name": nc.get("name"),
                    "collection_priority": nc.get("priority"),
                    "collection_type": "nat",
                    "collection_action": "DNAT",
                }

                for rule in nc.get("nat_rules", []):
                    if rule.get("name") in self._deleted_rule_names:
                        continue
                    rule_data = {
                        "rule_name": rule.get("name"),
                        "rule_collection_name": collection_data["collection_name"],
                        "rule_collection_priority": collection_data["collection_priority"],
                        "rule_collection_action": "DNAT",
                        "priority": rule.get("priority"),
                        "rule_type": "dnat",
                        "translated_address": rule.get("translate_address"),
                        "translated_port": str(rule.get("translate_port", "")),
                        "original_destination": rule.get("original_destination"),
                        "source_addresses": rule.get("source_addresses", []),
                        "destination_addresses": rule.get("destination_addresses", []),
                        "target_addresses": rule.get("target_addresses", []),
                        "protocols": rule.get("protocols", []),
                    }
                    rule_data.update(group_data)
                    all_rules.append(rule_data)

        logger.info(
            "MockAzureClient: Retrieved %d rules from policy '%s' (mock)",
            len(all_rules),
            policy_name,
        )
        return all_rules

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate_firewall_rule(
        self, rule_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate a firewall rule (same logic as real AzureClient)."""
        errors = []

        required_fields = ["rule_collection_name", "priority", "action", "protocol"]
        for field in required_fields:
            if not rule_data.get(field):
                errors.append(f"Required field '{field}' is missing")

        collection_name = rule_data.get("rule_collection_name", "")
        if collection_name:
            if len(collection_name) < 3:
                errors.append(
                    "Rule collection name must be at least 3 characters long"
                )
            elif len(collection_name) > 80:
                errors.append(
                    "Rule collection name must not exceed 80 characters"
                )
            elif not all(
                c.isalnum() or c in " _-." for c in collection_name
            ):
                errors.append(
                    "Rule collection name can only contain alphanumeric characters, "
                    "spaces, underscores, hyphens, and dots"
                )

        priority = rule_data.get("priority")
        if priority is not None:
            if not isinstance(priority, int):
                errors.append("Priority must be an integer")
            elif priority < 100 or priority > 4096:
                errors.append(
                    f"Priority must be between 100 and 4096, got {priority}"
                )

        action = rule_data.get("action", "")
        if action not in ("Allow", "Deny", "DNAT"):
            errors.append(
                f"Action must be 'Allow', 'Deny', or 'DNAT', got '{action}'"
            )

        protocol = rule_data.get("protocol", "")
        valid_protocols = {"Tcp", "Udp", "Any", "IpProtocol"}
        if protocol not in valid_protocols:
            errors.append(
                f"Protocol must be one of {valid_protocols}, got '{protocol}'"
            )

        collection_action = rule_data.get("rule_collection_action", "")
        if collection_action and collection_action not in ("Allow", "Deny"):
            errors.append(
                f"Collection action must be 'Allow' or 'Deny', got '{collection_action}'"
            )

        # Validate destination FQDNs
        import re
        destination_fqdns = rule_data.get("destination_fqdns")
        if destination_fqdns:
            fqdns = (
                destination_fqdns
                if isinstance(destination_fqdns, list)
                else json.loads(destination_fqdns)
                if isinstance(destination_fqdns, str)
                else [destination_fqdns]
            )
            for fqdn in fqdns:
                if not self._validate_fqdn(fqdn):
                    errors.append(f"Invalid FQDN: {fqdn}")

        # Validate source IPs
        source_addresses = rule_data.get("source_addresses")
        if source_addresses:
            addresses = (
                source_addresses
                if isinstance(source_addresses, list)
                else json.loads(source_addresses)
                if isinstance(source_addresses, str)
                else [source_addresses]
            )
            import ipaddress
            for addr in addresses:
                if not self._validate_ip_address(addr):
                    errors.append(f"Invalid IP address: {addr}")

        # Validate destination ports
        destination_ports = rule_data.get("destination_ports")
        if destination_ports:
            ports = (
                destination_ports
                if isinstance(destination_ports, list)
                else json.loads(destination_ports)
                if isinstance(destination_ports, str)
                else [destination_ports]
            )
            for port in ports:
                try:
                    port_num = int(port) if not isinstance(port, int) else port
                    if port_num < 1 or port_num > 65535:
                        errors.append(
                            f"Port must be between 1 and 65535, got {port_num}"
                        )
                except (ValueError, TypeError):
                    errors.append(f"Invalid port number: {port}")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info("MockAzureClient: Rule validation passed (mock)")
        else:
            logger.warning(
                "MockAzureClient: Rule validation failed: %s (mock)", errors
            )
        return is_valid, errors

    def _validate_fqdn(self, fqdn: str) -> bool:
        """Validate an FQDN string."""
        if not fqdn or not isinstance(fqdn, str):
            return False
        if fqdn == "*":
            return True
        import re
        pattern = r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        return bool(re.match(pattern, fqdn.strip()))

    def _validate_ip_address(self, addr: str) -> bool:
        """Validate an IP address or CIDR notation."""
        import ipaddress
        try:
            if "/" in addr:
                network = ipaddress.ip_network(addr, strict=False)
                return 0 <= network.prefixlen <= 32
            else:
                ipaddress.ip_address(addr)
                return True
        except (ValueError, TypeError):
            return False

    # ------------------------------------------------------------------ #
    # CRUD Operations (in-memory)
    # ------------------------------------------------------------------ #

    def create_firewall_rule_in_azure(
        self,
        resource_group: str,
        policy_name: str,
        collection_name: str,
        rule_data: Dict[str, Any],
    ) -> Optional[str]:
        """Create a firewall rule in the mock client."""
        self._log_operation("create_rule", {
            "policy": policy_name,
            "collection": collection_name,
            "rule": rule_data,
        })

        # Find the matching group and collection
        groups = self.get_rule_collection_groups(resource_group, policy_name)
        for group in groups:
            for rc in group.get("rule_collections", []):
                if rc["name"] == collection_name:
                    rule_entry = {
                        "name": rule_data.get("rule_name", f"rule-{uuid.uuid4().hex[:8]}"),
                        "priority": rule_data.get("priority", 100),
                        "action": rule_data.get("action", "Allow"),
                        "protocols": [
                            {
                                "port": rule_data.get("destination_ports", ["443"])[0]
                                if rule_data.get("destination_ports")
                                else "443",
                                "protocol": rule_data.get("protocol", "Tcp"),
                            }
                        ],
                        "source_addresses": rule_data.get("source_addresses", []),
                        "destination_fqdns": rule_data.get("destination_fqdns", []),
                        "destination_ports": rule_data.get("destination_ports", []),
                    }
                    rc["rules"].append(rule_entry)

                    # Also track in operation log
                    self._created_rules.append({
                        "policy": policy_name,
                        "collection": collection_name,
                        "rule_name": rule_entry["name"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                    logger.info(
                        "MockAzureClient: Created rule '%s' in collection '%s' (mock)",
                        rule_entry["name"],
                        collection_name,
                    )
                    return f"mock-rule-id-{uuid.uuid4().hex[:8]}"
            # Try NAT collections
            for nc in group.get("nat_collections", []):
                if nc["name"] == collection_name:
                    rule_entry = {
                        "name": rule_data.get("rule_name", f"nat-rule-{uuid.uuid4().hex[:8]}"),
                        "priority": rule_data.get("priority", 100),
                        "protocols": rule_data.get("protocols", ["Tcp"]),
                        "source_addresses": rule_data.get("source_addresses", []),
                        "destination_addresses": rule_data.get("destination_addresses", []),
                        "target_addresses": rule_data.get("target_addresses", []),
                        "translate_port": rule_data.get("translated_port", ""),
                        "translate_address": rule_data.get("translated_address"),
                        "original_destination": rule_data.get("original_destination"),
                    }
                    nc["nat_rules"].append(rule_entry)
                    self._created_rules.append({
                        "policy": policy_name,
                        "collection": collection_name,
                        "rule_name": rule_entry["name"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "type": "nat",
                    })
                    logger.info(
                        "MockAzureClient: Created NAT rule '%s' in collection '%s' (mock)",
                        rule_entry["name"],
                        collection_name,
                    )
                    return f"mock-nat-rule-id-{uuid.uuid4().hex[:8]}"

        # Create the collection if it doesn't exist
        policy = self.get_firewall_policy(resource_group, policy_name)
        if policy:
            policy_id = policy["policy_id"]
            # Find or create group
            group = None
            for g in self._rule_collection_groups:
                if g["firewall_policy_id"] == policy_id:
                    group = g
                    break
            if not group:
                group = {
                    "id": f"rg-{policy_name}-group-{uuid.uuid4().hex[:8]}",
                    "name": f"{policy_name}-group",
                    "priority": 100,
                    "firewall_policy_id": policy_id,
                    "rule_collections": [],
                    "nat_collections": [],
                }
                self._rule_collection_groups.append(group)

            # Create collection
            new_rc = {
                "id": f"rc-{collection_name}-{uuid.uuid4().hex[:8]}",
                "name": collection_name,
                "priority": rule_data.get("priority", 100),
                "action": rule_data.get("action", "Allow"),
                "rules": [
                    {
                        "name": rule_data.get("rule_name", f"rule-{uuid.uuid4().hex[:8]}"),
                        "priority": rule_data.get("priority", 100),
                        "action": rule_data.get("action", "Allow"),
                        "protocols": [
                            {
                                "port": rule_data.get("destination_ports", ["443"])[0]
                                if rule_data.get("destination_ports")
                                else "443",
                                "protocol": rule_data.get("protocol", "Tcp"),
                            }
                        ],
                        "source_addresses": rule_data.get("source_addresses", []),
                        "destination_fqdns": rule_data.get("destination_fqdns", []),
                        "destination_ports": rule_data.get("destination_ports", []),
                    }
                ],
            }
            group["rule_collections"].append(new_rc)
            self._created_rules.append({
                "policy": policy_name,
                "collection": collection_name,
                "rule_name": new_rc["rules"][0]["name"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            return f"mock-rule-id-{uuid.uuid4().hex[:8]}"

        logger.warning(
            "MockAzureClient: Could not find policy '%s' (mock)", policy_name
        )
        return None

    def delete_firewall_rule_in_azure(
        self,
        resource_group: str,
        policy_name: str,
        collection_name: str,
        rule_name: str,
    ) -> bool:
        """Delete a firewall rule from the mock client."""
        self._log_operation("delete_rule", {
            "policy": policy_name,
            "collection": collection_name,
            "rule_name": rule_name,
        })

        groups = self.get_rule_collection_groups(resource_group, policy_name)
        for group in groups:
            for rc in group.get("rule_collections", []):
                if rc["name"] == collection_name:
                    original_count = len(rc["rules"])
                    rc["rules"] = [r for r in rc["rules"] if r["name"] != rule_name]
                    if len(rc["rules"]) < original_count:
                        self._deleted_rule_names.add(rule_name)
                        logger.info(
                            "MockAzureClient: Deleted rule '%s' (mock)", rule_name
                        )
                        return True
            for nc in group.get("nat_collections", []):
                if nc["name"] == collection_name:
                    original_count = len(nc["nat_rules"])
                    nc["nat_rules"] = [
                        r for r in nc["nat_rules"] if r["name"] != rule_name
                    ]
                    if len(nc["nat_rules"]) < original_count:
                        self._deleted_rule_names.add(rule_name)
                        logger.info(
                            "MockAzureClient: Deleted NAT rule '%s' (mock)", rule_name
                        )
                        return True

        self._deleted_rule_names.add(rule_name)
        logger.info(
            "MockAzureClient: Marked rule '%s' as deleted (mock)", rule_name
        )
        return True

    def bulk_create_firewall_rules(
        self,
        resource_group: str,
        policy_name: str,
        rules_batch: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Bulk create rules in the mock client."""
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "created_rules": [],
        }

        for rule_data in rules_batch:
            rule_name = rule_data.get("rule_name", f"rule-{uuid.uuid4().hex[:8]}")
            rule_collection = rule_data.get("rule_collection_name", collection_name or "default-collection")
            ok = self.create_firewall_rule_in_azure(
                resource_group, policy_name, rule_collection, rule_data
            )
            if ok:
                results["success_count"] += 1
                results["created_rules"].append(rule_name)
            else:
                results["failed_count"] += 1
                results["errors"].append(f"Failed to create rule '{rule_name}'")

        logger.info(
            "MockAzureClient: Bulk created %d/%d rules (mock)",
            results["success_count"],
            len(rules_batch),
        )
        return results

    def bulk_delete_firewall_rules(
        self,
        resource_group: str,
        policy_name: str,
        rule_names: List[str],
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Bulk delete rules from the mock client."""
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "deleted_rules": [],
        }

        for rule_name in rule_names:
            if self.delete_firewall_rule_in_azure(
                resource_group, policy_name, collection_name or "", rule_name
            ):
                results["success_count"] += 1
                results["deleted_rules"].append(rule_name)
            else:
                results["failed_count"] += 1
                results["errors"].append(f"Failed to delete rule '{rule_name}'")

        logger.info(
            "MockAzureClient: Bulk deleted %d/%d rules (mock)",
            results["success_count"],
            len(rule_names),
        )
        return results

    def check_duplicate_rules(
        self,
        new_rules: List[Dict[str, Any]],
        existing_rules: List[Dict[str, Any]],
        priority_field: str = "priority",
        collection_field: str = "rule_collection_name",
    ) -> List[Dict[str, Any]]:
        """Check for duplicate rules (mock - same logic as AzureClient)."""
        duplicates = []
        existing_lookup = {}
        for existing_rule in existing_rules:
            key = self._rule_key(existing_rule, collection_field)
            existing_lookup[key] = existing_rule

        for new_rule in new_rules:
            key = self._rule_key(new_rule, collection_field)
            if key in existing_lookup:
                existing_rule = existing_lookup[key]
                if new_rule.get(priority_field) == existing_rule.get(priority_field):
                    duplicates.append({
                        "new_rule": new_rule,
                        "existing_rule": existing_rule,
                        "conflict_type": "priority_collision",
                        "message": f"Duplicate rule found in collection '{new_rule.get(collection_field)}' with same priority {new_rule.get(priority_field)}",
                    })
                else:
                    duplicates.append({
                        "new_rule": new_rule,
                        "existing_rule": existing_rule,
                        "conflict_type": "name_collision",
                        "message": f"Rule name '{new_rule.get('rule_name', 'unknown')}' already exists in collection '{new_rule.get(collection_field)}'",
                    })
        return duplicates

    def _rule_key(self, rule: Dict[str, Any], collection_field: str) -> str:
        """Generate a unique key for a rule."""
        collection = rule.get(collection_field, "")
        rule_name = rule.get("rule_name", "")
        rule_priority = rule.get("priority", "")
        return f"{collection}:{rule_name}:{rule_priority}"

    # ------------------------------------------------------------------ #
    # Status Operations
    # ------------------------------------------------------------------ #

    def get_azure_firewall_status(
        self, resource_group: str, firewall_name: str
    ) -> Dict[str, Any]:
        """Get mock firewall status."""
        return {
            "name": firewall_name,
            "resource_group": resource_group,
            "location": "eastus",
            "state": "Deployed",
            "sku_tier": "Standard",
            "scale_units": 3,
            "tags": {"env": "development"},
            "policy_id": "policy-001",
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _log_operation(self, operation: str, details: Dict[str, Any]):
        """Log an operation for debugging/auditing."""
        self._operation_log.append({
            "operation": operation,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ------------------------------------------------------------------ #
    # Factory compatibility
    # ------------------------------------------------------------------ #

    @classmethod
    def from_settings(cls, settings) -> "MockAzureClient":
        """Create a MockAzureClient from settings (factory pattern compat)."""
        return cls()