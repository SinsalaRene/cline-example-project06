import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatDialogModule } from '@angular/material/dialog';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatRadioModule } from '@angular/material/radio';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBarModule } from '@angular/material/snack-bar';

// Shared Components
import { LoadingSpinnerComponent } from './components/loading-spinner/loading-spinner.component';
import { ErrorNotificationComponent, ErrorNotificationService } from './components/error-notification/error-notification.component';
import { ConfirmDialogComponent } from './components/confirm-dialog/confirm-dialog.component';

// Shared Directives
import { LoadingDirective } from './directives/loading.directive';

/**
 * SharedModule
 *
 * Provides a centralized place for common Angular Material modules,
 * Angular forms, shared components, directives, and services.
 *
 * This module exports:
 * - Angular CommonModule
 * - Angular Forms (ReactiveFormsModule, FormsModule)
 * - Angular Material Modules (table, form, buttons, dialogs, etc.)
 * - LoadingSpinnerComponent
 * - ErrorNotificationComponent
 * - ConfirmDialogComponent
 * - LoadingDirective
 *
 * Usage: Import SharedModule in any feature module that needs these shared dependencies.
 *
 * @example
 * ```typescript
 * @NgModule({
 *   imports: [SharedModule],
 *   // ...
 * })
 * export class MyFeatureModule {}
 * ```
 */
@NgModule({
    declarations: [
        // No custom directives/pipes declared here - all are standalone
    ],
    imports: [
        // Angular CommonModule
        CommonModule,

        // Angular Forms
        ReactiveFormsModule,
        FormsModule,

        // Angular Material Modules
        // Table
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,

        // Forms & Inputs
        MatInputModule,
        MatFormFieldModule,
        MatSelectModule,
        MatRadioModule,
        MatCheckboxModule,
        MatDatepickerModule,
        MatNativeDateModule,

        // Buttons & Actions
        MatButtonModule,
        MatMenuModule,

        // Icons & Media
        MatIconModule,

        // Layout & Containers
        MatCardModule,
        MatListModule,
        MatSidenavModule,

        // Navigation & Tabs
        MatTabsModule,

        // Overlays & Dialogs
        MatDialogModule,
        MatTooltipModule,
        MatSnackBarModule,

        // Progress & Loading
        MatProgressSpinnerModule,

        // Expansion
        MatExpansionModule,

        // Chips
        MatChipsModule,

        // Shared Components (standalone)
        LoadingSpinnerComponent,
        ErrorNotificationComponent,
        ConfirmDialogComponent,

        // Shared Directives (standalone)
        LoadingDirective,
    ],
    exports: [
        // Re-export all imports so consuming modules can use them directly
        CommonModule,
        ReactiveFormsModule,
        FormsModule,
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        MatInputModule,
        MatFormFieldModule,
        MatSelectModule,
        MatRadioModule,
        MatCheckboxModule,
        MatDatepickerModule,
        MatNativeDateModule,
        MatButtonModule,
        MatIconModule,
        MatCardModule,
        MatTabsModule,
        MatDialogModule,
        MatListModule,
        MatProgressSpinnerModule,
        MatExpansionModule,
        MatChipsModule,
        MatSidenavModule,
        MatMenuModule,
        MatTooltipModule,
        MatSnackBarModule,

        // Shared Components
        LoadingSpinnerComponent,
        ErrorNotificationComponent,
        ConfirmDialogComponent,

        // Shared Directives
        LoadingDirective,
    ],
})
export class SharedModule { }