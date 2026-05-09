/**
 * Impact Analysis Module
 *
 * Provides the impact analysis dialog component for viewing
 * the impact of NSG rule changes before committing them.
 *
 * @module impact-analysis-module
 * @author Network Module Team
 * @since 1.0.0
 */

import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBarModule } from '@angular/material/snack-bar';

import { ImpactAnalysisDialogComponent } from './impact-analysis-dialog.component';

@NgModule({
    declarations: [ImpactAnalysisDialogComponent],
    imports: [
        CommonModule,
        MatDialogModule,
        MatButtonModule,
        MatIconModule,
        MatDividerModule,
        MatProgressSpinnerModule,
        MatTableModule,
        MatChipsModule,
        MatSnackBarModule,
    ],
    exports: [ImpactAnalysisDialogComponent],
})
export class ImpactAnalysisModule { }