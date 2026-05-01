/**
 * Audit Module
 *
 * Provides the audit log UI for viewing, filtering, searching, and exporting
 * system audit entries. It supports:
 *
 * - List view with search, filtering, and pagination
 * - Multi-criteria filtering (date, action, resource type, severity, user, result)
 * - Detailed entry view with change diff display
 * - Export to CSV and JSON formats
 * - Summary statistics dashboard
 * - Responsive layout
 *
 * # Usage
 *
 * Import components directly (all are standalone components):
 *
 * @example
 * ```typescript
 * import { AuditViewerComponent } from './audit/components/audit-viewer.component';
 * ```
 */

// Barrel exports - re-export all audit-related modules
export { AuditViewerComponent } from './components/audit-viewer.component';
export { AuditDetailComponent } from './components/audit-detail.component';
export { AuditService } from './services/audit.service';
export * from './models/audit.model';

/**
 * AuditModule is a convenience barrel module that re-exports all audit-related components,
 * services, and models for easy imports.
 *
 * All components in this module are standalone and can be imported individually.
 */
export class AuditModule { }
