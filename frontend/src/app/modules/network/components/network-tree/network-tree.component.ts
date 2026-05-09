/**
 * Network Tree Component
 *
 * Displays the network topology as a hierarchical MatTree with the following structure:
 *   Virtual Network
 *     └── Subnet 1
 *           └── NSG (attached to subnet)
 *                 └── Rule 1
 *                 └── Rule 2
 *           └── NSG 2
 *                 └── Rule A
 *     └── Subnet 2
 *           └── NSG 3
 *     └── External Device 1
 *
 * Each leaf node is clickable for editing. Supports expand/collapse all,
 * search highlighting, node count badges, and a right-click context menu.
 *
 * @module network-tree-component
 * @author Network Module Team
 * @since 1.0.0
 */

import {
    Component,
    OnInit,
    OnDestroy,
    ChangeDetectionStrategy,
    ViewEncapsulation,
    EventEmitter,
    Output,
    AfterViewInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTreeModule } from '@angular/material/tree';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { Subject, takeUntil, debounceTime } from 'rxjs';
import {
    TopologyGraph,
    TopologyNode,
    NodeType,
    VirtualNetwork,
    Subnet,
    NetworkSecurityGroup,
    NSGRule,
    ExternalNetworkDevice,
    NODE_TYPE_LABELS,
} from '../../models/network.model';

// ============================================================================
// Tree data model types
// ============================================================================

/**
 * Flat node representing a single item in the tree (with expand/collapse state).
 * Used with MatTreeFlattener to build a hierarchical tree view.
 */
export class TreeFlatNode {
    constructor(
        public label: string,
        public level: number,
        public expandable: boolean,
        public type: NodeType,
        public data: VirtualNetwork | Subnet | NetworkSecurityGroup | NSGRule | ExternalNetworkDevice,
        public children?: TreeFlatNode[]
    ) { }
}

// ============================================================================
// Component
// ============================================================================

/**
 * Tree-based hierarchy view of the network topology.
 *
 * @selector app-network-tree
 * @standalone
 */
@Component({
    selector: 'app-network-tree',
    templateUrl: './network-tree.component.html',
    styleUrls: ['./network-tree.component.css'],
    changeDetection: ChangeDetectionStrategy.OnPush,
    encapsulation: ViewEncapsulation.None,
    imports: [
        CommonModule,
        MatTreeModule,
        MatInputModule,
        MatFormFieldModule,
        MatButtonModule,
        MatIconModule,
        MatChipsModule,
        MatMenuModule,
        MatDividerModule,
    ],
    standalone: true,
})
export class NetworkTreeComponent implements OnInit, OnDestroy, AfterViewInit {
    private destroy$ = new Subject<void>();

    /** Output emitted when a user selects a node for editing. */
    @Output() nodeAction = new EventEmitter<{ nodeId: string; action: string }>();

    /** Output emitted when a node is double-clicked. */
    @Output() nodeSelected = new EventEmitter<TopologyNode>();

    /** The full topology data loaded from the API. */
    public topologyData: TopologyGraph | null = null;

    /** Expanded flat nodes for the MatTree (MatTreeFlattener output). */
    public expandedFlatNodes: TreeFlatNode[] = [];

    /** Search query string entered by the user. */
    public searchQuery: string = '';

    /** Filter by node type ('all', 'virtual_network', 'subnet', 'nsg', etc.). */
    public filterType: string = 'all';

    /** Filter by location. */
    public filterLocation: string = '';

    /** Count of nodes displayed after filtering. */
    public filteredNodeCount = 0;

    /** Context menu position for right-click actions. */
    public contextMenuX = 0;
    public contextMenuY = 0;
    public contextMenuNode: TreeFlatNode | null = null;

    /**
     * Creates a new NetworkTreeComponent.
     */
    constructor() { }

    /**
     * Lifecycle hook called after project initialization.
     */
    ngOnInit(): void {
        // Topology data should be set by parent component
    }

    /**
     * Lifecycle hook called after view initialization.
     * Used to subscribe to search input changes with debounce.
     */
    ngAfterViewInit(): void {
        // Search handling via template (ngModel with (ngModelChange))
    }

    /**
     * Lifecycle hook called before component destruction.
     * Cleans up all subscriptions.
     */
    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    /**
     * Set the topology data and build the flat tree.
     *
     * @param data - The topology graph to render.
     */
    public setTopologyData(data: TopologyGraph | null): void {
        this.topologyData = data;
        const flatNodes = this._buildFlatNodes(data);
        this.expandedFlatNodes = flatNodes;
        this._updateFilteredCount(flatNodes);
    }

    /**
     * Build the flat tree node array from the topology graph.
     *
     * The tree structure is: VNet → [Subnets, NSGs, External Devices] → NSG → Rules
     *
     * @param data - The topology graph.
     * @returns Array of flat tree nodes.
     *
     * @private
     */
    private _buildFlatNodes(data: TopologyGraph | null): TreeFlatNode[] {
        if (!data || !data.nodes.length) return [];

        // Separate nodes by type for efficient querying
        const vnets = data.nodes.filter((n) => n.type === NodeType.VIRTUAL_NETWORK) as Array<TopologyNode & { data: VirtualNetwork }>;
        const subnets = data.nodes.filter((n) => n.type === NodeType.SUBNET) as Array<TopologyNode & { data: Subnet }>;
        const nsgs = data.nodes.filter((n) => n.type === NodeType.NSG) as Array<TopologyNode & { data: NetworkSecurityGroup }>;
        const rules = data.nodes.filter((n) => n.type === NodeType.NSG_RULE) as Array<TopologyNode & { data: NSGRule }>;
        const externalDevices = data.nodes.filter((n) => n.type === NodeType.EXTERNAL_DEVICE) as Array<TopologyNode & { data: ExternalNetworkDevice }>;

        const result: TreeFlatNode[] = [];

        // Build VNet tree
        for (const vnetRaw of vnets) {
            const vnData = vnetRaw.data as VirtualNetwork;
            const vnId = vnData.id;

            // Get subnets for this VNet
            const vnSubnets = subnets.filter((sn) => (sn.data as Subnet).vnetId === vnId);

            // Get NSGs for this VNet
            const vnNsgs = nsgs.filter((nsg) => (nsg.data as NetworkSecurityGroup).vnetId === vnId);

            // Get external devices for this VNet (not associated with subnets)
            const vnExtDevices = externalDevices.filter((ed) => {
                const edData = ed.data as ExternalNetworkDevice;
                return !edData.subnets || edData.subnets.length === 0;
            });

            // Build subnet children with NSG and rule children
            const subnetNodes: TreeFlatNode[] = vnSubnets.map((sn) => {
                const snData = sn.data as Subnet;
                const subnetChildren: TreeFlatNode[] = [];

                // NSGs attached to this subnet
                const subnetNsgs = vnNsgs.filter((nsg) => true); // All NSGs for this VNet

                for (const nsgNode of subnetNsgs) {
                    const nsgData = nsgNode.data as NetworkSecurityGroup;
                    // Get rules for this NSG
                    const nsgRules = rules.filter((r) => (r.data as NSGRule).nsgId === nsgData.id);

                    const ruleNodes: TreeFlatNode[] = nsgRules.map((r) => {
                        const ruleData = r.data as NSGRule;
                        return new TreeFlatNode(
                            `📋 ${ruleData.name} [${ruleData.access === 'allow' ? '✓' : '✗'}]`,
                            3,
                            false,
                            NodeType.NSG_RULE,
                            ruleData
                        );
                    });

                    const nsgWithChildren = new TreeFlatNode(
                        `🛡️ ${nsgData.name}`,
                        2,
                        ruleNodes.length > 0,
                        NodeType.NSG,
                        nsgData,
                        ruleNodes
                    );
                    subnetChildren.push(nsgWithChildren);
                }

                const subnetNode = new TreeFlatNode(
                    `📦 ${snData.name} (${snData.addressPrefix})`,
                    1,
                    subnetChildren.length > 0,
                    NodeType.SUBNET,
                    snData,
                    subnetChildren
                );
                return subnetNode;
            });

            // External device children
            const extDeviceNodes: TreeFlatNode[] = vnExtDevices.map((ed) => {
                const edData = ed.data as ExternalNetworkDevice;
                return new TreeFlatNode(
                    `🔌 ${edData.name}`,
                    1,
                    false,
                    NodeType.EXTERNAL_DEVICE,
                    edData
                );
            });

            // Top-level NSG children (not attached to subnets)
            const topLevelNsgNodes: TreeFlatNode[] = vnNsgs.map((nsgNode) => {
                const nsgData = nsgNode.data as NetworkSecurityGroup;
                const nsgRules = rules.filter((r) => (r.data as NSGRule).nsgId === nsgData.id);

                const ruleNodes: TreeFlatNode[] = nsgRules.map((r) => {
                    const ruleData = r.data as NSGRule;
                    return new TreeFlatNode(
                        `📋 ${ruleData.name} [${ruleData.access === 'allow' ? '✓' : '✗'}]`,
                        2,
                        false,
                        NodeType.NSG_RULE,
                        ruleData
                    );
                });

                return new TreeFlatNode(
                    `🛡️ ${nsgData.name}`,
                    1,
                    ruleNodes.length > 0,
                    NodeType.NSG,
                    nsgData,
                    ruleNodes
                );
            });

            // Combine all children for VNet
            const vnetChildren: TreeFlatNode[] = [
                ...subnetNodes,
                ...topLevelNsgNodes,
                ...extDeviceNodes,
            ];

            const vnetTree = new TreeFlatNode(
                `🌐 ${vnData.name} [${vnetChildren.length} nodes]`,
                0,
                true,
                NodeType.VIRTUAL_NETWORK,
                vnData,
                vnetChildren
            );
            result.push(vnetTree);
        }

        return result;
    }

    /**
     * Handle search input changes with debouncing.
     * Filters tree nodes by name matching.
     */
    onSearchInput(): void {
        this._applyFilter();
    }

    /**
     * Apply current filters to the tree data.
     * Filters by search query (substring match on node label), node type, and location.
     *
     * @private
     */
    private _applyFilter(): void {
        if (!this.topologyData) return;

        const query = this.searchQuery.toLowerCase().trim();

        // Filter the top-level VNets and their children
        const vnets = this.topologyData.nodes.filter((n) => n.type === NodeType.VIRTUAL_NETWORK) as Array<TopologyNode & { data: VirtualNetwork }>;

        const filteredVnets = vnets.filter((vn) => {
            const vnData = vn.data;
            // Search query
            if (query && !vnData.name.toLowerCase().includes(query)) return false;
            // Type filter
            if (this.filterType !== 'all' && this.filterType !== NodeType.VIRTUAL_NETWORK) {
                // Check if any children match the filter
                return this._childrenMatchFilter(vn, query);
            }
            // Location filter
            if (this.filterLocation && !vnData.location?.toLowerCase().includes(this.filterLocation.toLowerCase())) return false;
            return true;
        });

        this.filteredNodeCount = filteredVnets.length;
    }

    /**
     * Check if a VNet has children matching the current filter.
     *
     * @param vnetNode - The VNet topology node.
     * @param query - The search query.
     * @returns true if any children match the filter criteria.
     *
     * @private
     */
    private _childrenMatchFilter(vnetNode: TopologyNode & { data: VirtualNetwork }, query: string): boolean {
        const vnId = vnetNode.data.id;

        // Check subnets
        const subnets = this.topologyData?.nodes.filter((n) => n.type === NodeType.SUBNET) as Array<TopologyNode & { data: Subnet }> || [];
        for (const sn of subnets) {
            if ((sn.data as Subnet).vnetId === vnId) {
                const snData = sn.data as Subnet;
                if (query && !snData.name.toLowerCase().includes(query)) continue;
                if (this.filterType === NodeType.SUBNET || this.filterType === 'all') return true;
            }
        }

        // Check NSGs
        const nsgs = this.topologyData?.nodes.filter((n) => n.type === NodeType.NSG) as Array<TopologyNode & { data: NetworkSecurityGroup }> || [];
        for (const nsg of nsgs) {
            if ((nsg.data as NetworkSecurityGroup).vnetId === vnId) {
                if (query && !(nsg.data as NetworkSecurityGroup).name.toLowerCase().includes(query)) continue;
                if (this.filterType === NodeType.NSG || this.filterType === 'all') return true;
            }
        }

        return false;
    }

    /**
     * Update the filtered node count display.
     *
     * @param nodes - The filtered nodes array.
     *
     * @private
     */
    private _updateFilteredCount(nodes: TreeFlatNode[]): void {
        this.filteredNodeCount = nodes.length;
    }

    /**
     * Toggle expand/collapse all nodes in the tree.
     * Expands all nodes if collapsed, collapses all if expanded.
     */
    toggleExpandAll(): void {
        this.expandedFlatNodes.forEach((node) => {
            (node as any).expanded = !node.expandable;
        });
    }

    /**
     * Handle right-click context menu on a tree node.
     *
     * @param event - The mouse event.
     * @param node - The tree flat node.
     */
    onNodeContextMenu(event: MouseEvent, node: TreeFlatNode): void {
        event.preventDefault();
        this.contextMenuX = event.clientX;
        this.contextMenuY = event.clientY;
        this.contextMenuNode = node;
    }

    /**
     * Handle context menu action selection.
     *
     * @param action - The selected action name.
     */
    onContextMenuAction(action: string): void {
        if (!this.contextMenuNode) return;
        this.nodeAction.emit({
            nodeId: (this.contextMenuNode.data as any).id || '',
            action,
        });
        this.contextMenuNode = null;
    }

    /**
     * Handle node click events.
     *
     * @param node - The clicked tree flat node.
     */
    onNodeClick(node: TreeFlatNode): void {
        this.nodeAction.emit({
            nodeId: (node.data as any).id || '',
            action: 'select',
        });
    }

    /**
     * Handle node double-click events.
     *
     * @param node - The double-clicked tree flat node.
     */
    onNodeDblClick(node: TreeFlatNode): void {
        // Build a TopologyNode for the event emitter
        const topologyNode: TopologyNode = {
            id: (node.data as any).id || '',
            type: node.type,
            data: node.data,
            connections: [],
        };
        this.nodeSelected.emit(topologyNode);
    }

    /**
     * Get the display label for a node type.
     *
     * @param type - The node type enum.
     * @returns The human-readable label.
     */
    getNodeTypeLabel(type: NodeType): string {
        return NODE_TYPE_LABELS[type] || type;
    }

    /**
     * Track by function for template rendering performance.
     *
     * @param _index - The node index.
     * @param node - The tree flat node.
     * @returns The node's data id for stable identity.
     */
    /**
     * Get the Material color for a node type.
     *
     * @param type - The node type enum.
     * @returns The Material color name.
     *
     * @private
     */
    _getNodeTypeColor(type: NodeType): string {
        const colorMap: Partial<Record<NodeType, string>> = {
            [NodeType.VIRTUAL_NETWORK]: 'primary',
            [NodeType.SUBNET]: 'accent',
            [NodeType.NSG]: 'warn',
            [NodeType.NSG_RULE]: '',
            [NodeType.EXTERNAL_DEVICE]: 'primary',
            [NodeType.CONNECTION]: 'secondary',
        };
        return colorMap[type] || '';
    }

    /**
     * Track by function for template rendering performance.
     *
     * @param _index - The node index.
     * @param node - The tree flat node.
     * @returns The node's data id for stable identity.
     */
    trackByFn(_index: number, node: TreeFlatNode): string {
        return (node.data as any).id || `${node.type}-${node.label}`;
    }
}
