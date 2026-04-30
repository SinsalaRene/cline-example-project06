import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import {
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
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
    MatPaginatorModule as MatPaginatorM2,
    MatDatepickerModule,
    MatNativeDateModule,
    MatRadioModule,
    MatCheckboxModule,
    MatSnackBarModule,
    MatProgressBarModule,
    MatDividerModule,
    MatStepperModule,
    MatAutocompleteModule
} from '@angular/material';

/**
 * SharedModule
 *
 * Provides a centralized place for common Angular Material modules,
 * Angular forms, and common directives/pipes that are shared across
 * multiple feature modules.
 *
 * This module exports commonly used modules so that feature modules
 * can import them once here instead of importing each module individually.
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
        // Custom pipes will be declared here as they are created
        // e.g., CustomPipe, FormatDatePipe, etc.
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
        MatAutocompleteModule,

        // Buttons & Actions
        MatButtonModule,
        MatMenuModule,

        // Icons & Media
        MatIconModule,

        // Layout & Containers
        MatCardModule,
        MatDividerModule,
        MatListModule,
        MatSidenavModule,

        // Navigation & Tabs
        MatTabsModule,
        MatStepperModule,

        // Overlays & Dialogs
        MatDialogModule,
        MatTooltipModule,
        MatSnackBarModule,

        // Progress & Loading
        MatProgressSpinnerModule,
        MatProgressBarModule,

        // Expansion
        MatExpansionModule,

        // Chips
        MatChipsModule,
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
        MatAutocompleteModule,
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
        MatProgressBarModule,
        MatDividerModule,
        MatStepperModule,
    ],
})
export class SharedModule { }