/**
 * Network Module
 *
 * Angular module for network topology visualization.
 *
 * This module provides components and services for managing the network topology,
 * including Virtual Networks, Subnets, Network Security Groups (NSG), NSG Rules,
 * External Network Devices, and Network Connections.
 *
 * # Module Architecture
 *
 * ```
 * network/
 * ├── network.module.ts              ← Module declaration
 * ├── network.routing.ts             ← Route configuration
 * ├── models/
 * │   └── network.model.ts           ← TypeScript interfaces
 * ├── services/
 * │   └── network.service.ts         ← API communication layer
 * └── components/
 *     ├── topology-container.component.ts  ← Parent with view toggle
 *     ├── network-tree.component.ts        ← MatTree hierarchy view
 *     ├── network-graph.component.ts       ← SVG graph view
 *     ├── nsg-detail-panel.component.ts    ← NSG detail view
 *     ├── nsg-rule-editor.component.ts     ← NSG rule table editor
 *     ├── nsg-rule-form-dialog.component.ts← NSG rule add/edit dialog
 *     └── vnet-detail.component.ts         ← VNet detail view
 * ```
 *
 * # Key Features
 *
 * - **Tree View**: Hierarchical MatTree showing VNet → Subnet → NSG → Rule hierarchy
 * - **Graph View**: SVG-based interactive network topology graph with drag-and-drop
 * - **NSG Detail Panel**: NSG properties, sync status badge, and embedded rule editor
 * - **NSG Rule Editor**: MatTable with columns for all rule properties, drag-drop reorder
 * - **NSG Rule Form Dialog**: Add/Edit dialog with priority uniqueness validation
 * - **VNet Detail**: Detailed view of a single Virtual Network
 * - **Search/Filter**: Filter nodes by name, type, location
 *
 * @module network-module
 * @author Network Module Team
 * @since 1.0.0
 */

import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule } from '@angular/material/sort';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { MatSelectModule } from '@angular/material/select';
import { CdkDragDrop, CdkDrag, CdkDropList, CdkDragHandle } from '@angular/cdk/drag-drop';

// Standalone components (already self-contained)
import { TopologyContainerComponent } from './components/topology-container/topology-container.component';
import { NetworkTreeComponent } from './components/network-tree/network-tree.component';
import { NetworkGraphComponent } from './components/network-graph/network-graph.component';
import { NsgDetailPanelComponent } from './components/nsg-detail-panel/nsg-detail-panel.component';
import { NsgRuleEditorComponent } from './components/nsg-rule-editor/nsg-rule-editor.component';
import { NsgRuleFormDialogComponent } from './components/nsg-rule-form-dialog/nsg-rule-form-dialog.component';

@NgModule({
    imports: [
        CommonModule,
        RouterModule,
        ReactiveFormsModule,
        FormsModule,
        MatButtonModule,
        MatIconModule,
        MatCardModule,
        MatProgressSpinnerModule,
        MatChipsModule,
        MatDividerModule,
        MatTabsModule,
        MatTableModule,
        MatSortModule,
        MatCheckboxModule,
        MatDialogModule,
        MatTooltipModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        CdkDrag,
        CdkDropList,
        CdkDragHandle,
    ],
    declarations: [],
    exports: [
        // Top-level container
        TopologyContainerComponent,
        // View components
        NetworkTreeComponent,
        NetworkGraphComponent,
        // NSG management components
        NsgDetailPanelComponent,
        NsgRuleEditorComponent,
        NsgRuleFormDialogComponent,
    ]
})
export class NetworkModule { }