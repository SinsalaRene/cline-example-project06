/**
 * Network Routing
 *
 * Route configuration for the network topology module.
 *
 * Defines lazy-loaded routes for the network module and nested routes
 * for VNet detail views.
 *
 * @module network-routing
 * @author Network Module Team
 */

import { Routes } from '@angular/router';
import { TopologyContainerComponent } from './components/topology-container/topology-container.component';
import { VnetDetailComponent } from './components/vnet-detail/vnet-detail.component';

/**
 * Route definitions for the network module.
 *
 * - `network` → TopologyContainerComponent (default view with tree/graph toggle)
 * - `network/vnets/:id` → VnetDetailComponent (detail view of a specific VNet)
 * - `**` → redirect to network
 */
export const NETWORK_ROUTES: Routes = [
    {
        path: '',
        component: TopologyContainerComponent,
        data: { title: 'Network Topology' }
    },
    {
        path: 'vnets/:id',
        component: VnetDetailComponent,
        data: { title: 'VNet Detail' }
    },
    {
        path: '**',
        redirectTo: '',
        pathMatch: 'full'
    }
];