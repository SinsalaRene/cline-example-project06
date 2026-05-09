/**
 * Connection Manager Module
 *
 * Provides the connection manager component for managing
 * network connections between network entities.
 *
 * @module connection-manager-module
 * @author Network Module Team
 * @since 1.0.0
 */

import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';

import { ConnectionManagerComponent, ConnectionFormDialogComponent } from './connection-manager.component';

@NgModule({
    declarations: [ConnectionFormDialogComponent],
    imports: [
        CommonModule,
        ReactiveFormsModule,
        ConnectionManagerComponent,
    ],
    exports: [ConnectionManagerComponent, ConnectionFormDialogComponent],
})
export class ConnectionManagerModule { }