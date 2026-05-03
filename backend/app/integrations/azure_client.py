"""
Azure SDK client for Azure Firewall Management integration.

Provides Azure service authentication, firewall rule management,
resource group operations, and rule validation through Azure SDK.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from azure.identity import ClientSecretCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import (
    FirewallPolicy,
    FirewallPolicyRuleCollection,
    FirewallPolicyNatRuleCollection,
    FirewallPolicyRuleCollectionGroup,
)
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError, AzureError

logger = logging.getLogger(__name__)


class AzureClientError(Exception):
    """Base exception for Azure client operations."""

    pass


class AzureAuthenticationError(AzureClientError):
    """Raised when Azure authentication fails."""

    pass


class AzureResourceNotFoundError(AzureClientError):
    """Raised when Azure resource is not found."""

    pass


class AzureRuleValidationError(AzureClientError):
    """Raised when Azure rule validation fails."""

    pass


class AzureRateLimitExceededError(AzureClientError):
    """Raised when Azure rate limit is exceeded."""

    pass


class AzureClient:
    """Azure SDK client for firewall management operations.

    Handles authentication and provides methods to interact with
    Azure Firewall, firewall policies, and rule collections.

    Usage:
        azure_client = AzureClient(
            tenant_id="...",
            client_id="...",
            client_secret="...",
            subscription_id="..."
        )
        await azure_client.authenticate()
        rules = await azure_client.list_firewall_rules(policy_id="...")
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        subscription_id: str,
        location: str = "eastus",
    ):
        """Initialize the AzureClient.

        Args:
            tenant_id: Azure AD tenant ID for authentication.
            client_id: Service principal client ID.
            client_secret: Service principal client secret.
            subscription_id: Azure subscription ID.
            location: Azure region for resource creation.

        Raises:
            AzureAuthenticationError: If credentials are invalid.
        """
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._subscription_id = subscription_id
        self._location = location
        self._network_client: Optional[NetworkManagementClient] = None
        self._is_authenticated = False

        # Rate limiting configuration
        self._rate_limit_retries = 3
        self._rate_limit_delay = 1  # seconds
        self._rate_limit_max_delay = 30  # seconds

        logger.info("AzureClient initialized for subscription %s", subscription_id)

    def authenticate(self) -> bool:
        """Authenticate with Azure using service principal credentials.

        Returns:
            True if authentication was successful.

        Raises:
            AzureAuthenticationError: If credentials are invalid or expired.
        """
        try:
            credentials = ClientSecretCredential(
                tenant_id=self._tenant_id,
                client_id=self._client_id,
                client_secret=self._client_secret,
            )

            self._network_client = NetworkManagementClient(
                credentials, self._subscription_id
            )
            self._is_authenticated = True

            logger.info(
                "AzureClient authenticated successfully for subscription %s",
                self._subscription_id,
            )
            return True

        except AzureError as e:
            logger.error("Azure authentication failed: %s", str(e))
            raise AzureAuthenticationError(f"Authentication failed: {str(e)}") from e

    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._is_authenticated

    @property
    def network_client(self) -> NetworkManagementClient:
        """Get the Azure Network Management Client."""
        if not self._is_authenticated:
            self.authenticate()
        return self._network_client

    def get_firewall_policy(
        self, resource_group: str, policy_name: str
    ) -> Optional[FirewallPolicy]:
        """Get an Azure firewall policy by name.

        Args:
            resource_group: Azure resource group name.
            policy_name: Name of the firewall policy.

        Returns:
            FirewallPolicy if found, None otherwise.

        Raises:
            AzureResourceNotFoundError: If policy cannot be accessed.
        """
        try:
            policy = self.network_client.firewall_policies.get(
                resource_group, policy_name
            )
            logger.info(
                "Retrieved firewall policy '%s' in group '%s'",
                policy_name,
                resource_group,
            )
            return policy

        except ResourceNotFoundError:
            logger.warning(
                "Firewall policy '%s' not found in group '%s'",
                policy_name,
                resource_group,
            )
            return None

        except AzureError as e:
            logger.error(
                "Error retrieving firewall policy '%s': %s", policy_name, str(e)
            )
            raise AzureResourceNotFoundError(
                f"Failed to retrieve policy '{policy_name}': {str(e)}"
            ) from e

    def list_firewall_policies(self, resource_group: str) -> List[FirewallPolicy]:
        """List all firewall policies in a resource group.

        Args:
            resource_group: Azure resource group name.

        Returns:
            List of FirewallPolicy objects.
        """
        try:
            policies = list(self.network_client.firewall_policies.list(resource_group))
            logger.info(
                "Listed %d firewall policies in group '%s'",
                len(policies),
                resource_group,
            )
            return policies

        except AzureError as e:
            logger.error("Error listing firewall policies: %s", str(e))
            raise AzureClientError(
                f"Failed to list firewall policies: {str(e)}"
            ) from e

    def get_rule_collection_groups(
        self, resource_group: str, policy_name: str
    ) -> List[Dict[str, Any]]:
        """Get all rule collection groups for a firewall policy.

        Args:
            resource_group: Azure resource group name.
            policy_name: Name of the firewall policy.

        Returns:
            List of dictionaries containing rule collection group data.
        """
        try:
            groups = list(
                self.network_client.firewall_policy_rule_collection_groups.list(
                    resource_group, policy_name
                )
            )
            logger.info(
                "Retrieved %d rule collection groups for policy '%s'",
                len(groups),
                policy_name,
            )
            return groups

        except ResourceNotFoundError:
            logger.info(
                "No rule collection groups found for policy '%s'", policy_name
            )
            return []

        except AzureError as e:
            logger.error(
                "Error retrieving rule collection groups for policy '%s': %s",
                policy_name,
                str(e),
            )
            raise AzureClientError(
                f"Failed to get rule collection groups: {str(e)}"
            ) from e

    def get_firewall_rules_from_azure(
        self, resource_group: str, policy_name: str
    ) -> List[Dict[str, Any]]:
        """Get all firewall rules from an Azure firewall policy.

        This is the main method for importing firewall rules from Azure
        into the application database.

        Args:
            resource_group: Azure resource group name.
            policy_name: Name of the firewall policy.

        Returns:
            List of dictionaries containing rule data in the format compatible
            with our database models.

        Raises:
            AzureClientError: If rules cannot be retrieved.
        """
        all_rules = []

        try:
            rule_collection_groups = self.get_rule_collection_groups(
                resource_group, policy_name
            )

            for group in rule_collection_groups:
                group_data = {
                    "group_id": str(getattr(group, "id", None)) if group else None,
                    "group_name": getattr(group, "name", None),
                    "group_priority": getattr(group, "priority", None),
                }

                # Process rule collections (regular firewall rules)
                if group and hasattr(group, "rule_collections") and group.rule_collections:
                    for rc in group.rule_collections:
                        collection_data = {
                            "collection_name": getattr(rc, "name", None),
                            "collection_priority": getattr(rc, "priority", None),
                            "collection_action": getattr(rc, "action", None) or "Allow",
                        }

                        if hasattr(rc, "rules") and rc.rules:
                            for rule in rc.rules:
                                rule_data = self._extract_rule_data(
                                    rule, collection_data
                                )
                                rule_data.update(group_data)
                                all_rules.append(rule_data)
                        else:
                            logger.debug(
                                "Collection '%s' has no rules", getattr(rc, "name", "unknown")
                            )

                # Process NAT collections
                if group and hasattr(group, "nat_collections") and group.nat_collections:
                    for nc in group.nat_collections:
                        collection_data = {
                            "collection_name": getattr(nc, "name", None),
                            "collection_priority": getattr(nc, "priority", None),
                            "collection_type": "nat",
                        }

                        if hasattr(nc, "nat_rules") and nc.nat_rules:
                            for rule in nc.nat_rules:
                                nat_rule_data = self._extract_nat_rule_data(
                                    rule, collection_data
                                )
                                nat_rule_data.update(group_data)
                                all_rules.append(nat_rule_data)
                        else:
                            logger.debug("NAT collection '%s' has no rules", getattr(nc, "name", "unknown"))

            logger.info(
                "Retrieved %d rules from policy '%s'", len(all_rules), policy_name
            )
            return all_rules

        except AzureClientError:
            raise
        except AzureError as e:
            logger.error(
                "Error retrieving rules from Azure policy '%s': %s",
                policy_name,
                str(e),
            )
            raise AzureClientError(
                f"Failed to retrieve rules from Azure: {str(e)}"
            ) from e

    def _extract_rule_data(
        self, rule: Any, collection_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract rule data from an Azure rule object (dict-based).

        Args:
            rule: Azure SDK rule object or dict.
            collection_data: Parent collection metadata.

        Returns:
            Dictionary containing extracted rule data.
        """
        # Handle dict-based rules (Azure SDK 30.x style)
        if isinstance(rule, dict):
            rule_data = {
                "rule_name": rule.get("name", ""),
                "rule_collection_name": collection_data.get("collection_name"),
                "rule_collection_priority": collection_data.get("collection_priority"),
                "rule_collection_action": collection_data.get("collection_action"),
                "priority": rule.get("priority", 100),
                "action": collection_data.get("collection_action", "Allow"),
                "rule_type": "allow" if rule.get("action", "") == "Allow" else "deny",
            }
            rule_data["source_addresses"] = rule.get("source_addresses", [])
            rule_data["destination_fqdns"] = rule.get("fqdn_filters", [])
            rule_data["destination_ports"] = rule.get("destination_ports", [])
            rule_data["protocol"] = rule.get("protocol", "Tcp")
        else:
            # Handle object-based rules
            rule_data = {
                "rule_name": getattr(rule, "name", ""),
                "rule_collection_name": collection_data.get("collection_name"),
                "rule_collection_priority": collection_data.get("collection_priority"),
                "rule_collection_action": collection_data.get("collection_action"),
                "priority": getattr(rule, "priority", 100),
                "action": collection_data.get("collection_action", "Allow"),
                "rule_type": "allow" if getattr(rule, "action", "") == "Allow" else "deny",
            }
            rule_data["source_addresses"] = getattr(rule, "source_addresses", []) or []
            rule_data["destination_fqdns"] = getattr(rule, "fqdn_filters", []) or []
            rule_data["destination_ports"] = getattr(rule, "destination_ports", []) or []
            rule_data["protocol"] = getattr(rule, "protocol", "Tcp")

        logger.debug("Extracted rule data: %s", rule_data)
        return rule_data

    def _extract_nat_rule_data(
        self, rule: Any, collection_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract rule data from an Azure NAT rule object.

        Args:
            rule: Azure SDK NAT rule object or dict.
            collection_data: Parent NAT collection metadata.

        Returns:
            Dictionary containing extracted NAT rule data.
        """
        # Handle dict-based NAT rules
        if isinstance(rule, dict):
            rule_data = {
                "rule_name": rule.get("name", ""),
                "rule_collection_name": collection_data.get("collection_name"),
                "rule_collection_priority": collection_data.get("collection_priority"),
                "rule_collection_action": "DNAT",
                "priority": rule.get("priority", 100),
                "rule_type": "dnat",
                "translated_address": rule.get("translate_address"),
                "translated_port": str(rule.get("translate_port", "")),
                "original_destination": rule.get("original_destination"),
                "source_addresses": rule.get("source_addresses", []),
                "destination_addresses": rule.get("destination_addresses", []),
                "target_addresses": rule.get("target_addresses", []),
                "protocols": rule.get("protocols", []),
            }
        else:
            # Handle object-based NAT rules
            rule_data = {
                "rule_name": getattr(rule, "name", ""),
                "rule_collection_name": collection_data.get("collection_name"),
                "rule_collection_priority": collection_data.get("collection_priority"),
                "rule_collection_action": "DNAT",
                "priority": getattr(rule, "priority", 100),
                "rule_type": "dnat",
                "translated_address": getattr(rule, "translate_address", None),
                "translated_port": str(getattr(rule, "translate_port", "") or ""),
                "original_destination": getattr(rule, "original_destination", None),
                "source_addresses": getattr(rule, "source_addresses", []) or [],
                "destination_addresses": getattr(rule, "destination_addresses", []) or [],
                "target_addresses": getattr(rule, "target_addresses", []) or [],
                "protocols": getattr(rule, "protocols", []) or [],
            }

        logger.debug("Extracted NAT rule data: %s", rule_data)
        return rule_data

    def validate_firewall_rule(
        self, rule_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate a firewall rule against Azure constraints.

        Args:
            rule_data: Dictionary containing rule data to validate.

        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors = []

        # Required fields validation
        required_fields = ["rule_collection_name", "priority", "action", "protocol"]
        for field in required_fields:
            if not rule_data.get(field):
                errors.append(f"Required field '{field}' is missing")

        # Rule collection name validation
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
            elif not all(c.isalnum() or c in " _-." for c in collection_name):
                errors.append(
                    "Rule collection name can only contain alphanumeric characters, spaces, underscores, hyphens, and dots"
                )

        # Priority validation (Azure uses 100-4096 for rule collections)
        priority = rule_data.get("priority")
        if priority is not None:
            if not isinstance(priority, int):
                errors.append("Priority must be an integer")
            elif priority < 100 or priority > 4096:
                errors.append(
                    f"Priority must be between 100 and 4096, got {priority}"
                )

        # Action validation
        action = rule_data.get("action", "")
        if action not in ("Allow", "Deny", "DNAT"):
            errors.append(f"Action must be 'Allow', 'Deny', or 'DNAT', got '{action}'")

        # Protocol validation
        protocol = rule_data.get("protocol", "")
        valid_protocols = {"Tcp", "Udp", "Any", "IpProtocol"}
        if protocol not in valid_protocols:
            errors.append(
                f"Protocol must be one of {valid_protocols}, got '{protocol}'"
            )

        # Collection action validation
        collection_action = rule_data.get("rule_collection_action", "")
        if collection_action and collection_action not in ("Allow", "Deny"):
            errors.append(
                f"Collection action must be 'Allow' or 'Deny', got '{collection_action}'"
            )

        # Destination FQDN validation (for application rules)
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

        # Source IP validation
        source_addresses = rule_data.get("source_addresses")
        if source_addresses:
            addresses = (
                source_addresses
                if isinstance(source_addresses, list)
                else json.loads(source_addresses)
                if isinstance(source_addresses, str)
                else [source_addresses]
            )
            for addr in addresses:
                if not self._validate_ip_address(addr):
                    errors.append(f"Invalid IP address: {addr}")

        # Destination port validation
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
                        errors.append(f"Port must be between 1 and 65535, got {port_num}")
                except (ValueError, TypeError):
                    errors.append(f"Invalid port number: {port}")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info("Firewall rule validation passed for rule data")
        else:
            logger.warning(
                "Firewall rule validation failed: %s", errors
            )

        return is_valid, errors

    def _validate_fqdn(self, fqdn: str) -> bool:
        """Validate an FQDN string.

        Args:
            fqdn: FQDN string to validate.

        Returns:
            True if valid FQDN.
        """
        if not fqdn or not isinstance(fqdn, str):
            return False

        import re
        pattern = r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        return bool(re.match(pattern, fqdn.strip()))

    def _validate_ip_address(self, addr: str) -> bool:
        """Validate an IP address or CIDR notation.

        Args:
            addr: IP address or CIDR notation string.

        Returns:
            True if valid IP address.
        """
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

    def check_duplicate_rules(
        self,
        new_rules: List[Dict[str, Any]],
        existing_rules: List[Dict[str, Any]],
        priority_field: str = "priority",
        collection_field: str = "rule_collection_name",
    ) -> List[Dict[str, Any]]:
        """Check for duplicate rules between new and existing rules.

        Args:
            new_rules: List of new rule dictionaries to check.
            existing_rules: List of existing rule dictionaries.
            priority_field: Field name for priority comparison.
            collection_field: Field name for collection name comparison.

        Returns:
            List of duplicate findings with details.
        """
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

        if duplicates:
            logger.warning("Found %d duplicate rules", len(duplicates))
        return duplicates

    def _rule_key(self, rule: Dict[str, Any], collection_field: str) -> str:
        """Generate a unique key for a rule based on collection and name."""
        collection = rule.get(collection_field, "")
        rule_name = rule.get("rule_name", "")
        rule_priority = rule.get("priority", "")
        return f"{collection}:{rule_name}:{rule_priority}"

    def _create_azure_rule_dict(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a dict-based Azure rule object compatible with SDK 30.x."""
        return {
            "name": rule_data.get("rule_name", "rule"),
            "priority": rule_data.get("priority", 100),
            "action": rule_data.get("action", "Allow"),
            "source_addresses": rule_data.get("source_addresses", []),
            "destination_fqdns": rule_data.get("destination_fqdns", []),
            "destination_ports": rule_data.get("destination_ports", []),
            "protocol": rule_data.get("protocol", "Tcp"),
        }

    def create_firewall_rule_in_azure(
        self,
        resource_group: str,
        policy_name: str,
        collection_name: str,
        rule_data: Dict[str, Any],
    ) -> Optional[str]:
        """Create a single firewall rule in Azure.

        Args:
            resource_group: Azure resource group name.
            policy_name: Name of the firewall policy.
            collection_name: Name of the rule collection.
            rule_data: Dictionary containing rule data.

        Returns:
            Rule ID if created successfully, None otherwise.
        """
        try:
            collection = self.network_client.firewall_policy_rule_collection_groups.get(
                resource_group, policy_name, collection_name
            )

            azure_rule = self._create_azure_rule_dict(rule_data)

            if not hasattr(collection, "rules") or collection.rules is None:
                collection.rules = []
            collection.rules.append(azure_rule)

            poller = self.network_client.firewall_policy_rule_collection_groups.begin_create_or_update(
                resource_group, policy_name, collection_name, collection
            )
            result = poller.result()

            logger.info(
                "Created rule '%s' in collection '%s' on policy '%s'",
                rule_data.get("rule_name"),
                collection_name,
                policy_name,
            )
            return str(result.id) if result and result.id else None

        except ResourceNotFoundError:
            logger.error(
                "Collection '%s' not found in policy '%s'",
                collection_name,
                policy_name,
            )
            return None

        except AzureError as e:
            logger.error("Failed to create rule in Azure: %s", str(e))
            raise AzureClientError(f"Failed to create rule: {str(e)}") from e

    def delete_firewall_rule_in_azure(
        self,
        resource_group: str,
        policy_name: str,
        collection_name: str,
        rule_name: str,
    ) -> bool:
        """Delete a single firewall rule from Azure.

        Args:
            resource_group: Azure resource group name.
            policy_name: Name of the firewall policy.
            collection_name: Name of the rule collection.
            rule_name: Name of the rule to delete.

        Returns:
            True if deleted successfully.
        """
        try:
            collection = self.network_client.firewall_policy_rule_collection_groups.get(
                resource_group, policy_name, collection_name
            )

            if hasattr(collection, "rules") and collection.rules:
                filtered_rules = []
                for r in collection.rules:
                    if hasattr(r, "name"):
                        if r.name != rule_name:
                            filtered_rules.append(r)
                    else:
                        if r.get("name", "") != rule_name:
                            filtered_rules.append(r)
                collection.rules = filtered_rules

            poller = self.network_client.firewall_policy_rule_collection_groups.begin_create_or_update(
                resource_group, policy_name, collection_name, collection
            )
            poller.result()

            logger.info(
                "Deleted rule '%s' from collection '%s'",
                rule_name,
                collection_name,
            )
            return True

        except ResourceNotFoundError:
            logger.warning(
                "Collection '%s' not found, rule '%s' may already be deleted",
                collection_name,
                rule_name,
            )
            return False

        except AzureError as e:
            logger.error("Failed to delete rule from Azure: %s", str(e))
            raise AzureClientError(f"Failed to delete rule: {str(e)}") from e

    def bulk_create_firewall_rules(
        self,
        resource_group: str,
        policy_name: str,
        rules_batch: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create multiple firewall rules in Azure in a single operation.

        Args:
            resource_group: Azure resource group name.
            policy_name: Name of the firewall policy.
            rules_batch: List of rule dictionaries.
            collection_name: Optional collection name to create/use.

        Returns:
            Dictionary containing results with success_count, failed_count, and errors.
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "created_rules": [],
        }

        try:
            azure_rules = []
            for i, rule_data in enumerate(rules_batch):
                try:
                    azure_rule = self._create_azure_rule_dict(rule_data)
                    azure_rules.append(azure_rule)
                except Exception as e:
                    results["errors"].append({
                        "index": i,
                        "rule": rule_data,
                        "error": str(e),
                    })
                    results["failed_count"] += 1

            if not azure_rules:
                results["errors"].append("No valid rules to create")
                return results

            try:
                collection = self.network_client.firewall_policy_rule_collection_groups.get(
                    resource_group, policy_name, collection_name
                )
                if not collection.rules:
                    collection.rules = []
                collection.rules.extend(azure_rules)
                poller = self.network_client.firewall_policy_rule_collection_groups.begin_create_or_update(
                    resource_group, policy_name, collection_name, collection
                )
            except ResourceNotFoundError:
                collection = FirewallPolicyRuleCollectionGroup(
                    name=f"{collection_name}-group",
                    priority=1000,
                    rules=azure_rules,
                )
                poller = self.network_client.firewall_policy_rule_collection_groups.begin_create_or_update(
                    resource_group, policy_name, collection_name, collection
                )

            poller.result()
            results["success_count"] = len(azure_rules)
            results["created_rules"] = [r.get("name", "") for r in azure_rules]

            logger.info(
                "Bulk created %d rules in policy '%s'",
                results["success_count"],
                policy_name,
            )

        except AzureError as e:
            logger.error("Bulk create failed for policy '%s': %s", policy_name, str(e))
            results["errors"].append(f"Failed to create collection: {str(e)}")
            results["failed_count"] = len(rules_batch)

        return results

    def bulk_delete_firewall_rules(
        self,
        resource_group: str,
        policy_name: str,
        rule_names: List[str],
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete multiple firewall rules from Azure.

        Args:
            resource_group: Azure resource group name.
            policy_name: Name of the firewall policy.
            rule_names: List of rule names to delete.
            collection_name: Optional collection name.

        Returns:
            Dictionary containing results with success_count, failed_count, and errors.
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "deleted_rules": [],
        }

        try:
            collection = self.network_client.firewall_policy_rule_collection_groups.get(
                resource_group, policy_name, collection_name
            )

            if hasattr(collection, "rules") and collection.rules:
                before_count = len(collection.rules)
                collection.rules = [
                    r for r in collection.rules
                    if getattr(r, "name", None) not in rule_names
                ]
                deleted_count = before_count - len(collection.rules)

                poller = self.network_client.firewall_policy_rule_collection_groups.begin_create_or_update(
                    resource_group, policy_name, collection_name, collection
                )
                poller.result()

                results["success_count"] = deleted_count
                results["deleted_rules"] = rule_names[:deleted_count]
                results["failed_count"] = len(rule_names) - deleted_count
            else:
                results["failed_count"] = len(rule_names)
                results["errors"].append("Collection has no rules")

            logger.info(
                "Bulk deleted %d rules from policy '%s'",
                results["success_count"],
                policy_name,
            )

        except ResourceNotFoundError:
            results["errors"].append(f"Collection '{collection_name}' not found")
            results["failed_count"] = len(rule_names)

        except AzureError as e:
            logger.error("Bulk delete failed for policy '%s': %s", policy_name, str(e))
            results["errors"].append(f"Failed to delete: {str(e)}")
            results["failed_count"] = len(rule_names)

        return results

    def get_azure_firewall_status(
        self, resource_group: str, firewall_name: str
    ) -> Dict[str, Any]:
        """Get the status of an Azure Firewall.

        Args:
            resource_group: Azure resource group name.
            firewall_name: Name of the Azure Firewall.

        Returns:
            Dictionary containing firewall status information.
        """
        try:
            firewall = self.network_client.firewalls.get(resource_group, firewall_name)

            status_info = {
                "name": firewall.name,
                "resource_group": resource_group,
                "location": firewall.location,
                "state": "Deployed" if getattr(firewall, "scale_units", 0) and firewall.scale_units > 0 else "Not deployed",
                "sku_tier": str(firewall.sku.tier) if firewall.sku else "Unknown",
                "scale_units": firewall.scale_units,
                "managed_service_ids": firewall.managed_service_ids,
                "tags": getattr(firewall, "tags", {}) or {},
                "policy_id": getattr(firewall, "firewall_policy_id", None),
            }

            logger.info("Retrieved firewall status for '%s': %s", firewall_name, status_info)
            return status_info

        except ResourceNotFoundError:
            return {
                "name": firewall_name,
                "resource_group": resource_group,
                "state": "Not found",
                "error": f"Firewall '{firewall_name}' not found in resource group '{resource_group}'",
            }

        except AzureError as e:
            logger.error("Error getting firewall status: %s", str(e))
            return {
                "name": firewall_name,
                "resource_group": resource_group,
                "state": "Error",
                "error": str(e),
            }


# Factory function for creating AzureClient from settings
def create_azure_client_from_settings(settings) -> AzureClient:
    """Create an AzureClient from application settings.

    Args:
        settings: Settings object containing Azure configuration.

    Returns:
        Configured AzureClient instance.
    """
    return AzureClient(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        subscription_id=settings.azure_subscription_id,
        location=settings.azure_region,
    )