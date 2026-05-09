/**
 * External Devices Module
 *
 * Feature module for external network device management and impact analysis.
 * Provides list, form, and detail components for external devices, plus
 * the impact analysis dialog and connection manager.
 *
 * @module external-devices-module
 * @author Network Module Team
 * @since 1.0.0
 */

import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ExternalDevicesListComponent } from './external-devices-list.component';
import { ExternalDeviceFormDialogComponent } from './external-device-form/external-device-form-dialog.component';
import { ExternalDeviceDetailComponent } from './external-device-detail/external-device-detail.component';
import { ConfirmationDialogComponent } from './confirmation-dialog/confirmation-dialog.component';

@NgModule({
    declarations: [
        ExternalDevicesListComponent,
        ExternalDeviceFormDialogComponent,
        ExternalDeviceDetailComponent,
        ConfirmationDialogComponent,
    ],
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        MatInputModule,
        MatFormFieldModule,
        MatButtonModule,
        MatDialogModule,
        MatIconModule,
        MatChipsModule,
        MatSelectModule,
        MatCheckboxModule,
        MatCardModule,
        MatProgressSpinnerModule,
        ExternalDeviceFormDialogComponent,
        ExternalDeviceDetailComponent,
    ],
    exports: [
        ExternalDevicesListComponent,
        ExternalDeviceFormDialogComponent,
        ExternalDeviceDetailComponent,
        ConfirmationDialogComponent,
    ],
})
export class ExternalDevicesModule { }