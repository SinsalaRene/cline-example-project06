import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatTabsModule } from '@angular/material/tabs';
import { MatMenuModule } from '@angular/material/menu';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBarModule } from '@angular/material/snack-bar';

import { ErrorNotificationComponent } from '../../shared/components/error-notification/error-notification.component';
import { LayoutComponent } from './layout.component';
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
    declarations: [],
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
        MatSnackBarModule,
        LayoutComponent,
        ErrorNotificationComponent
    ],
    exports: [
        LayoutComponent
    ]
})
export class LayoutModule { }