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
 *     └── vnet-detail.component.ts         ← VNet detail view
 * ```
 *
 * # Key Features
 *
 * - **Tree View**: Hierarchical MatTree showing VNet → Subnet → NSG → Rule hierarchy
 * - **Graph View**: SVG-based interactive network topology graph with drag-and-drop
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

@NgModule({
    imports: [
        CommonModule,
        RouterModule,
        ReactiveFormsModule,
        MatButtonModule,
        MatIconModule,
        MatCardModule,
        MatProgressSpinnerModule,
        MatChipsModule,
        MatDividerModule,
        MatTabsModule
    ],
    declarations: [
        // Component declarations moved to network.components.ts
    ],
    exports: [
        // Component exports moved to network.components.ts
    ]
})
export class NetworkModule { }
