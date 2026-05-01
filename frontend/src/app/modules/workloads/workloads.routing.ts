import { Routes } from '@angular/router';
import { WorkloadsListComponent } from './components/workloads-list.component';
import { WorkloadDetailComponent } from './components/workload-detail.component';
import { WorkloadFormComponent } from './components/workload-form.component';

export const workloadsRoutes: Routes = [
    {
        path: '',
        component: WorkloadsListComponent,
        data: {
            title: 'Workloads'
        }
    },
    {
        path: 'create',
        component: WorkloadFormComponent,
        data: {
            title: 'Create Workload'
        }
    },
    {
        path: ':id',
        component: WorkloadDetailComponent,
        data: {
            title: 'Workload Detail'
        }
    },
    {
        path: ':id/edit',
        component: WorkloadFormComponent,
        data: {
            title: 'Edit Workload'
        }
    }
];