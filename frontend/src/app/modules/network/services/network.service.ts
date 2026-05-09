/**
 * Network Service
 *
 * Provides methods for managing network topology entities including Virtual Networks,
 * Subnets, Network Security Groups (NSG), NSG Rules, External Network Devices,
 * and Network Connections.
 *
 * # Features
 *
 * - **Topology Graph**: Fetch the complete network topology as a graph of nodes and edges
 * - **Virtual Networks**: CRUD operations for VNets
 * - **Subnets**: CRUD operations for subnets, scoped to a VNet
 * - **NSGs**: CRUD operations for Network Security Groups
 * - **NSG Rules**: CRUD operations with support for rule reordering
 * - **External Devices**: CRUD operations for external network devices
 * - **Connections**: CRUD operations for network connections between entities
 *
 * # Usage
 *
 * ```typescript
 * import { NetworkService } from './services/network.service';
 *
 * constructor(private networkService: NetworkService) { }
 *
 * // Get topology graph
 * this.networkService.getTopology().subscribe(graph => { ... });
 *
 * // Get all VNets
 * this.networkService.getVnets().subscribe(vnets => { ... });
 *
 * // Create a new VNet
 * this.networkService.createVnet(data).subscribe(vnet => { ... });
 * ```
 *
 * @module network-service
 * @author Network Module Team
 */

import { Injectable, NgZone } from '@angular/core';
import { HttpClient, HttpParams, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import {
    VirtualNetwork,
    Subnet,
    NetworkSecurityGroup,
    NSGRule,
    ExternalNetworkDevice,
    NetworkConnection,
    TopologyGraph,
    TopologyNode,
    TopologyEdge,
    NodeType,
    ConnectionType,
    Direction,
    Protocol,
    Access,
    DeviceType,
    SyncStatus,
    CreateVnetRequest,
    CreateSubnetRequest,
    CreateNsgRequest,
    CreateNsgRuleRequest,
    NsgRuleOrderRequest,
    CreateExternalDeviceRequest,
    CreateConnectionRequest,
    ConnectionFilters,
    NODE_STYLES,
    NODE_TYPE_LABELS
} from '../models/network.model';

/**
 * Base URL for network API endpoints.
 */
const NETWORK_API_BASE = '/api/v1/network';

/**
 * Service layer for all network topology operations.
 *
 * Provides CRUD operations for Virtual Networks, Subnets, NSGs, NSG Rules,
 * External Devices, and Network Connections. Also provides the topology
 * graph endpoint that aggregates all entities.
 */
@Injectable({
    providedIn: 'root'
})
export class NetworkService {

    /** Base URL for all network API endpoints. */
    private readonly baseUrl = NETWORK_API_BASE;

    /**
     * Creates a new NetworkService.
     *
     * @param http - Angular HTTP client for making API requests.
     */
    constructor(private http: HttpClient) { }

    // ==========================================================================
    // Topology Graph
    // ==========================================================================

    /**
     * Fetch the complete network topology graph.
     *
     * Returns all nodes (VNets, subnets, NSGs, rules, external devices) and
     * edges (connections between them) in a single graph structure.
     *
     * @returns Observable of the TopologyGraph structure.
     */
    getTopology(): Observable<TopologyGraph> {
        return this.http.get<any>(`${this.baseUrl}/topology`).pipe(
            map(response => this._transformApiResponse(response))
        );
    }

    /**
     * Transform the raw API response into our typed TopologyGraph structure.
     *
     * The backend returns a flat structure with separate arrays for each entity type.
     * This method aggregates them into the node/edge graph format the frontend expects.
     *
     * @param response - Raw API response with entity arrays.
     * @returns Transformed TopologyGraph.
     *
     * @private
     */
    private _transformApiResponse(response: any): TopologyGraph {
        const nodes: TopologyNode[] = [];
        const edges: TopologyEdge[] = [];

        // Transform Virtual Networks
        (response.vnets || []).forEach((vn: any) => {
            nodes.push({
                id: vn.id,
                type: NodeType.VIRTUAL_NETWORK,
                data: vn,
                connections: []
            });
        });

        // Transform Subnets
        (response.subnets || []).forEach((sn: any) => {
            nodes.push({
                id: sn.id,
                type: NodeType.SUBNET,
                data: sn,
                connections: []
            });
            // Add edge from VNet to Subnet
            if (sn.vnetId) {
                edges.push({
                    sourceId: sn.vnetId,
                    targetId: sn.id,
                    connectionType: ConnectionType.PEERING,
                    description: `Parent VNet`
                });
            }
        });

        // Transform NSGs
        (response.nsgs || []).forEach((nsg: any) => {
            nodes.push({
                id: nsg.id,
                type: NodeType.NSG,
                data: nsg,
                connections: []
            });
            // Add edge from VNet to NSG
            if (nsg.vnetId) {
                edges.push({
                    sourceId: nsg.vnetId,
                    targetId: nsg.id,
                    connectionType: ConnectionType.DIRECT,
                    description: `NSG attached`
                });
            }
            // Add edges from NSG to its rules
            (nsg.rules || []).forEach((rule: any) => {
                nodes.push({
                    id: rule.id,
                    type: NodeType.NSG_RULE,
                    data: rule,
                    connections: []
                });
                edges.push({
                    sourceId: nsg.id,
                    targetId: rule.id,
                    connectionType: ConnectionType.DIRECT,
                    description: rule.name
                });
            });
        });

        // Transform External Devices
        (response.externalDevices || []).forEach((ed: any) => {
            nodes.push({
                id: ed.id,
                type: NodeType.EXTERNAL_DEVICE,
                data: ed,
                connections: []
            });
        });

        // Transform Network Connections
        (response.connections || []).forEach((conn: any) => {
            // Only add edges for connections not already represented
            // (VNet-Subnet and VNet-NSG edges are already added above)
            if (!['subnet', 'nsg'].includes(conn.sourceType) ||
                !['nsg', 'subnet'].includes(conn.destinationType)) {
                edges.push({
                    sourceId: conn.sourceId,
                    targetId: conn.destinationId,
                    connectionType: conn.connectionType,
                    description: conn.description
                });
            }
        });

        return { nodes, edges };
    }

    // ==========================================================================
    // Virtual Networks
    // ==========================================================================

    /**
     * Get all Virtual Networks.
     *
     * @returns Observable of VirtualNetwork array.
     */
    getVnets(): Observable<VirtualNetwork[]> {
        return this.http.get<any>(`${this.baseUrl}/virtual-networks`).pipe(
            map(response => (response.vnets || response) as VirtualNetwork[])
        );
    }

    /**
     * Get a single Virtual Network by ID.
     *
     * @param id - The VNet ID.
     * @returns Observable of the VirtualNetwork.
     */
    getVnet(id: string): Observable<VirtualNetwork> {
        return this.http.get<any>(`${this.baseUrl}/virtual-networks/${id}`).pipe(
            map(response => response.vnet || response)
        );
    }

    /**
     * Create a new Virtual Network.
     *
     * @param data - The VNet creation data.
     * @returns Observable of the created VirtualNetwork.
     */
    createVnet(data: CreateVnetRequest): Observable<VirtualNetwork> {
        return this.http.post<any>(`${this.baseUrl}/virtual-networks`, data).pipe(
            map(response => response.vnet || response)
        );
    }

    /**
     * Update an existing Virtual Network.
     *
     * @param id - The VNet ID.
     * @param data - The update data.
     * @returns Observable of the updated VirtualNetwork.
     */
    updateVnet(id: string, data: Partial<CreateVnetRequest>): Observable<VirtualNetwork> {
        return this.http.put<any>(`${this.baseUrl}/virtual-networks/${id}`, data).pipe(
            map(response => response.vnet || response)
        );
    }

    /**
     * Delete a Virtual Network.
     *
     * @param id - The VNet ID.
     * @returns Observable confirming deletion.
     */
    deleteVnet(id: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/virtual-networks/${id}`);
    }

    // ==========================================================================
    // Subnets
    // ==========================================================================

    /**
     * Get Subnets, optionally filtered by VNet ID.
     *
     * @param vnetId - Optional VNet ID to filter by.
     * @returns Observable of Subnet array.
     */
    getSubnets(vnetId?: string): Observable<Subnet[]> {
        let params = new HttpParams();
        if (vnetId) {
            params = params.set('vnetId', vnetId);
        }
        return this.http.get<any>(`${this.baseUrl}/subnets`, { params }).pipe(
            map(response => response.subnets || response)
        );
    }

    /**
     * Get a single Subnet by ID.
     *
     * @param id - The Subnet ID.
     * @returns Observable of the Subnet.
     */
    getSubnet(id: string): Observable<Subnet> {
        return this.http.get<any>(`${this.baseUrl}/subnets/${id}`).pipe(
            map(response => response.subnet || response)
        );
    }

    /**
     * Create a new Subnet.
     *
     * @param data - The Subnet creation data.
     * @returns Observable of the created Subnet.
     */
    createSubnet(data: CreateSubnetRequest): Observable<Subnet> {
        return this.http.post<any>(`${this.baseUrl}/subnets`, data).pipe(
            map(response => response.subnet || response)
        );
    }

    /**
     * Delete a Subnet.
     *
     * @param id - The Subnet ID.
     * @returns Observable confirming deletion.
     */
    deleteSubnet(id: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/subnets/${id}`);
    }

    // ==========================================================================
    // Network Security Groups (NSGs)
    // ==========================================================================

    /**
     * Get all NSGs.
     *
     * @returns Observable of NetworkSecurityGroup array.
     */
    getNsgs(): Observable<NetworkSecurityGroup[]> {
        return this.http.get<any>(`${this.baseUrl}/nsgs`).pipe(
            map(response => response.nsgs || response)
        );
    }

    /**
     * Get a single NSG by ID.
     *
     * @param id - The NSG ID.
     * @returns Observable of the NetworkSecurityGroup.
     */
    getNsg(id: string): Observable<NetworkSecurityGroup> {
        return this.http.get<any>(`${this.baseUrl}/nsgs/${id}`).pipe(
            map(response => response.nsg || response)
        );
    }

    /**
     * Create a new NSG.
     *
     * @param data - The NSG creation data.
     * @returns Observable of the created NetworkSecurityGroup.
     */
    createNsg(data: CreateNsgRequest): Observable<NetworkSecurityGroup> {
        return this.http.post<any>(`${this.baseUrl}/nsgs`, data).pipe(
            map(response => response.nsg || response)
        );
    }

    /**
     * Update an existing NSG.
     *
     * @param id - The NSG ID.
     * @param data - The update data.
     * @returns Observable of the updated NetworkSecurityGroup.
     */
    updateNsg(id: string, data: Partial<CreateNsgRequest>): Observable<NetworkSecurityGroup> {
        return this.http.put<any>(`${this.baseUrl}/nsgs/${id}`, data).pipe(
            map(response => response.nsg || response)
        );
    }

    /**
     * Delete an NSG.
     *
     * @param id - The NSG ID.
     * @returns Observable confirming deletion.
     */
    deleteNsg(id: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/nsgs/${id}`);
    }

    // ==========================================================================
    // NSG Rules
    // ==========================================================================

    /**
     * Get all NSG rules for a given NSG.
     *
     * @param nsgId - The NSG ID.
     * @returns Observable of NSGRule array.
     */
    getNsgRules(nsgId: string): Observable<NSGRule[]> {
        return this.http.get<any>(`${this.baseUrl}/nsgs/${nsgId}/rules`).pipe(
            map(response => response.rules || response)
        );
    }

    /**
     * Create a new NSG rule.
     *
     * @param nsgId - The parent NSG ID.
     * @param data - The rule creation data.
     * @returns Observable of the created NSGRule.
     */
    createNsgRule(nsgId: string, data: CreateNsgRuleRequest): Observable<NSGRule> {
        return this.http.post<any>(`${this.baseUrl}/nsgs/${nsgId}/rules`, data).pipe(
            map(response => response.rule || response)
        );
    }

    /**
     * Update an existing NSG rule.
     *
     * @param ruleId - The rule ID.
     * @param data - The update data.
     * @returns Observable of the updated NSGRule.
     */
    updateNsgRule(ruleId: string, data: Partial<CreateNsgRuleRequest>): Observable<NSGRule> {
        return this.http.put<any>(`${this.baseUrl}/nsg-rules/${ruleId}`, data).pipe(
            map(response => response.rule || response)
        );
    }

    /**
     * Delete an NSG rule.
     *
     * @param ruleId - The rule ID.
     * @returns Observable confirming deletion.
     */
    deleteNsgRule(ruleId: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/nsg-rules/${ruleId}`);
    }

    /**
     * Reorder NSG rules within an NSG.
     *
     * Sends a list of rule IDs with their new positions. The backend
     * will update priorities accordingly.
     *
     * @param nsgId - The parent NSG ID.
     * @param ruleOrder - Array of rule positions.
     * @returns Observable confirming reorder.
     */
    reorderNsgRules(nsgId: string, ruleOrder: NsgRuleOrderRequest): Observable<void> {
        return this.http.put<void>(`${this.baseUrl}/nsgs/${nsgId}/rules/reorder`, ruleOrder);
    }

    /**
     * Sync an NSG configuration to Azure.
     *
     * Triggers a synchronization of the local NSG configuration with
     * the corresponding Azure NSG resource. Updates the sync status
     * on the backend after successful sync.
     *
     * @param nsgId - The NSG ID to sync.
     * @returns Observable confirming sync was triggered.
     */
    syncNsgToAzure(nsgId: string): Observable<{ synced: boolean }> {
        return this.http.post<any>(`${this.baseUrl}/nsgs/${nsgId}/sync`, {}).pipe(
            map(response => response.sync || { synced: true })
        );
    }

    // ==========================================================================
    // External Network Devices
    // ==========================================================================

    /**
     * Get all external network devices.
     *
     * @returns Observable of ExternalNetworkDevice array.
     */
    getExternalDevices(): Observable<ExternalNetworkDevice[]> {
        return this.http.get<any>(`${this.baseUrl}/external-devices`).pipe(
            map(response => response.externalDevices || response)
        );
    }

    /**
     * Get a single external device by ID.
     *
     * @param id - The device ID.
     * @returns Observable of the ExternalNetworkDevice.
     */
    getExternalDevice(id: string): Observable<ExternalNetworkDevice> {
        return this.http.get<any>(`${this.baseUrl}/external-devices/${id}`).pipe(
            map(response => response.device || response)
        );
    }

    /**
     * Create a new external network device.
     *
     * @param data - The device creation data.
     * @returns Observable of the created ExternalNetworkDevice.
     */
    createExternalDevice(data: CreateExternalDeviceRequest): Observable<ExternalNetworkDevice> {
        return this.http.post<any>(`${this.baseUrl}/external-devices`, data).pipe(
            map(response => response.device || response)
        );
    }

    /**
     * Update an existing external network device.
     *
     * @param id - The device ID.
     * @param data - The update data.
     * @returns Observable of the updated ExternalNetworkDevice.
     */
    updateExternalDevice(id: string, data: Partial<CreateExternalDeviceRequest>): Observable<ExternalNetworkDevice> {
        return this.http.put<any>(`${this.baseUrl}/external-devices/${id}`, data).pipe(
            map(response => response.device || response)
        );
    }

    /**
     * Delete an external network device.
     *
     * @param id - The device ID.
     * @returns Observable confirming deletion.
     */
    deleteExternalDevice(id: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/external-devices/${id}`);
    }

    // ==========================================================================
    // Network Connections
    // ==========================================================================

    /**
     * Get network connections, optionally filtered.
     *
     * @param filters - Optional connection filters.
     * @returns Observable of NetworkConnection array.
     */
    getConnections(filters?: ConnectionFilters): Observable<NetworkConnection[]> {
        let params = new HttpParams();
        if (filters?.sourceId) params = params.set('sourceId', filters.sourceId);
        if (filters?.sourceType) params = params.set('sourceType', filters.sourceType);
        if (filters?.destinationId) params = params.set('destinationId', filters.destinationId);
        if (filters?.destinationType) params = params.set('destinationType', filters.destinationType);
        if (filters?.connectionType) params = params.set('connectionType', filters.connectionType);

        return this.http.get<any>(`${this.baseUrl}/connections`, { params }).pipe(
            map(response => response.connections || response)
        );
    }

    /**
     * Get a single connection by ID.
     *
     * @param id - The connection ID.
     * @returns Observable of the NetworkConnection.
     */
    getConnection(id: string): Observable<NetworkConnection> {
        return this.http.get<any>(`${this.baseUrl}/connections/${id}`).pipe(
            map(response => response.connection || response)
        );
    }

    /**
     * Create a new network connection.
     *
     * @param data - The connection creation data.
     * @returns Observable of the created NetworkConnection.
     */
    createConnection(data: CreateConnectionRequest): Observable<NetworkConnection> {
        return this.http.post<any>(`${this.baseUrl}/connections`, data).pipe(
            map(response => response.connection || response)
        );
    }

    /**
     * Delete a network connection.
     *
     * @param id - The connection ID.
     * @returns Observable confirming deletion.
     */
    deleteConnection(id: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/connections/${id}`);
    }

    // ==========================================================================
    // Utility helpers
    // ==========================================================================

    /**
     * Get the display label for a node type.
     *
     * @param type - The node type enum.
     * @returns Display label string.
     */
    getNodeTypeLabel(type: NodeType): string {
        return NODE_TYPE_LABELS[type] || type;
    }

    /**
     * Get the SVG style config for a node type.
     *
     * @param type - The node type enum.
     * @returns Style configuration object.
     */
    getNodeStyle(type: NodeType): { fillColor: string; strokeColor: string; shape: string; width: number; height: number } {
        return NODE_STYLES[type] || { fillColor: '#9e9e9e', strokeColor: '#616161', shape: 'rect', width: 80, height: 40 };
    }

    /**
     * Handle HTTP errors with consistent error handling.
     *
     * @param error - The caught error object.
     * @returns Observable that throws the formatted error.
     *
     * @private
     */
    private _handleError(name: string) {
        return (error: HttpErrorResponse): Observable<never> => {
            const errorMsg = error instanceof HttpErrorResponse
                ? error.message
                : `Unknown error in ${name}`;
            return throwError(() => new Error(`${name}: ${errorMsg}`));
        };
    }
}

export * from '../models/network.model';
