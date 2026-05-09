/**
 * Network Graph Component
 *
 * Renders an SVG-based interactive network topology graph.
 *
 * # Rendering Algorithm
 *
 * The graph uses a layered layout algorithm:
 * 1. **Level Assignment**: Nodes are assigned to layers based on their type.
 *    - Layer 0: Virtual Networks (top)
 *    - Layer 1: Subnets
 *    - Layer 2: NSGs
 *    - Layer 3: NSG Rules
 *    - Layer 4: External Devices
 * 2. **Node Placement**: Within each layer, nodes are spaced evenly
 *    along the Y axis, centered horizontally.
 * 3. **Edge Routing**: Edges are drawn as straight lines between
 *    node centers, with arrow markers indicating direction.
 * 4. **Transform & Zoom**: The SVG viewBox provides a coordinate
 *    system. Zoom is applied via a scale transform on an inner
 *    <g> element. Pan is applied via a translate transform.
 * 5. **Drag-and-Drop**: When the user mousedown on a node, the
 *    component captures the delta in SVG coordinates and applies
 *    it to the node's x/y, updating the DOM live.
 *
 * @module network-graph-component
 * @author Network Module Team
 * @since 1.0.0
 */

import {
    Component,
    OnInit,
    OnDestroy,
    ChangeDetectionStrategy,
    ViewEncapsulation,
    Input,
    Output,
    EventEmitter,
    ElementRef,
    ViewChild,
    AfterViewInit,
    NgZone,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, takeUntil } from 'rxjs';
import {
    TopologyNode,
    NodeType,
    TopologyEdge,
    CONNECTION_TYPE_LABELS,
    NODE_STYLES,
} from '../../models/network.model';

// ============================================================================
// SVG Element factories
// ============================================================================

/**
 * Creates an SVG <g> (group) element.
 *
 * @param id - The group ID.
 * @returns The created SVGGroupElement.
 *
 * @private
 */
function createSvgGroup(id: string): SVGGElement {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('id', id);
    return g;
}

/**
 * Creates an SVG <line> element.
 *
 * @param id - The line ID.
 * @returns The created SVGLineElement.
 *
 * @private
 */
function createSvgLine(id: string): SVGLineElement {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('id', id);
    return line;
}

/**
 * Creates an SVG <rect> element.
 *
 * @param id - The rect ID.
 * @param x - X position.
 * @param y - Y position.
 * @param w - Width.
 * @param h - Height.
 * @param rx - Border radius.
 * @returns The created SVGRectElement.
 *
 * @private
 */
function createSvgRect(id: string, x: number, y: number, w: number, h: number, rx = 4): SVGRectElement {
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('id', id);
    rect.setAttribute('x', String(x));
    rect.setAttribute('y', String(y));
    rect.setAttribute('width', String(w));
    rect.setAttribute('height', String(h));
    rect.setAttribute('rx', String(rx));
    return rect;
}

/**
 * Creates an SVG <text> element.
 *
 * @param id - The text ID.
 * @param x - X position.
 * @param y - Y position.
 * @param text - The text content.
 * @returns The created SVGTextElement.
 *
 * @private
 */
function createSvgText(id: string, x: number, y: number, text: string): SVGTextElement {
    const textEl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    textEl.setAttribute('id', id);
    textEl.setAttribute('x', String(x));
    textEl.setAttribute('y', String(y));
    textEl.setAttribute('text-anchor', 'middle');
    textEl.textContent = text;
    return textEl;
}

/**
 * Creates an SVG <polygon> element for hexagon/diamond shapes.
 *
 * @param id - The polygon ID.
 * @param points - Array of x,y pairs.
 * @returns The created SVGPolygonElement.
 *
 * @private
 */
function createSvgPolygon(id: string, points: number[]): SVGPolygonElement {
    const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygon.setAttribute('id', id);
    polygon.setAttribute('points', points.map((p) => String(p)).join(' '));
    return polygon;
}

/**
 * Creates an SVG <marker> element for arrow heads.
 *
 * @param id - The marker ID.
 * @returns The created SVGElement.
 *
 * @private
 */
function createSvgMarker(id: string): SVGElement {
    const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    marker.setAttribute('id', id);
    marker.setAttribute('markerWidth', '10');
    marker.setAttribute('markerHeight', '10');
    marker.setAttribute('refX', '10');
    marker.setAttribute('refY', '5');
    marker.setAttribute('orient', 'auto');

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M0,0 L10,5 L0,10 Z');
    path.setAttribute('fill', '#666');

    marker.appendChild(path);
    return marker;
}

// ============================================================================
// Node position interface
// ============================================================================

/** Position information for a rendered node. */
interface NodePosition {
    nodeId: string;
    x: number;
    y: number;
    width: number;
    height: number;
}

// ============================================================================
// Component
// ============================================================================

/**
 * SVG-based interactive graph view of the network topology.
 *
 * Supports drag-and-drop, zoom in/out, node selection, context menu,
 * and a responsive legend.
 *
 * @selector app-network-graph
 * @standalone
 */
@Component({
    selector: 'app-network-graph',
    templateUrl: './network-graph.component.html',
    styleUrls: ['./network-graph.component.css'],
    changeDetection: ChangeDetectionStrategy.OnPush,
    encapsulation: ViewEncapsulation.None,
    imports: [
        CommonModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        MatChipsModule,
        MatDividerModule,
        MatInputModule,
        MatFormFieldModule,
        FormsModule,
        MatMenuModule,
        MatTooltipModule,
    ],
    standalone: true,
})
export class NetworkGraphComponent implements OnInit, OnDestroy, AfterViewInit {
    private destroy$ = new Subject<void>();

    /** Input: topology nodes to render. */
    @Input() nodes: TopologyNode[] = [];

    /** Input: topology edges to render. */
    @Input() edges: TopologyEdge[] = [];

    /** Input: search query for highlighting. */
    @Input() searchQuery: string = '';

    /** Output emitted when a user selects a node. */
    @Output() nodeSelected = new EventEmitter<TopologyNode>();

    /** Output emitted when a node is double-clicked. */
    @Output() nodeDblClick = new EventEmitter<TopologyNode>();

    /** Output emitted for context menu actions. */
    @Output() contextMenuAction = new EventEmitter<{ nodeId: string; action: string }>();

    /** Output emitted when zoom level changes. */
    @Output() zoomChange = new EventEmitter<number>();

    /** Reference to the SVG container element. */
    @ViewChild('svgContainer', { read: ElementRef }) svgContainer!: ElementRef<SVGSVGElement>;

    /** Reference to the SVG element for DOM manipulation. */
    private svgEl!: SVGSVGElement;

    /** The pan transform group within SVG. */
    private panGroup!: SVGGElement;

    /** The edges group within the pan group. */
    private edgesGroup!: SVGGElement;

    /** The nodes group within the pan group. */
    private nodesGroup!: SVGGElement;

    /** The legend group at the bottom of the SVG. */
    private legendGroup!: SVGGElement;

    /** The defs element for markers and gradients. */
    private defs!: SVGElement;

    /** Zoom scale factor. */
    private zoomScale = 1;

    /** Pan offset X. */
    private panX = 0;

    /** Pan offset Y. */
    private panY = 0;

    /** Whether the user is currently dragging the canvas. */
    private isPanning = false;

    /** Whether the user is dragging a node. */
    private isDraggingNode = false;

    /** The node currently being dragged. */
    private draggedNodeId: string | null = null;

    /** Start mouse position for drag calculation. */
    private dragStartX = 0;

    /** Start mouse position for drag calculation. */
    private dragStartY = 0;

    /** Map of node ID to computed position for rendering. */
    private nodePositions = new Map<string, NodePosition>();

    /** Currently selected node ID. */
    private selectedNodeId: string | null = null;

    /** Legend visibility. */
    public showLegend = true;

    /** Context menu state. */
    public showContextMenu = false;

    /** Context menu position. */
    public contextMenuX = 0;

    /** Context menu position. */
    public contextMenuY = 0;

    /** Context menu node ID. */
    contextMenuNodeId: string | null = null;

    /** SVG namespace constant. */
    private readonly SVG_NS = 'http://www.w3.org/2000/svg';

    /**
     * Creates a new NetworkGraphComponent.
     *
     * @param elementRef - The host element reference.
     * @param ngZone - The Angular zone for event listener management.
     */
    constructor(
        private elementRef: ElementRef,
        private ngZone: NgZone
    ) { }

    /**
     * Lifecycle hook called after project initialization.
     */
    ngOnInit(): void {
        // Will render after view init
    }

    /**
     * Lifecycle hook called after the view has been initialized.
     * Sets up the SVG canvas and event listeners.
     */
    ngAfterViewInit(): void {
        this._initSvg();
        this._addGlobalListeners();
        this._render();
    }

    /**
     * Lifecycle hook called before component destruction.
     * Cleans up subscriptions and event listeners.
     */
    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
        this._removeGlobalListeners();
    }

    /**
     * Initialize the SVG canvas structure.
     *
     * Creates the SVG element with viewBox, defs (for markers),
     * a pan transform group containing:
     *   - edges group
     *   - nodes group
     *   - legend group
     *
     * @private
     */
    private _initSvg(): void {
        if (!this.svgContainer) return;

        const host = this.svgContainer.nativeElement;
        this.svgEl = document.createElementNS(this.SVG_NS, 'svg');
        this.svgEl.setAttribute('width', '100%');
        this.svgEl.setAttribute('height', '100%');
        this.svgEl.setAttribute('viewBox', '0 0 1200 700');
        this.svgEl.setAttribute('preserveAspectRatio', 'xMidYMid meet');

        // Defs for markers and gradients
        this.defs = document.createElementNS(this.SVG_NS, 'defs');
        this.svgEl.appendChild(this.defs);

        // Create arrow marker
        const marker = createSvgMarker('arrow');
        this.defs.appendChild(marker);

        // Create highlighted arrow marker
        const highlightMarker = createSvgMarker('arrow-highlight');
        (highlightMarker as SVGGElement).querySelectorAll('path').forEach((p) => {
            (p as SVGPathElement).setAttribute('fill', '#2196f3');
        });
        this.defs.appendChild(highlightMarker);

        // Pan transform group
        this.panGroup = createSvgGroup('pan-group');
        this.svgEl.appendChild(this.panGroup);

        // Edges group
        this.edgesGroup = createSvgGroup('edges-group');
        this.panGroup.appendChild(this.edgesGroup);

        // Nodes group
        this.nodesGroup = createSvgGroup('nodes-group');
        this.panGroup.appendChild(this.nodesGroup);

        // Legend group
        this.legendGroup = createSvgGroup('legend-group');
        this.panGroup.appendChild(this.legendGroup);

        host.appendChild(this.svgEl);
    }

    /**
     * Add global mouse event listeners for pan and drag.
     * Using NgZone.fromEvent to handle events outside Angular's zone
     * for performance.
     *
     * @private
     */
    private _addGlobalListeners(): void {
        // Use native event listeners with the ngZone for proper change detection
        const svg = this.svgEl;
        if (!svg) return;

        // We add listeners directly to the SVG element
        svg.addEventListener('mousedown', (e: MouseEvent) => this._onSvgMouseDown(e));
        svg.addEventListener('mousemove', (e: MouseEvent) => this._onSvgMouseMove(e));
        svg.addEventListener('mouseup', (e: MouseEvent) => this._onSvgMouseUp(e));
        svg.addEventListener('wheel', (e: WheelEvent) => this._onWheel(e), { passive: false });
        svg.addEventListener('contextmenu', (e: MouseEvent) => this._onContextMenu(e));
        svg.addEventListener('dblclick', (e: MouseEvent) => this._onDblClick(e));

        // Window listeners for drag end
        this.ngZone.runOutsideAngular(() => {
            document.addEventListener('mousemove', (e: MouseEvent) => this._onGlobalMouseMove(e));
            document.addEventListener('mouseup', (e: MouseEvent) => this._onGlobalMouseUp(e));
        });
    }

    /**
     * Remove global event listeners.
     *
     * @private
     */
    private _removeGlobalListeners(): void {
        const svg = this.svgEl;
        if (!svg) return;

        svg.removeEventListener('mousedown', this._onSvgMouseDown as EventListener);
        svg.removeEventListener('mousemove', this._onSvgMouseMove as EventListener);
        svg.removeEventListener('mouseup', this._onSvgMouseUp as EventListener);
        svg.removeEventListener('wheel', this._onWheel as EventListener);
        svg.removeEventListener('contextmenu', this._onContextMenu as EventListener);
        svg.removeEventListener('dblclick', this._onDblClick as EventListener);

        document.removeEventListener('mousemove', this._onGlobalMouseMove as EventListener);
        document.removeEventListener('mouseup', this._onGlobalMouseUp as EventListener);
    }

    /**
     * Calculate node positions using a layered layout algorithm.
     *
     * Layer 0: Virtual Networks
     * Layer 1: Subnets
     * Layer 2: NSGs
     * Layer 3: External Devices
     * NSG Rules are grouped inside their parent NSG.
     *
     * @returns A map of node ID to NodePosition.
     *
     * @private
     */
    private _calculatePositions(): Map<string, NodePosition> {
        const positions = new Map<string, NodePosition>();

        // Separate nodes by layer
        const layer0: TopologyNode[] = []; // VNets
        const layer1: TopologyNode[] = []; // Subnets
        const layer2: TopologyNode[] = []; // NSGs
        const layer3: TopologyNode[] = []; // External Devices
        const rules: TopologyNode[] = []; // NSG Rules

        for (const node of this.nodes) {
            switch (node.type) {
                case NodeType.VIRTUAL_NETWORK:
                    layer0.push(node);
                    break;
                case NodeType.SUBNET:
                    layer1.push(node);
                    break;
                case NodeType.NSG:
                    layer2.push(node);
                    break;
                case NodeType.EXTERNAL_DEVICE:
                    layer3.push(node);
                    break;
                case NodeType.NSG_RULE:
                    rules.push(node);
                    break;
            }
        }

        const startY = 80;
        const layerSpacing = 160;

        // Layer 0: VNets (centered horizontally)
        const l0Count = layer0.length || 1;
        const l0Width = l0Count * 220;
        const l0StartX = (1200 - l0Width) / 2;

        layer0.forEach((node, i) => {
            const style = NODE_STYLES[NodeType.VIRTUAL_NETWORK];
            const x = l0StartX + i * 220 + 50;
            const y = startY;
            positions.set(node.id, {
                nodeId: node.id,
                x,
                y,
                width: style.width,
                height: style.height,
            });
        });

        // Layer 1: Subnets (below VNets)
        const l1Count = layer1.length || 1;
        const l1Width = l1Count * 160;
        const l1StartX = (1200 - l1Width) / 2;

        layer1.forEach((node, i) => {
            const style = NODE_STYLES[NodeType.SUBNET];
            const x = l1StartX + i * 160 + 30;
            const y = startY + layerSpacing;
            positions.set(node.id, {
                nodeId: node.id,
                x,
                y,
                width: style.width,
                height: style.height,
            });
        });

        // Layer 2: NSGs
        const l2Count = layer2.length || 1;
        const l2Width = l2Count * 120;
        const l2StartX = (1200 - l2Width) / 2;

        layer2.forEach((node, i) => {
            const style = NODE_STYLES[NodeType.NSG];
            const x = l2StartX + i * 120 + 10;
            const y = startY + layerSpacing * 2;
            positions.set(node.id, {
                nodeId: node.id,
                x,
                y,
                width: style.width,
                height: style.height,
            });
        });

        // Layer 3: External Devices
        const l3Count = layer3.length || 1;
        const l3Width = l3Count * 120;
        const l3StartX = (1200 - l3Width) / 2;

        layer3.forEach((node, i) => {
            const style = NODE_STYLES[NodeType.EXTERNAL_DEVICE];
            const x = l3StartX + i * 120 + 10;
            const y = startY + layerSpacing * 3;
            positions.set(node.id, {
                nodeId: node.id,
                x,
                y,
                width: style.width,
                height: style.height,
            });
        });

        // Rules: placed beside their parent NSG
        const nsgMap = new Map<string, TopologyNode>();
        layer2.forEach((n) => nsgMap.set(n.data.id, n));

        rules.forEach((rule) => {
            const nsgData = rule.data as { nsgId: string };
            const parentNsg = nsgMap.get(nsgData?.nsgId);
            const parentPos = parentNsg ? positions.get(parentNsg.id) : undefined;

            const style = NODE_STYLES[NodeType.NSG_RULE];
            // Find the next available rule slot for this NSG
            const ruleCountForNsg = rules.filter(
                (r) => (r.data as { nsgId: string })?.nsgId === nsgData?.nsgId
            ).length;
            const ruleIndex = rules
                .filter((r) => (r.data as { nsgId: string })?.nsgId === nsgData?.nsgId)
                .indexOf(rule);

            const x = parentPos
                ? parentPos.x + parentPos.width + 20 + (ruleIndex % 3) * 50
                : 800;
            const y = parentPos
                ? parentPos.y + 10 + Math.floor(ruleIndex / 3) * 40
                : 400;

            positions.set(rule.id, {
                nodeId: rule.id,
                x,
                y,
                width: style.width,
                height: style.height,
            });
        });

        return positions;
    }

    /**
     * Render the graph: calculate positions, draw edges, draw nodes.
     *
     * @private
     */
    private _render(): void {
        if (!this.svgEl) return;

        this.nodePositions = this._calculatePositions();

        // Apply transform
        this._applyTransform();

        // Clear and redraw
        this.edgesGroup.innerHTML = '';
        this.nodesGroup.innerHTML = '';
        this.legendGroup.innerHTML = '';

        // Draw edges
        this._drawEdges();

        // Draw nodes
        this._drawNodes();

        // Draw legend
        this._drawLegend();
    }

    /**
     * Apply the current zoom and pan transform to the pan group.
     *
     * @private
     */
    private _applyTransform(): void {
        if (!this.panGroup) return;
        this.panGroup.setAttribute(
            'transform',
            `translate(${this.panX}, ${this.panY}) scale(${this.zoomScale})`
        );
    }

    /**
     * Draw edges between nodes.
     *
     * @private
     */
    private _drawEdges(): void {
        const highlighted = this.selectedNodeId || this.searchQuery;

        for (const edge of this.edges) {
            const sourcePos = this.nodePositions.get(edge.sourceId);
            const targetPos = this.nodePositions.get(edge.targetId);

            if (!sourcePos || !targetPos) continue;

            const line = createSvgLine(`edge-${edge.sourceId}-${edge.targetId}`);
            line.setAttribute('x1', String(sourcePos.x + sourcePos.width / 2));
            line.setAttribute('y1', String(sourcePos.y + sourcePos.height / 2));
            line.setAttribute('x2', String(targetPos.x + targetPos.width / 2));
            line.setAttribute('y2', String(targetPos.y + targetPos.height / 2));
            line.setAttribute('stroke', highlighted ? '#2196f3' : '#999');
            line.setAttribute('stroke-width', highlighted ? '2.5' : '1.5');
            line.setAttribute('stroke-dasharray', '6,4');
            line.setAttribute('opacity', highlighted ? '1' : '0.6');
            line.setAttribute('marker-end', 'url(#arrow-highlight)');

            this.edgesGroup.appendChild(line);
        }
    }

    /**
     * Draw nodes on the canvas.
     *
     * @private
     */
    private _drawNodes(): void {
        for (const [nodeId, pos] of this.nodePositions) {
            const node = this.nodes.find((n) => n.id === nodeId);
            if (!node) continue;

            const style = NODE_STYLES[node.type] || {
                fillColor: '#999',
                strokeColor: '#666',
                shape: 'rect',
                width: 100,
                height: 50,
            };

            const isSelected = this.selectedNodeId === nodeId;
            const isHighlighted =
                this.searchQuery &&
                (node.data as { name?: string }).name?.toLowerCase().includes(this.searchQuery.toLowerCase());

            const g = createSvgGroup(`node-${nodeId}`);
            g.setAttribute('cursor', 'pointer');
            g.setAttribute('data-node-id', nodeId);

            let shape: SVGElement;

            // Draw shape based on node type
            switch (style.shape) {
                case 'diamond':
                    // NSG: diamond shape
                    const cx = pos.x + pos.width / 2;
                    const cy = pos.y + pos.height / 2;
                    const d = pos.width / 2;
                    const points = [cx, cy - d, cx + d, cy, cx, cy + d, cx - d, cy];
                    shape = createSvgPolygon(`node-${nodeId}-shape`, points);
                    break;

                case 'hexagon':
                    // External Device: hexagon
                    const hx = pos.x + pos.width / 2;
                    const hy = pos.y + pos.height / 2;
                    const hr = pos.width / 2;
                    const hexPoints: number[] = [];
                    for (let i = 0; i < 6; i++) {
                        const angle = (Math.PI / 3) * i - Math.PI / 6;
                        hexPoints.push(hx + hr * Math.cos(angle));
                        hexPoints.push(hy + hr * Math.sin(angle));
                    }
                    shape = createSvgPolygon(`node-${nodeId}-shape`, hexPoints);
                    break;

                default:
                    // Rectangle
                    const rect = createSvgRect(
                        `node-${nodeId}-shape`,
                        pos.x,
                        pos.y,
                        pos.width,
                        pos.height,
                        node.type === NodeType.EXTERNAL_DEVICE ? 8 : 4
                    );
                    shape = rect;
            }

            shape.setAttribute('fill', style.fillColor);
            shape.setAttribute('stroke', isSelected ? '#1a237e' : isHighlighted ? '#ff9800' : style.strokeColor);
            shape.setAttribute('stroke-width', isSelected ? '3' : '1.5');
            shape.setAttribute('opacity', isHighlighted ? '1' : '0.9');
            g.appendChild(shape);

            // Inner shadow/highlight for selected
            if (isSelected) {
                const highlightRect = createSvgRect(
                    `node-${nodeId}-highlight`,
                    pos.x + 2,
                    pos.y + 2,
                    pos.width - 4,
                    pos.height - 4,
                    4
                );
                highlightRect.setAttribute('fill', 'none');
                highlightRect.setAttribute('stroke', '#ffffff');
                highlightRect.setAttribute('stroke-width', '2');
                highlightRect.setAttribute('opacity', '0.3');
                g.appendChild(highlightRect);
            }

            // Node label
            const label = (node.data as { name?: string }).name || nodeId;
            const textEl = createSvgText(
                `node-${nodeId}-label`,
                pos.x + pos.width / 2,
                pos.y + pos.height / 2 + 5,
                label.length > 16 ? label.substring(0, 14) + '..' : label
            );
            textEl.setAttribute('fill', '#fff');
            textEl.setAttribute('font-size', '11');
            textEl.setAttribute('font-weight', 'bold');
            textEl.setAttribute('pointer-events', 'none');
            g.appendChild(textEl);

            // Type indicator icon
            const typeIcon = createSvgText(
                `node-${nodeId}-type`,
                pos.x + pos.width / 2,
                pos.y + 14,
                this._getTypeIcon(node.type)
            );
            typeIcon.setAttribute('font-size', '14');
            typeIcon.setAttribute('pointer-events', 'none');
            g.appendChild(typeIcon);

            this.nodesGroup.appendChild(g);
        }
    }

    /**
     * Draw the legend at the bottom of the graph.
     *
     * @private
     */
    private _drawLegend(): void {
        if (!this.showLegend) return;

        const legendY = 640;
        const startX = 20;
        let currentX = startX;

        const types: NodeType[] = [
            NodeType.VIRTUAL_NETWORK,
            NodeType.SUBNET,
            NodeType.NSG,
            NodeType.NSG_RULE,
            NodeType.EXTERNAL_DEVICE,
        ];

        for (const type of types) {
            const style = NODE_STYLES[type];
            const labelMap: Record<string, string> = {
                [NodeType.VIRTUAL_NETWORK]: 'VNet',
                [NodeType.SUBNET]: 'Subnet',
                [NodeType.NSG]: 'NSG',
                [NodeType.NSG_RULE]: 'Rule',
                [NodeType.EXTERNAL_DEVICE]: 'Ext Device',
            };
            const label = labelMap[type] || type;

            let shapeEl: SVGElement;
            switch (style.shape) {
                case 'diamond':
                    const cx = currentX + 8;
                    const cy = legendY + 8;
                    const d = 8;
                    shapeEl = createSvgPolygon(`legend-${type}`, [cx, cy - d, cx + d, cy, cx, cy + d, cx - d, cy]);
                    break;
                case 'hexagon':
                    const hx = currentX + 8;
                    const hy = legendY + 8;
                    const hr = 8;
                    const hexPoints: number[] = [];
                    for (let i = 0; i < 6; i++) {
                        const angle = (Math.PI / 3) * i - Math.PI / 6;
                        hexPoints.push(hx + hr * Math.cos(angle));
                        hexPoints.push(hy + hr * Math.sin(angle));
                    }
                    shapeEl = createSvgPolygon(`legend-${type}`, hexPoints);
                    break;
                default:
                    shapeEl = createSvgRect(`legend-${type}`, currentX, legendY, 16, 16, 2);
            }

            shapeEl.setAttribute('fill', style.fillColor);
            shapeEl.setAttribute('stroke', style.strokeColor);
            shapeEl.setAttribute('stroke-width', '1');
            this.legendGroup.appendChild(shapeEl);

            const textEl = createSvgText(`legend-label-${type}`, currentX + 24, legendY + 12, label);
            textEl.setAttribute('fill', '#333');
            textEl.setAttribute('font-size', '11');
            this.legendGroup.appendChild(textEl);

            currentX += 100;
        }
    }

    /**
     * Get the Unicode icon character for a node type.
     *
     * @param type - The node type.
     * @returns Unicode icon character.
     *
     * @private
     */
    private _getTypeIcon(type: NodeType): string {
        const icons: Record<NodeType, string> = {
            [NodeType.VIRTUAL_NETWORK]: '🌐',
            [NodeType.SUBNET]: '📦',
            [NodeType.NSG]: '🛡️',
            [NodeType.NSG_RULE]: '📋',
            [NodeType.EXTERNAL_DEVICE]: '🔌',
            [NodeType.CONNECTION]: '🔗',
        };
        return icons[type] || '📌';
    }

    /**
     * Convert screen coordinates to SVG coordinates.
     *
     * @param screenX - Screen X coordinate.
     * @param screenY - Screen Y coordinate.
     * @returns SVG coordinate.
     *
     * @private
     */
    private _screenToSvg(screenX: number, screenY: number): { x: number; y: number } {
        const rect = this.svgEl.getBoundingClientRect();
        const svgX = (screenX - rect.left) / rect.width * 1200;
        const svgY = (screenY - rect.top) / rect.height * 700;
        return {
            x: (svgX - this.panX) / this.zoomScale,
            y: (svgY - this.panY) / this.zoomScale,
        };
    }

    /**
     * Handle SVG mouse down for node selection or canvas panning.
     *
     * @param event - The mouse event.
     *
     * @private
     */
    private _onSvgMouseDown = (event: MouseEvent): void => {
        const target = event.target as SVGElement;
        const nodeGroup = target.closest('[data-node-id]') as SVGElement | null;

        if (nodeGroup) {
            const nodeId = nodeGroup.getAttribute('data-node-id');
            if (nodeId) {
                // Start dragging a node
                this.isDraggingNode = true;
                this.draggedNodeId = nodeId;
                this.dragStartX = event.clientX;
                this.dragStartY = event.clientY;
                this.selectedNodeId = nodeId;
                this._render();
                event.preventDefault();
                return;
            }
        }

        // Start panning
        this.isPanning = true;
        this.dragStartX = event.clientX;
        this.dragStartY = event.clientY;
        event.preventDefault();
    };

    /**
     * Handle SVG mouse move for panning or node dragging.
     *
     * @param event - The mouse event.
     *
     * @private
     */
    private _onSvgMouseMove = (event: MouseEvent): void => {
        if (this.isPanning) {
            const dx = event.clientX - this.dragStartX;
            const dy = event.clientY - this.dragStartY;
            this.panX += dx;
            this.panY += dy;
            this.dragStartX = event.clientX;
            this.dragStartY = event.clientY;
            this._applyTransform();
            event.preventDefault();
        } else if (this.isDraggingNode && this.draggedNodeId) {
            const pos = this.nodePositions.get(this.draggedNodeId);
            if (pos) {
                const svgPos = this._screenToSvg(event.clientX, event.clientY);
                pos.x = Math.round(svgPos.x - pos.width / 2);
                pos.y = Math.round(svgPos.y - pos.height / 2);
                this._render();
                event.preventDefault();
            }
        }
    };

    /**
     * Handle SVG mouse up to end panning or dragging.
     *
     * @param event - The mouse event.
     *
     * @private
     */
    private _onSvgMouseUp = (event: MouseEvent): void => {
        if (this.isDraggingNode && this.draggedNodeId) {
            this.isDraggingNode = false;
            this.draggedNodeId = null;
            // Trigger change detection outside Angular zone
            this.ngZone.run(() => {
                this._render();
            });
        }
        this.isPanning = false;
    };

    /**
     * Handle global mouse move for drag continuation.
     *
     * @param event - The mouse event.
     *
     * @private
     */
    private _onGlobalMouseMove = (event: MouseEvent): void => {
        if (this.isDraggingNode && this.draggedNodeId) {
            const pos = this.nodePositions.get(this.draggedNodeId);
            if (pos) {
                const svgPos = this._screenToSvg(event.clientX, event.clientY);
                pos.x = Math.round(svgPos.x - pos.width / 2);
                pos.y = Math.round(svgPos.y - pos.height / 2);
                this._render();
            }
        }
    };

    /**
     * Handle global mouse up to end drag.
     *
     * @param event - The mouse event.
     *
     * @private
     */
    private _onGlobalMouseUp = (event: MouseEvent): void => {
        if (this.isDraggingNode) {
            this.isDraggingNode = false;
            this.draggedNodeId = null;
            this.ngZone.run(() => {
                this._render();
            });
        }
        this.isPanning = false;
    };

    /**
     * Handle mouse wheel for zoom in/out.
     *
     * @param event - The wheel event.
     *
     * @private
     */
    private _onWheel = (event: WheelEvent): void => {
        event.preventDefault();
        const delta = -event.deltaY * 0.002;
        const newScale = Math.min(Math.max(0.2, this.zoomScale + delta), 3);

        // Zoom toward mouse position
        const rect = this.svgEl.getBoundingClientRect();
        const mouseX = ((event.clientX - rect.left) / rect.width) * 1200;
        const mouseY = ((event.clientY - rect.top) / rect.height) * 700;

        const scaleRatio = newScale / this.zoomScale;
        this.panX = mouseX - (mouseX - this.panX) * scaleRatio;
        this.panY = mouseY - (mouseY - this.panY) * scaleRatio;
        this.zoomScale = newScale;

        this._applyTransform();
        this.zoomChange.emit(this.zoomScale);
    };

    /**
     * Handle right-click context menu on the graph.
     *
     * @param event - The mouse event.
     *
     * @private
     */
    _onContextMenu = (event: MouseEvent): void => {
        event.preventDefault();
        const target = event.target as SVGElement;
        const nodeGroup = target.closest('[data-node-id]') as SVGElement | null;

        if (nodeGroup) {
            const nodeId = nodeGroup.getAttribute('data-node-id');
            if (nodeId) {
                this.contextMenuNodeId = nodeId;
                this.contextMenuX = event.clientX;
                this.contextMenuY = event.clientY;
                this.showContextMenu = true;
                this.ngZone.run(() => {
                    // Trigger change detection
                });
            }
        }
    };

    /**
     * Handle double-click on a node.
     *
     * @param event - The mouse event.
     *
     * @private
     */
    private _onDblClick = (event: MouseEvent): void => {
        const target = event.target as SVGElement;
        const nodeGroup = target.closest('[data-node-id]') as SVGElement | null;

        if (nodeGroup) {
            const nodeId = nodeGroup.getAttribute('data-node-id');
            if (nodeId) {
                const node = this.nodes.find((n) => n.id === nodeId);
                if (node) {
                    this.ngZone.run(() => {
                        this.nodeDblClick.emit(node);
                    });
                }
            }
        }
    };

    /**
     * Handle zoom in button click.
     */
    zoomIn(): void {
        this.zoomScale = Math.min(3, this.zoomScale + 0.2);
        this._applyTransform();
        this.zoomChange.emit(this.zoomScale);
    }

    /**
     * Handle zoom out button click.
     */
    zoomOut(): void {
        this.zoomScale = Math.max(0.2, this.zoomScale - 0.2);
        this._applyTransform();
        this.zoomChange.emit(this.zoomScale);
    }

    /**
     * Reset zoom and pan to default.
     */
    resetView(): void {
        this.zoomScale = 1;
        this.panX = 0;
        this.panY = 0;
        this._render();
        this.zoomChange.emit(1);
    }

    /**
     * Toggle legend visibility.
     */
    toggleLegend(): void {
        this.showLegend = !this.showLegend;
        this._render();
    }

    /**
     * Handle context menu action selection.
     *
     * @param action - The action to perform.
     */
    onContextMenuAction = (action: string): void => {
        const nodeId = this.contextMenuNodeId;
        if (nodeId !== null && nodeId !== undefined) {
            this.contextMenuAction.emit({
                nodeId: nodeId,
                action,
            });
        }
        this.showContextMenu = false;
        this.contextMenuNodeId = null;
    };

    /**
     * Handle clicking on the graph background (deselect node).
     */
    onGraphBackgroundClick(): void {
        this.selectedNodeId = null;
        this._render();
    }
}