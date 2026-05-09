/**
 * Network Models
 *
 * TypeScript interfaces and types for the network topology module.
 * These interfaces mirror the backend SQLAlchemy models and FastAPI schemas
 * for Virtual Networks, Subnets, Network Security Groups (NSG), NSG Rules,
 * External Network Devices, and Network Connections.
 *
 * # Module Architecture
 *
 * ```
 * network/
 * ├── models/
 * │   └── network.model.ts    ← TypeScript interfaces for all network entities
 * ├── services/
 * │   └── network.service.ts  ← API communication layer
 * ├── components/
 * │   ├── topology-container.component.ts  ← Parent with view toggle
 * │   ├── network-tree.component.ts        ← MatTree hierarchy view
 * │   ├── network-graph.component.ts       ← SVG graph view
 * │   └── vnet-detail.component.ts         ← VNet detail view
 * ```
 *
 * @module network-models
 * @author Network Module Team
 */

// ============================================================================
// Enums
// ============================================================================

/** Traffic direction for NSG rules. */
export enum Direction {
    INBOUND = 'inbound',
    OUTBOUND = 'outbound'
}

/** Protocol types for NSG rules. */
export enum Protocol {
    TCP = 'TCP',
    UDP = 'UDP',
    ICMP = 'ICMP',
    AH = 'AH',
    ANY = '*'
}

/** Access action for NSG rules. */
export enum Access {
    ALLOW = 'allow',
    DENY = 'deny'
}

/** Types of external network devices. */
export enum DeviceType {
    ROUTER = 'router',
    SWITCH = 'switch',
    FIREWALL = 'firewall',
    OTHER = 'other'
}

/** Types of network connections. */
export enum ConnectionType {
    DIRECT = 'direct',
    VPN = 'vpn',
    EXPRESS_ROUTER = 'express_router',
    PEERING = 'peering',
    VPN_GATEWAY = 'vpn_gateway',
    CUSTOM = 'custom'
}

/** Sync status of an NSG with Azure. */
export enum SyncStatus {
    PENDING = 'pending',
    APPLIED = 'applied',
    FAILED = 'failed'
}

/** Node type for graph rendering. */
export enum NodeType {
    VIRTUAL_NETWORK = 'virtual_network',
    SUBNET = 'subnet',
    NSG = 'nsg',
    NSG_RULE = 'nsg_rule',
    EXTERNAL_DEVICE = 'external_device',
    CONNECTION = 'connection'
}

// ============================================================================
// Interfaces
// ============================================================================

/**
 * Represents an Azure Virtual Network.
 *
 * Virtual Networks are the fundamental networking construct containing
 * subnets, NSGs, and serving as the top-level grouping for network resources.
 */
export interface VirtualNetwork {
    id: string;
    name: string;
    addressSpace: string;
    location: string;
    resourceGroup: string;
    subscriptionId?: string;
    tags?: string;
    isSynced?: boolean;
    subnets?: Subnet[];
    nsgs?: NetworkSecurityGroup[];
    createdAt?: string;
    updatedAt?: string;
}

/**
 * Represents a subnet within a Virtual Network.
 *
 * Subnets are logical partitions of a virtual network address space.
 * Each subnet can contain resources and is associated with a Network
 * Security Group for traffic control.
 */
export interface Subnet {
    id: string;
    name: string;
    addressPrefix: string;
    vnetId: string;
    nsgId?: string;
    description?: string;
    tags?: string;
    isActive?: boolean;
    nsg?: NetworkSecurityGroup;
    externalDevices?: ExternalNetworkDevice[];
    createdAt?: string;
    updatedAt?: string;
}

/**
 * Represents a Network Security Group associated with a Virtual Network.
 *
 * NSGs contain rules that allow or deny network traffic. They can be
 * synced with Azure NSGs tracked via syncStatus.
 */
export interface NetworkSecurityGroup {
    id: string;
    name: string;
    location: string;
    vnetId: string;
    resourceGroup: string;
    subscriptionId?: string;
    tags?: string;
    syncStatus?: SyncStatus;
    azureNsgId?: string;
    lastSyncedAt?: string;
    rules?: NSGRule[];
    subnets?: Subnet[];
    connections?: NetworkConnection[];
    createdAt?: string;
    updatedAt?: string;
}

/**
 * Represents a rule within a Network Security Group.
 *
 * Each rule defines a priority, direction, protocol, source/destination
 * addresses/ports, and access action (allow/deny).
 */
export interface NSGRule {
    id: string;
    nsgId: string;
    name: string;
    priority: number;
    direction: Direction;
    protocol: Protocol;
    sourceAddressPrefix?: string;
    destinationAddressPrefix?: string;
    sourcePortRange?: string;
    destinationPortRange?: string;
    access: Access;
    sourceIpGroup?: string;
    destinationIpGroup?: string;
    serviceTag?: string;
    isEnabled?: boolean;
    createdAt?: string;
    updatedAt?: string;
}

/**
 * Represents an external network device in the topology.
 *
 * Physical or virtual devices such as routers, switches, firewalls,
 * or other network infrastructure that connect to or interact with
 * the virtual network.
 */
export interface ExternalNetworkDevice {
    id: string;
    name: string;
    ipAddress?: string;
    deviceType: DeviceType;
    vendor?: string;
    model?: string;
    serialNumber?: string;
    contactName?: string;
    contactEmail?: string;
    contactPhone?: string;
    notes?: string;
    tags?: string;
    isActive?: boolean;
    subnets?: Subnet[];
    createdAt?: string;
    updatedAt?: string;
}

/**
 * Represents a link in the network topology graph.
 *
 * Connections define how network entities relate to each other.
 * Each connection references a source and destination, each of which
 * can be a Subnet, NetworkSecurityGroup, or ExternalNetworkDevice.
 */
export interface NetworkConnection {
    id: string;
    sourceId: string;
    sourceType: string;
    destinationId: string;
    destinationType: string;
    connectionType: ConnectionType;
    description?: string;
    createdAt?: string;
}

/**
 * A node in the topology graph for rendering purposes.
 *
 * Aggregates entity data with connection metadata for the SVG graph view.
 */
export interface TopologyNode {
    id: string;
    type: NodeType;
    data: VirtualNetwork | Subnet | NetworkSecurityGroup | NSGRule | ExternalNetworkDevice;
    connections: TopologyEdge[];
    x?: number;
    y?: number;
}

/**
 * An edge connecting two topology nodes in the graph.
 */
export interface TopologyEdge {
    sourceId: string;
    targetId: string;
    connectionType?: ConnectionType;
    description?: string;
}

/**
 * Full topology graph structure returned from the API.
 */
export interface TopologyGraph {
    nodes: TopologyNode[];
    edges: TopologyEdge[];
}

// ============================================================================
// Request/Response DTOs
// ============================================================================

/** Request DTO for creating a Virtual Network. */
export interface CreateVnetRequest {
    name: string;
    addressSpace: string;
    location: string;
    resourceGroup: string;
    subscriptionId?: string;
    tags?: string;
}

/** Request DTO for creating a Subnet. */
export interface CreateSubnetRequest {
    name: string;
    addressPrefix: string;
    vnetId: string;
    nsgId?: string;
    description?: string;
    tags?: string;
}

/** Request DTO for creating an NSG. */
export interface CreateNsgRequest {
    name: string;
    location: string;
    vnetId: string;
    resourceGroup: string;
    subscriptionId?: string;
    tags?: string;
}

/** Request DTO for creating an NSG Rule. */
export interface CreateNsgRuleRequest {
    name: string;
    priority: number;
    direction: Direction;
    protocol: Protocol;
    sourceAddressPrefix?: string;
    destinationAddressPrefix?: string;
    sourcePortRange?: string;
    destinationPortRange?: string;
    access: Access;
    isEnabled?: boolean;
}

/** Request DTO for reordering NSG rules. */
export interface NsgRuleOrderRequest {
    ruleOrder: { nsgRuleId: string; position: number }[];
}

/** Request DTO for creating an External Network Device. */
export interface CreateExternalDeviceRequest {
    name: string;
    ipAddress?: string;
    deviceType: DeviceType;
    vendor?: string;
    model?: string;
    contactName?: string;
    contactEmail?: string;
    contactPhone?: string;
    notes?: string;
    tags?: string;
}

/** Request DTO for creating a Network Connection. */
export interface CreateConnectionRequest {
    sourceId: string;
    sourceType: string;
    destinationId: string;
    destinationType: string;
    connectionType: ConnectionType;
    description?: string;
}

/** Connection filters for the getConnections API method. */
export interface ConnectionFilters {
    sourceId?: string;
    sourceType?: string;
    destinationId?: string;
    destinationType?: string;
    connectionType?: ConnectionType;
}

// ============================================================================
// Display helpers
// ============================================================================

/** Display labels for node types in the graph legend. */
export const NODE_TYPE_LABELS: Record<NodeType, string> = {
    [NodeType.VIRTUAL_NETWORK]: 'Virtual Network',
    [NodeType.SUBNET]: 'Subnet',
    [NodeType.NSG]: 'NSG',
    [NodeType.NSG_RULE]: 'NSG Rule',
    [NodeType.EXTERNAL_DEVICE]: 'External Device',
    [NodeType.CONNECTION]: 'Connection'
};

/** Node styling configuration by type for the SVG graph. */
export const NODE_STYLES: Record<NodeType, { fillColor: string; strokeColor: string; shape: string; width: number; height: number }> = {
    [NodeType.VIRTUAL_NETWORK]: { fillColor: '#2196f3', strokeColor: '#1565c0', shape: 'rect', width: 180, height: 50 },
    [NodeType.SUBNET]: { fillColor: '#4caf50', strokeColor: '#2e7d32', shape: 'rect', width: 140, height: 40 },
    [NodeType.NSG]: { fillColor: '#ff9800', strokeColor: '#e65100', shape: 'diamond', width: 100, height: 100 },
    [NodeType.NSG_RULE]: { fillColor: '#ffeb3b', strokeColor: '#f57f17', shape: 'rect', width: 40, height: 30 },
    [NodeType.EXTERNAL_DEVICE]: { fillColor: '#f44336', strokeColor: '#b71c1c', shape: 'hexagon', width: 100, height: 100 },
    [NodeType.CONNECTION]: { fillColor: '#9c27b0', strokeColor: '#4a148c', shape: 'circle', width: 20, height: 20 }
};

/** Display labels for connection types. */
export const CONNECTION_TYPE_LABELS: Record<ConnectionType, string> = {
    [ConnectionType.DIRECT]: 'Direct',
    [ConnectionType.VPN]: 'VPN',
    [ConnectionType.EXPRESS_ROUTER]: 'ExpressRoute',
    [ConnectionType.PEERING]: 'Peering',
    [ConnectionType.VPN_GATEWAY]: 'VPN Gateway',
    [ConnectionType.CUSTOM]: 'Custom'
};

/** Display labels for device types. */
export const DEVICE_TYPE_LABELS: Record<DeviceType, string> = {
    [DeviceType.ROUTER]: 'Router',
    [DeviceType.SWITCH]: 'Switch',
    [DeviceType.FIREWALL]: 'Firewall',
    [DeviceType.OTHER]: 'Other'
};

/** Display labels for directions. */
export const DIRECTION_LABELS: Record<Direction, string> = {
    [Direction.INBOUND]: 'Inbound',
    [Direction.OUTBOUND]: 'Outbound'
};

/** Display labels for access types. */
export const ACCESS_LABELS: Record<Access, string> = {
    [Access.ALLOW]: 'Allow',
    [Access.DENY]: 'Deny'
};

/** Display labels for sync status. */
export const SYNC_STATUS_LABELS: Record<SyncStatus, string> = {
    [SyncStatus.PENDING]: 'Pending',
    [SyncStatus.APPLIED]: 'Applied',
    [SyncStatus.FAILED]: 'Failed'
};

// ============================================================================
// Impact Analysis Types
// ============================================================================

/**
 * Change type for an NSG rule during impact analysis.
 *
 * - 'added': Rule exists in new configuration but not in old
 * - 'removed': Rule existed in old configuration but not in new
 * - 'modified': Rule exists in both but with different properties
 * - 'unchanged': Rule is identical in both configurations
 */
export enum RuleChangeType {
    ADDED = 'added',
    REMOVED = 'removed',
    MODIFIED = 'modified',
    UNCHANGED = 'unchanged'
}

/**
 * Result of comparing a single NSG rule between before and after states.
 *
 * Used by the impact analysis algorithm to determine what changed
 * when NSG rules are modified.
 */
export interface RuleComparison {
    /** The rule from the old (before) configuration. */
    oldRule?: NSGRule;
    /** The rule from the new (after) configuration. */
    newRule?: NSGRule;
    /** The type of change detected. */
    changeType: RuleChangeType;
    /** List of specific fields that differ between old and new. */
    changedFields?: string[];
}

/**
 * Represents a subnet that is affected by NSG rule changes.
 *
 * Contains details about which specific rules impact this subnet
 * and in what way (newly allowed, newly denied, or unchanged).
 */
export interface AffectedSubnet {
    /** The subnet entity being affected. */
    subnet: Subnet;
    /** NSG associated with this subnet. */
    nsg?: NetworkSecurityGroup;
    /** Rules that newly allow traffic to this subnet after changes. */
    newlyAllowedRules?: RuleComparison[];
    /** Rules that newly deny traffic to this subnet after changes. */
    newlyDeniedRules?: RuleComparison[];
    /** Rules that affect this subnet but had no change. */
    unchangedAffectingRules?: RuleComparison[];
}

/**
 * Represents an external device that becomes reachable after NSG rule changes.
 *
 * Used to show which external devices gain or lose network access
 * based on the proposed NSG rule modifications.
 */
export interface ReachableDevice {
    /** The external network device entity. */
    device: ExternalNetworkDevice;
    /** Whether the device GAINS access (true) or LOSES access (false) after changes. */
    gainsAccess: boolean;
    /** The rules responsible for the new/removed access. */
    responsibleRules?: RuleComparison[];
}

/**
 * Complete result of an NSG impact analysis.
 *
 * Aggregates rule comparisons, affected subnets, and reachable devices
 * into a single result structure for the impact analysis dialog.
 */
export interface ImpactResult {
    /** The NSG ID being analyzed. */
    nsgId: string;
    /** Comparison of each rule between old and new configurations. */
    ruleComparisons: RuleComparison[];
    /** Subnets affected by the proposed rule changes. */
    affectedSubnets: AffectedSubnet[];
    /** External devices that gain or lose access after changes. */
    reachableDevices: ReachableDevice[];
    /** Whether any rules were removed that previously allowed access. */
    hasRemovedAccess: boolean;
    /** Summary count of added rules. */
    addedCount: number;
    /** Summary count of removed rules. */
    removedCount: number;
    /** Summary count of modified rules. */
    modifiedCount: number;
    /** Summary count of unchanged rules. */
    unchangedCount: number;
}

/**
 * Summary of impact for a quick-glance display.
 *
 * Used by the inline impact summary below the NSG rule editor table.
 */
export interface ImpactSummary {
    /** Total number of rules affected. */
    totalAffected: number;
    /** Number of rules being added. */
    addedCount: number;
    /** Number of rules being removed. */
    removedCount: number;
    /** Number of rules being modified. */
    modifiedCount: number;
    /** Whether the changes would remove existing access (warning condition). */
    hasRemovedAccess: boolean;
    /** List of devices that would lose access. */
    blockedDevices: ReachableDevice[];
}

/**
 * Input data passed to the impact analysis dialog.
 */
export interface ImpactAnalysisData {
    /** The NSG ID being analyzed. */
    nsgId: string;
    /** The NSG name for display. */
    nsgName?: string;
    /** NSG rules before the proposed changes. */
    oldRules: NSGRule[];
    /** NSG rules after the proposed changes (not yet saved). */
    newRules: NSGRule[];
}
