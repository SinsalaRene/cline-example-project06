import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard, ReverseAuthGuard, PublicGuard, RoleGuard, PermissionGuard } from './core/guards/auth.guard';
import { LoginComponent } from './modules/auth/login/login.component';
import { LogoutComponent } from './modules/auth/logout/logout.component';

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
    // Role-protected route example
    {
        path: 'admin',
        canActivate: [RoleGuard],
        data: { roles: ['admin'] },
        loadChildren: () => import('./modules/admin/admin.module').then(m => m.AdminModule)
    },
    // Permission-protected route example
    {
        path: 'settings',
        canActivate: [PermissionGuard],
        data: { permission: 'settings:write' },
        loadChildren: () => import('./modules/settings/settings.module').then(m => m.SettingsModule)
    },
    { path: '**', redirectTo: '/dashboard' }
];

@NgModule({
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule]
})
export class AppRoutingModule { }