/**
 * Workloads routing configuration for the Azure Firewall Management application.
 *
 * Defines the following routes:
 * - `workloads` → WorkloadsListComponent (list all workloads)
 * - `workloads/new` → WorkloadFormComponent (create new workload)
 * - `workloads/:id` → WorkloadDetailComponent (view workload details)
 * - `workloads/:id/edit` → WorkloadFormComponent (edit existing workload)
 *
 * @module workloads-routing
 */
import { Routes } from '@angular/router';
import { WorkloadsListComponent } from './components/workloads-list.component';
import { WorkloadDetailComponent } from './components/workload-detail.component';
import { WorkloadFormComponent } from './components/workload-form.component';

/**
 * Route configuration for the workloads module.
 *
 * Note: Static routes ('new') must be defined before parameterized routes (':id')
 * to ensure Angular Router matches them correctly.
 */
export const workloadsRoutes: Routes = [
    {
        path: '',
        component: WorkloadsListComponent,
        data: {
            title: 'Workloads'
        }
    },
    {
        path: 'new',
        component: WorkloadFormComponent,
        data: {
            title: 'Create Workload'
        }
    },
    {
        path: ':id/edit',
        component: WorkloadFormComponent,
        data: {
            title: 'Edit Workload'
        }
    },
    {
        path: ':id',
        component: WorkloadDetailComponent,
        data: {
            title: 'Workload Detail'
        }
    }
];