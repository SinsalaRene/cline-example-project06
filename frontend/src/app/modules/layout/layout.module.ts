import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import {
    MatSidenavModule,
    MatListModule,
    MatTabsModule,
    MatMenuModule,
    MatIconModule,
    MatButtonModule,
    MatDividerModule,
    MatProgressBarModule,
    MatTooltipModule,
    MatChipsModule,
    MatSnackBarModule
} from '@angular/material';

import { LayoutComponent } from './layout.component';
import { ErrorNotificationComponent } from '../../shared/components/error-notification/error-notification.component';
import { SharedModule } from '../../shared/shared.module';

/**
 * LayoutModule
 *
 * Provides the application layout infrastructure including:
 * - Side navigation with responsive behavior
 * - Top header bar with user menu and theme toggle
 * - Error notification system
 * - Theme management integration
 *
 * This module should be imported in AppModule to provide the main layout.
 *
 * @example
 * ```typescript
 * @NgModule({
 *   imports: [LayoutModule],
 *   // ...
 * })
 * export class AppModule {}
 * ```
 */
@NgModule({
    declarations: [
        LayoutComponent,
        ErrorNotificationComponent
    ],
    imports: [
        CommonModule,
        ReactiveFormsModule,
        SharedModule,
        MatSidenavModule,
        MatListModule,
        MatTabsModule,
        MatMenuModule,
        MatIconModule,
        MatButtonModule,
        MatDividerModule,
        MatProgressBarModule,
        MatTooltipModule,
        MatChipsModule,
        MatSnackBarModule
    ],
    exports: [
        LayoutComponent
    ]
})
export class LayoutModule { }