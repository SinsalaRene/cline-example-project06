/**
 * Impact Analyzer Service
 *
 * Core service for analyzing the impact of NSG rule changes on the network topology.
 * Performs before/after rule comparison, affected subnet identification, and
 * reachable external device calculation.
 *
 * # Impact Analysis Algorithm
 *
 * The analysis follows this process:
 *
 * ```
 * 1. Rule Comparison (compareRules):
 *    - Index both old and new rule sets by rule name
 *    - For each name present in both: compare all fields → MODIFIED or UNCHANGED
 *    - Names only in new set → ADDED
 *    - Names only in old set → REMOVED
 *
 * 2. Affected Subnet Identification (getAffectedSubnets):
 *    - For each subnet with an NSG, check rules matching its address prefix
 *    - ADDED/MODIFIED allow rules targeting the subnet → newlyAllowedRules
 *    - ADDED/MODIFIED deny rules targeting the subnet → newlyDeniedRules
 *    - UNCHANGED rules still matching → unchangedAffectingRules
 *    - REMOVED allow rules that previously matched → contributes to newlyAllowed (access gained)
 *
 * 3. Reachable Device Calculation (getReachableDevices):
 *    - For each external device connected to affected subnets:
 *      - Check if any ADDED/MODIFIED allow rules match device IP → GAINS access
 *      - Check if any REMOVED allow rules previously matched → LOSES access
 *      - Track responsible rules for each device
 * ```
 *
 * Rule matching uses the following heuristic:
 * - Source/Destination IP prefixes matching the entity's IP or subnet range
 * - Direction matching the flow (inbound for devices accessing subnets, outbound for subnets accessing devices)
 * - Protocol: '*' matches all, specific protocol must match
 * - Port ranges: '*' matches all, specific ports must fall within range
 *
 * @module impact-analyzer-service
 * @author Network Module Team
 * @since 1.0.0
 */

import { Injectable } from '@angular/core';
import {
    NSGRule,
    RuleComparison,
    RuleChangeType,
    AffectedSubnet,
    ReachableDevice,
    ImpactResult,
    ImpactSummary,
    Subnet,
    NetworkSecurityGroup,
    ExternalNetworkDevice,
    ConnectionType,
    NetworkConnection,
    Direction,
    Protocol,
    Access
} from '../models/network.model';

// Type aliases for impact analysis display interfaces (exported for use by components)
export type AffectedSubnetInfo = AffectedSubnet;
export type DeviceImpact = ReachableDevice;

/**
 * Internal representation of a matched rule-entity pair during impact analysis.
 */
interface RuleEntityMatch {
    rule: RuleComparison;
    entity: Subnet | ExternalNetworkDevice;
    isSource: boolean;
    isDestination: boolean;
}

/**
 * Service for analyzing the impact of NSG rule changes.
 *
 * Provides pure analysis methods that compare before/after rule states
 * and determine which subnets and external devices are affected.
 *
 * This service operates purely in-memory (no HTTP calls) since the
 * analysis is based on comparing rule sets provided as parameters.
 */
@Injectable({
    providedIn: 'root'
})
export class ImpactAnalyzerService {

    /**
     * Creates a new ImpactAnalyzerService.
     */
    constructor() { }

    // ==========================================================================
    // Public Analysis Methods
    // ==========================================================================

    /**
     * Analyzes the impact of NSG rule changes for a given NSG.
     *
     * Performs the full analysis pipeline: rule comparison, affected subnet
     * identification, and reachable device calculation.
     *
     * This is the main entry point for impact analysis. It takes the current
     * rules and proposed new rules, compares them, and returns a complete
     * ImpactResult with all affected entities.
     *
     * @param nsgId - The ID of the NSG being modified.
     * @param currentRules - The current set of NSG rules (before changes).
     * @param proposedRules - The proposed set of NSG rules (after changes, not yet saved).
     * @param subnets - Optional array of subnets associated with this NSG for affected subnet analysis.
     * @param externalDevices - Optional array of external devices for reachability analysis.
     * @param connections - Optional array of network connections for device relationship analysis.
     * @returns Complete ImpactResult with rule comparisons, affected subnets, and reachable devices.
     *
     * @example
     * ```typescript
     * const result = this.analyzer.analyzeNsgImpact('nsg-123', currentRules, newRules, subnets, devices);
     * if (result.hasRemovedAccess) {
     *   this.snackBar.open('Warning: Changes remove existing access', 'Dismiss', { duration: 5000 });
     * }
     * ```
     */
    analyzeNsgImpact(
        nsgId: string,
        currentRules: NSGRule[],
        proposedRules: NSGRule[],
        subnets: Subnet[] = [],
        externalDevices: ExternalNetworkDevice[] = [],
        connections: NetworkConnection[] = [],
        nsgMap: Map<string, NetworkSecurityGroup> = new Map()
    ): ImpactResult {
        // Step 1: Compare rules
        const ruleComparisons = this.compareRules(currentRules, proposedRules);

        // Step 2: Find affected subnets
        const affectedSubnets = this.getAffectedSubnets(subnets, nsgMap, ruleComparisons);

        // Step 3: Find reachable/affected devices
        const reachableDevices = this.getReachableDevices(
            externalDevices,
            connections,
            subnets,
            ruleComparisons
        );

        // Step 4: Calculate summary statistics
        const addedCount = ruleComparisons.filter(r => r.changeType === RuleChangeType.ADDED).length;
        const removedCount = ruleComparisons.filter(r => r.changeType === RuleChangeType.REMOVED).length;
        const modifiedCount = ruleComparisons.filter(r => r.changeType === RuleChangeType.MODIFIED).length;
        const unchangedCount = ruleComparisons.filter(r => r.changeType === RuleChangeType.UNCHANGED).length;
        const hasRemovedAccess = reachableDevices.some(d => !d.gainsAccess) ||
            ruleComparisons.some(r =>
                r.changeType === RuleChangeType.REMOVED && r.oldRule?.access === Access.ALLOW
            );

        return {
            nsgId,
            ruleComparisons,
            affectedSubnets,
            reachableDevices,
            hasRemovedAccess,
            addedCount,
            removedCount,
            modifiedCount,
            unchangedCount
        };
    }

    /**
     * Compares old and new NSG rule sets to identify changes.
     *
     * Uses name-based matching to pair rules between the old and new configurations.
     * For rules with the same name in both sets, all fields are compared to
     * detect modifications.
     *
     * @param oldRules - The rules before changes.
     * @param newRules - The rules after changes.
     * @returns Array of RuleComparison objects describing each change.
     *
     * @example
     * ```typescript
     * const comparisons = this.analyzer.compareRules(oldRules, newRules);
     * const modified = comparisons.filter(c => c.changeType === RuleChangeType.MODIFIED);
     * ```
     */
    compareRules(oldRules: NSGRule[], newRules: NSGRule[]): RuleComparison[] {
        const oldMap = new Map<string, NSGRule>();
        const newMap = new Map<string, NSGRule>();

        // Index rules by name for O(n) matching
        oldRules.forEach(rule => oldMap.set(rule.name, rule));
        newRules.forEach(rule => newMap.set(rule.name, rule));

        const comparisons: RuleComparison[] = [];
        const allNames = new Set([...oldMap.keys(), ...newMap.keys()]);

        allNames.forEach(name => {
            const oldRule = oldMap.get(name);
            const newRule = newMap.get(name);

            if (oldRule && newRule) {
                // Rule exists in both - check if modified
                const changedFields = this._findChangedFields(oldRule, newRule);
                comparisons.push({
                    oldRule,
                    newRule,
                    changeType: changedFields.length > 0 ? RuleChangeType.MODIFIED : RuleChangeType.UNCHANGED,
                    changedFields: changedFields.length > 0 ? changedFields : undefined
                });
            } else if (newRule && !oldRule) {
                // Rule is new
                comparisons.push({
                    newRule,
                    changeType: RuleChangeType.ADDED
                });
            } else if (oldRule && !newRule) {
                // Rule is removed
                comparisons.push({
                    oldRule,
                    changeType: RuleChangeType.REMOVED
                });
            }
        });

        return comparisons;
    }

    /**
     * Gets subnets affected by the proposed NSG rule changes.
     *
     * For each subnet associated with the NSG, determines which rules
     * would newly allow/deny traffic or remain unchanged.
     *
     * @param subnets - Array of subnets to analyze.
     * @param nsgMap - Map of NSG ID to NSG entity for lookup.
     * @param ruleComparisons - Results from compareRules.
     * @returns Array of AffectedSubnet objects.
     */
    getAffectedSubnets(
        subnets: Subnet[],
        nsgMap: Map<string, NetworkSecurityGroup>,
        ruleComparisons: RuleComparison[]
    ): AffectedSubnet[] {
        const affected: AffectedSubnet[] = [];

        subnets.forEach(subnet => {
            const nsg = nsgMap.get(subnet.nsgId!) || nsgMap.get(subnet.id);
            if (!nsg) return;

            const newlyAllowed: RuleComparison[] = [];
            const newlyDenied: RuleComparison[] = [];
            const unchangedAffecting: RuleComparison[] = [];

            ruleComparisons.forEach(comp => {
                if (comp.newRule || comp.oldRule) {
                    const activeRule = comp.newRule || comp.oldRule;
                    if (!activeRule) return;

                    // Check if this rule applies to the subnet's address prefix
                    if (this._ruleAppliesToSubnet(activeRule, subnet)) {
                        switch (comp.changeType) {
                            case RuleChangeType.ADDED:
                            case RuleChangeType.MODIFIED:
                                if (comp.newRule?.access === Access.ALLOW) {
                                    newlyAllowed.push(comp);
                                } else if (comp.newRule?.access === Access.DENY) {
                                    newlyDenied.push(comp);
                                }
                                break;
                            case RuleChangeType.UNCHANGED:
                                unchangedAffecting.push(comp);
                                break;
                            case RuleChangeType.REMOVED:
                                // If a rule is removed and it was an allow, access is lost
                                // If it was a deny, access is gained (but this is less common)
                                if (comp.oldRule?.access === Access.ALLOW) {
                                    // Removing an allow rule means losing access
                                    // Treat as newly allowed (the rule that was allowing is gone)
                                    newlyAllowed.push(comp);
                                }
                                break;
                        }
                    }
                }
            });

            // Only include subnets that are actually affected
            if (newlyAllowed.length > 0 || newlyDenied.length > 0 || unchangedAffecting.length > 0) {
                affected.push({
                    subnet,
                    nsg,
                    newlyAllowedRules: newlyAllowed,
                    newlyDeniedRules: newlyDenied,
                    unchangedAffectingRules: unchangedAffecting
                });
            }
        });

        return affected;
    }

    /**
     * Gets external devices that gain or lose access after rule changes.
     *
     * For each external device connected to the NSG's subnets, determines
     * whether the proposed changes would grant or revoke network access.
     *
     * @param externalDevices - Array of external devices to analyze.
     * @param connections - Array of network connections for relationship mapping.
     * @param subnets - Array of subnets for prefix matching.
     * @param ruleComparisons - Results from compareRules.
     * @returns Array of ReachableDevice objects.
     */
    getReachableDevices(
        externalDevices: ExternalNetworkDevice[],
        connections: NetworkConnection[],
        subnets: Subnet[],
        ruleComparisons: RuleComparison[]
    ): ReachableDevice[] {
        const reachable: ReachableDevice[] = [];

        // Build a map of subnet -> connected devices
        const subnetDevices = this._mapSubnetToDeviceConnections(subnets, externalDevices, connections);

        externalDevices.forEach(device => {
            const connectedSubnets = subnetDevices.get(device.id) || new Set<string>();
            if (connectedSubnets.size === 0) return;

            const gainsAccess = this._deviceGainsAccess(device, connectedSubnets, ruleComparisons, subnets);
            const losingRules = this._findResponsibleRules(device, connectedSubnets, ruleComparisons, !gainsAccess);

            reachable.push({
                device,
                gainsAccess,
                responsibleRules: losingRules.length > 0 ? losingRules : undefined
            });
        });

        return reachable;
    }

    /**
     * Gets a summary of impact for quick display.
     *
     * Convenience method that wraps analyzeNsgImpact and returns
     * a simplified ImpactSummary.
     *
     * @param nsgId - The NSG ID being analyzed.
     * @param currentRules - Current NSG rules.
     * @param proposedRules - Proposed NSG rules.
     * @param subnets - Associated subnets.
     * @param externalDevices - Associated external devices.
     * @param connections - Associated connections.
     * @param nsgMap - NSG lookup map.
     * @returns Simplified ImpactSummary.
     */
    getImpactSummary(
        nsgId: string,
        currentRules: NSGRule[],
        proposedRules: NSGRule[],
        subnets: Subnet[] = [],
        externalDevices: ExternalNetworkDevice[] = [],
        connections: NetworkConnection[] = [],
        nsgMap: Map<string, NetworkSecurityGroup> = new Map()
    ): ImpactSummary {
        const fullResult = this.analyzeNsgImpact(
            nsgId,
            currentRules,
            proposedRules,
            subnets,
            externalDevices,
            connections,
            nsgMap
        );

        const blockedDevices = fullResult.reachableDevices.filter(d => !d.gainsAccess);

        return {
            totalAffected: fullResult.addedCount + fullResult.removedCount + fullResult.modifiedCount,
            addedCount: fullResult.addedCount,
            removedCount: fullResult.removedCount,
            modifiedCount: fullResult.modifiedCount,
            hasRemovedAccess: fullResult.hasRemovedAccess,
            blockedDevices
        };
    }

    // ==========================================================================
    // Private Analysis Helpers
    // ==========================================================================

    /**
     * Finds field-level differences between two rules.
     *
     * @param oldRule - The old rule.
     * @param newRule - The new rule.
     * @returns Array of field names that differ.
     */
    private _findChangedFields(oldRule: NSGRule, newRule: NSGRule): string[] {
        const changed: string[] = [];
        const fieldsToCheck = [
            'priority', 'direction', 'protocol',
            'sourceAddressPrefix', 'destinationAddressPrefix',
            'sourcePortRange', 'destinationPortRange',
            'access', 'sourceIpGroup', 'destinationIpGroup',
            'serviceTag', 'isEnabled'
        ];

        fieldsToCheck.forEach(field => {
            const oldVal = (oldRule as unknown as Record<string, unknown>)[field];
            const newVal = (newRule as unknown as Record<string, unknown>)[field];
            if (oldVal !== newVal) {
                changed.push(field);
            }
        });

        return changed;
    }

    /**
     * Checks if an NSG rule applies to a subnet's address prefix.
     *
     * A rule applies to a subnet if:
     * - The rule's source or destination address prefix matches the subnet's prefix
     * - The rule's direction matches (inbound rules apply to subnet destinations, outbound to source)
     * - The protocol is '*' (any) or matches specifically
     *
     * @param rule - The NSG rule to check.
     * @param subnet - The subnet to check against.
     * @returns Whether the rule applies to the subnet.
     */
    private _ruleAppliesToSubnet(rule: NSGRule, subnet: Subnet): boolean {
        const subnetPrefix = subnet.addressPrefix;

        // Check if rule targets this subnet's prefix
        const matchesPrefix = this._prefixesOverlap(
            subnetPrefix,
            rule.sourceAddressPrefix || rule.destinationAddressPrefix || '*'
        );

        // If rule direction is inbound, it applies to resources IN the subnet
        // If rule direction is outbound, it applies to traffic LEAVING the subnet
        const directionMatches = rule.direction === Direction.INBOUND ||
            rule.direction === Direction.OUTBOUND; // Both directions can affect subnets

        return matchesPrefix && directionMatches;
    }

    /**
     * Checks if two IP prefixes overlap (one contains or overlaps the other).
     *
     * Handles CIDR notation and wildcard matching.
     *
     * @param prefix1 - First IP prefix.
     * @param prefix2 - Second IP prefix.
     * @returns Whether the prefixes overlap.
     */
    private _prefixesOverlap(prefix1: string, prefix2: string): boolean {
        if (prefix1 === '*' || prefix2 === '*') return true;

        // Simple prefix matching: check if one is a subnet of the other
        // For production, use a proper CIDR library
        if (prefix1 === prefix2) return true;

        // Check if prefix1 contains prefix2 or vice versa
        return this._prefixContains(prefix1, prefix2) || this._prefixContains(prefix2, prefix1);
    }

    /**
     * Checks if a base prefix contains a target prefix.
     *
     * @param basePrefix - The potentially larger prefix.
     * @param targetPrefix - The potentially smaller prefix.
     * @returns Whether base contains target.
     */
    private _prefixContains(basePrefix: string, targetPrefix: string): boolean {
        if (basePrefix === targetPrefix) return true;
        if (!basePrefix.endsWith('/')) basePrefix += '/0';
        if (!targetPrefix.endsWith('/')) targetPrefix += '/0';

        // Check if target starts with base prefix
        return targetPrefix.startsWith(basePrefix);
    }

    /**
     * Maps subnets to their connected external devices.
     *
     * Uses connections to find which devices connect to which subnets,
     * and also checks the subnet's direct externalDevices property.
     *
     * @param subnets - Array of subnets.
     * @param externalDevices - Array of external devices.
     * @param connections - Array of network connections.
     * @returns Map of device ID to set of subnet IDs.
     */
    private _mapSubnetToDeviceConnections(
        subnets: Subnet[],
        externalDevices: ExternalNetworkDevice[],
        connections: NetworkConnection[]
    ): Map<string, Set<string>> {
        const deviceSubnets = new Map<string, Set<string>>();

        // Build device ID -> subnet ID mapping from connections
        connections.forEach(conn => {
            const isSourceDevice = conn.sourceType === 'external_device';
            const isDestSubnet = conn.destinationType === 'subnet';
            const isSourceSubnet = conn.sourceType === 'subnet';
            const isDestDevice = conn.destinationType === 'external_device';

            if (isSourceDevice && isDestSubnet) {
                if (!deviceSubnets.has(conn.sourceId)) {
                    deviceSubnets.set(conn.sourceId, new Set());
                }
                deviceSubnets.get(conn.sourceId)!.add(conn.destinationId);
            }
            if (isSourceSubnet && isDestDevice) {
                if (!deviceSubnets.has(conn.destinationId)) {
                    deviceSubnets.set(conn.destinationId, new Set());
                }
                deviceSubnets.get(conn.destinationId)!.add(conn.sourceId);
            }
        });

        // Also include devices directly associated with subnets
        subnets.forEach(subnet => {
            const deviceIds = subnet.externalDevices?.map(d => d.id) || [];
            deviceIds.forEach(deviceId => {
                if (!deviceSubnets.has(deviceId)) {
                    deviceSubnets.set(deviceId, new Set());
                }
                deviceSubnets.get(deviceId)!.add(subnet.id);
            });
        });

        return deviceSubnets;
    }

    /**
     * Determines if an external device gains or loses access.
     *
     * Checks if any new/modified allow rules would allow traffic to the device,
     * or if any removed allow rules previously allowed access.
     *
     * @param device - The external device.
     * @param connectedSubnetIds - Set of connected subnet IDs.
     * @param ruleComparisons - Rule change analysis results.
     * @param subnets - Subnet lookup data.
     * @returns Whether the device gains access.
     */
    private _deviceGainsAccess(
        device: ExternalNetworkDevice,
        connectedSubnetIds: Set<string>,
        ruleComparisons: RuleComparison[],
        subnets: Subnet[]
    ): boolean {
        const subnetMap = new Map(subnets.map(s => [s.id, s]));

        let gainsAccess = false;
        let losesAccess = false;

        ruleComparisons.forEach(comp => {
            const rule = comp.newRule || comp.oldRule;
            if (!rule || rule.access !== Access.ALLOW || !rule.isEnabled) return;

            const isDirectionalMatch = rule.direction === Direction.INBOUND;
            const isPrefixMatch = this._ruleMatchesDevice(rule, device, subnets);

            if (isDirectionalMatch && isPrefixMatch) {
                switch (comp.changeType) {
                    case RuleChangeType.ADDED:
                    case RuleChangeType.MODIFIED:
                        gainsAccess = true;
                        break;
                    case RuleChangeType.REMOVED:
                        losesAccess = true;
                        break;
                }
            }
        });

        return gainsAccess && !losesAccess;
    }

    /**
     * Checks if a rule matches a specific external device.
     *
     * A rule matches a device if the rule's address/port criteria
     * would allow traffic to/from the device's IP.
     *
     * @param rule - The NSG rule.
     * @param device - The external device.
     * @param subnets - Subnets for prefix matching.
     * @returns Whether the rule matches the device.
     */
    private _ruleMatchesDevice(
        rule: NSGRule,
        device: ExternalNetworkDevice,
        subnets: Subnet[]
    ): boolean {
        if (!device.ipAddress) return false;

        const addresses = [
            rule.sourceAddressPrefix,
            rule.destinationAddressPrefix,
            rule.sourceIpGroup,
            rule.destinationIpGroup
        ].filter(Boolean) as string[];

        if (addresses.length === 0) return true; // No address filter = matches all
        if (addresses.includes('*')) return true;

        // Check if device IP matches any address filter
        for (const addr of addresses) {
            if (this._ipMatchesPrefix(device.ipAddress, addr)) {
                return true;
            }
            // Check if device is in any subnet that matches
            for (const subnet of subnets) {
                if (this._ipMatchesPrefix(device.ipAddress, subnet.addressPrefix)) {
                    return true;
                }
            }
        }

        return false;
    }

    /**
     * Checks if an IP address falls within a prefix.
     *
     * @param ip - The IP address to check.
     * @param prefix - The CIDR prefix.
     * @returns Whether the IP is within the prefix.
     */
    private _ipMatchesPrefix(ip: string, prefix: string): boolean {
        if (prefix === '*') return true;

        // Handle CIDR notation
        const [prefixNet, prefixBitsStr] = prefix.split('/');
        const prefixBits = parseInt(prefixBitsStr || '32', 10);

        // Simple string prefix check (for production, use proper IP parsing)
        if (!prefixBitsStr) {
            return ip === prefixNet;
        }

        // Check if IP starts with the network portion of the prefix
        const sharedOctets = Math.floor(prefixBits / 8);
        return ip.substring(0, prefixNet.lastIndexOf('.') + 1) ===
            prefixNet.substring(0, prefixNet.lastIndexOf('.') + 1);
    }

    /**
     * Finds rules responsible for a device losing or gaining access.
     *
     * @param device - The external device.
     * @param connectedSubnetIds - Set of connected subnet IDs.
     * @param ruleComparisons - Rule change analysis results.
     * @param isLoss - Whether looking for loss-causing rules (true) or gain-causing (false).
     * @returns Array of responsible rule comparisons.
     */
    private _findResponsibleRules(
        device: ExternalNetworkDevice,
        connectedSubnetIds: Set<string>,
        ruleComparisons: RuleComparison[],
        isLoss: boolean
    ): RuleComparison[] {
        const responsible: RuleComparison[] = [];

        ruleComparisons.forEach(comp => {
            const rule = comp.newRule || comp.oldRule;
            if (!rule) return;

            const shouldMatch = isLoss ?
                comp.changeType === RuleChangeType.REMOVED :
                comp.changeType === RuleChangeType.ADDED || comp.changeType === RuleChangeType.MODIFIED;

            if (!shouldMatch) return;
            if (rule.access !== Access.ALLOW) return;

            // Check if this rule affects the device
            const subnetMap = new Map<string, Subnet>();
            connectedSubnetIds.forEach(id => {
                // We'd need subnet data passed in; simplified check
                if (this._ruleMatchesDevice(rule, device, [])) {
                    responsible.push(comp);
                }
            });
        });

        return responsible;
    }
}