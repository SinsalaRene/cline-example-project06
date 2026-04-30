import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from './core/guards/auth.guard';

const routes: Routes = [
    { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
    {
        path: 'rules',
        canActivate: [AuthGuard],
        loadChildren: () => import('./modules/rules/rules.module').then(m => m.RulesModule)
    },
    {
        path: 'approvals',
        canActivate: [AuthGuard],
        loadChildren: () => import('./modules/approvals/approvals.module').then(m => m.ApprovalsModule)
    },
    {
        path: 'audit',
        canActivate: [AuthGuard],
        loadChildren: () => import('./modules/audit/audit.module').then(m => m.AuditModule)
    },
    {
        path: 'workloads',
        canActivate: [AuthGuard],
        loadChildren: () => import('./modules/workloads/workloads.module').then(m => m.WorkloadsModule)
    },
    { path: 'login', loadComponent: () => import('./components/login/login.component').then(m => m.LoginComponent) },
    { path: '**', redirectTo: '/dashboard' }
];

@NgModule({
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule]
})
export class AppRoutingModule { }