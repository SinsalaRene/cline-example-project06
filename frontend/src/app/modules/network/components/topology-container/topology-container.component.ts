/**
 * Topology Container Component
 *
 * Parent component for the network topology visualization module.
 * Provides a container with view toggle buttons (Tree View / Graph View),
 * a search/filter bar, loading spinner, and error handling.
 *
 * This component lazy-loads either the NetworkTreeComponent or
 * NetworkGraphComponent based on the user's selected view mode.
 *
 * When an NSG node is clicked in graph view, the NSG detail panel is
 * displayed as an overlay/side panel with inline rule editing capabilities.
 *
 * @module topology-container-component
 * @author Network Module Team
 */

import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ViewEncapsulation } from '@angular/core';
import { Subject, takeUntil } from 'rxjs';
import { take } from 'rxjs/operators';
import { NetworkService } from '../../services/network.service';
import { TopologyGraph, TopologyNode } from '../../models/network.model';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { NetworkTreeComponent } from '../network-tree/network-tree.component';
import { NetworkGraphComponent } from '../network-graph/network-graph.component';
import { NsgDetailPanelComponent } from '../nsg-detail-panel/nsg-detail-panel.component';

/**
 * Supported view modes for the topology container.
 */
export type ViewMode = 'tree' | 'graph';

/**
 * Container component for network topology visualization.
 *
 * Provides view mode toggle, search/filter, and delegates rendering
 * to either the tree or graph child component.
 *
 * Also manages the NSG detail panel overlay when an NSG node is clicked.
 *
 * @selector app-topology-container
 * @standalone
 */
@Component({
    selector: 'app-topology-container',
    templateUrl: './topology-container.component.html',
    styleUrls: ['./topology-container.component.css'],
    changeDetection: ChangeDetectionStrategy.OnPush,
    encapsulation: ViewEncapsulation.None,
    imports: [
        CommonModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        MatProgressSpinnerModule,
        MatChipsModule,
        MatInputModule,
        MatFormFieldModule,
        NetworkTreeComponent,
        NetworkGraphComponent,
        NsgDetailPanelComponent
    ],
    standalone: true
})
export class TopologyContainerComponent implements OnInit, OnDestroy {

    private destroy$ = new Subject<void>();

    /** Current view mode: 'tree' or 'graph'. */
    public viewMode: ViewMode = 'tree';

    /** Whether topology data is being loaded. */
    public isLoading = true;

    /** Error message if topology fetch failed. */
    public error: string | null = null;

    /** The loaded topology graph data. */
    public topologyData: TopologyGraph | null = null;

    /** Search query for filtering nodes. */
    public searchQuery: string = '';

    /** Filter by node type. */
    public filterType: string = 'all';

    /** Filter by location. */
    public filterLocation: string = '';

    /** Count of nodes in the current topology. */
    public nodeCount = 0;

    /** Whether the NSG detail panel is visible. */
    public showNsgDetail = false;

    /** The NSG ID currently being viewed in the detail panel. */
    public selectedNsgId: string | null = null;

    /**
     * Creates a new TopologyContainerComponent.
     *
     * @param networkService - The network service for fetching topology data.
     */
    constructor(private networkService: NetworkService) { }

    /**
     * Lifecycle hook called after project initialization.
     * Subscribes to API calls and loads the topology graph.
     */
    ngOnInit(): void {
        this.loadTopology();
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
     * Load the topology graph from the backend API.
     */
    loadTopology(): void {
        this.isLoading = true;
        this.error = null;
        this.networkService.getTopology().pipe(take(1)).subscribe({
            next: (data) => {
                this.topologyData = data;
                this.nodeCount = data.nodes.length;
                this.isLoading = false;
                this.error = null;
            },
            error: (err: Error) => {
                this.error = `Failed to load topology: ${err.message}`;
                this.isLoading = false;
            }
        });
    }

    /**
     * Switch between tree and graph view modes.
     *
     * @param mode - The view mode to switch to.
     */
    switchView(mode: ViewMode): void {
        this.viewMode = mode;
    }

    /**
     * Retry loading the topology after a failure.
     */
    retry(): void {
        this.loadTopology();
    }

    /**
     * Handle search input changes with debouncing.
     */
    onSearchInput(): void {
        // Debounced in the child components
    }

    /**
     * Clear all filters and search query.
     */
    clearFilters(): void {
        this.searchQuery = '';
        this.filterType = 'all';
        this.filterLocation = '';
    }

    /**
     * Handle node action events from tree component.
     *
     * @param action - The node action object.
     */
    onNodeAction(action: { nodeId: string; action: string }): void {
        console.log('Node action:', action);
    }

    /**
     * Handle node selected events from graph component.
     *
     * When an NSG node is selected, loads the NSG details and shows the detail panel.
     *
     * @param node - The selected topology node.
     */
    onNodeSelected(node: TopologyNode): void {
        if (node.type === 'nsg') {
            this.loadNsgDetails(node);
        }
    }

    /**
     * Handle node double-click events from graph component.
     *
     * When an NSG node is double-clicked, loads the NSG details and shows the detail panel.
     *
     * @param node - The double-clicked topology node.
     */
    onNodeDblClick(node: TopologyNode): void {
        if (node.type === 'nsg') {
            this.loadNsgDetails(node);
        }
    }

    /**
     * Load NSG details for a given topology node.
     * The NsgDetailPanelComponent loads the NSG data internally.
     *
     * @param node - The NSG topology node.
     */
    loadNsgDetails(node: TopologyNode): void {
        this.selectedNsgId = node.id;
        this.showNsgDetail = true;
    }

    /**
     * Close the NSG detail panel.
     */
    closeNsgDetail(): void {
        this.showNsgDetail = false;
        this.selectedNsgId = null;
    }
}