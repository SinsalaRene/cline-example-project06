/**
 * Audit Module
 *
 * Provides the audit log UI for viewing, filtering, searching, and exporting
 * system audit entries.
 */

import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuditListComponent } from './components/audit-list.component';
import { AuditService } from './services/audit.service';

const routes: Routes = [
    { path: '', component: AuditListComponent }
];

@NgModule({
    imports: [
        RouterModule.forChild(routes),
        AuditListComponent
    ],
    providers: [AuditService]
})
export class AuditModule { }

export { AuditListComponent, AuditService };
