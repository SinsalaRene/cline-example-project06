import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard, PublicGuard } from './core/guards/auth.guard';
import { LoginComponent } from './modules/auth/login/login.component';
import { LogoutComponent } from './modules/auth/logout/logout.component';

const routes: Routes = [
    { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
    {
        path: 'dashboard',
        canActivate: [AuthGuard],
        loadChildren: () => import('./modules/dashboard/dashboard.module').then(m => m.DashboardModule)
    },
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
    // Public routes (accessible when not logged in)
    {
        path: 'login',
        canActivate: [PublicGuard],
        component: LoginComponent
    },
    // Logout route
    {
        path: 'logout',
        component: LogoutComponent
    },
    { path: '**', redirectTo: '/dashboard' }
];

@NgModule({
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule]
})
export class AppRoutingModule { }