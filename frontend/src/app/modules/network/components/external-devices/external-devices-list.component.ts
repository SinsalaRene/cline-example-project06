/**
 * External Devices List Component
 *
 * Displays a MatTable of all external network devices with columns for Name,
 * IP Address, Device Type, Vendor, Model, and Contact Email. Provides action
 * buttons for Edit, Delete, and View Connections for each device.
 *
 * Features:
 * - **MatTable** with columns: Name, IP Address, Device Type, Vendor, Model, Contact Email
 * - **MatSort** for column-based sorting
 * - **Add Device** button opens ExternalDeviceFormDialog
 * - **Edit** button opens form dialog pre-filled with device data
 * - **Delete** button opens confirmation dialog
 * - **View Connections** opens connection detail view for the device
 *
 * @module external-devices-list-component
 * @author Network Module Team
 * @since 1.0.0
 */

import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';

import { NetworkService } from '../../services/network.service';
import { ExternalNetworkDevice, DeviceType, DEVICE_TYPE_LABELS } from '../../models/network.model';
import { ExternalDeviceFormDialogComponent, ExternalDeviceFormData } from './external-device-form/external-device-form-dialog.component';
import { ConfirmationDialogComponent, ConfirmationDialogData } from './confirmation-dialog/confirmation-dialog.component';

/** Column definitions for display in the table. */
export interface DeviceAction {
  name: 'edit' | 'delete' | 'connections';
  icon: string;
  label: string;
  color: 'accent' | 'warn' | 'primary';
}

/**
 * External Devices List Component.
 *
 * Displays and manages a sortable table of external network devices.
 * Supports CRUD operations through material dialogs.
 *
 * @selector app-external-devices-list
 * @standalone
 */
@Component({
  selector: 'app-external-devices-list',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatSortModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatDividerModule,
    MatChipsModule,
    MatMenuModule,
    MatInputModule,
    MatFormFieldModule,
    FormsModule,
  ],
  template: `
    <div class="external-devices-list">
      <!-- Header -->
      <div class="list-header">
        <div class="title-section">
          <h3>External Network Devices</h3>
          <span class="device-count">{{ devices.length }} device(s)</span>
        </div>
        <div class="action-section">
          <div class="search-box">
            <mat-form-field appearance="outline" class="search-input">
              <mat-icon matPrefix>search</mat-icon>
              <input matInput placeholder="Search devices..." [(ngModel)]="searchTerm" (input)="applyFilter()">
            </mat-form-field>
          </div>
          <button mat-raised-button color="primary" (click)="openAddDeviceDialog()" class="add-btn">
            <mat-icon>add</mat-icon>
            Add Device
          </button>
        </div>
      </div>

      <mat-divider />

      <!-- Loading spinner -->
      <div class="loading-container" *ngIf="isLoading">
        <mat-progress-spinner
          mode="indeterminate"
          diameter="40"
        ></mat-progress-spinner>
      </div>

      <!-- Devices Table -->
      <div class="table-container" *ngIf="!isLoading">
        <table mat-table [dataSource]="dataSource" matSort class="devices-table">

          <!-- Name Column -->
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Device Name</th>
            <td mat-cell *matCellDef="let device">
              <span class="device-name">{{ device.name }}</span>
              <span *ngIf="!device.isActive" class="status-badge inactive">Inactive</span>
            </td>
          </ng-container>

          <!-- IP Address Column -->
          <ng-container matColumnDef="ipAddress">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>IP Address</th>
            <td mat-cell *matCellDef="let device" class="ip-cell">
              {{ device.ipAddress || '*' }}
            </td>
          </ng-container>

          <!-- Device Type Column -->
          <ng-container matColumnDef="deviceType">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Device Type</th>
            <td mat-cell *matCellDef="let device">
              <mat-chip class="type-chip">
                {{ getDeviceTypeLabel(device.deviceType) }}
              </mat-chip>
            </td>
          </ng-container>

          <!-- Vendor Column -->
          <ng-container matColumnDef="vendor">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Vendor</th>
            <td mat-cell *matCellDef="let device">{{ device.vendor || '-' }}</td>
          </ng-container>

          <!-- Model Column -->
          <ng-container matColumnDef="model">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Model</th>
            <td mat-cell *matCellDef="let device">{{ device.model || '-' }}</td>
          </ng-container>

          <!-- Contact Email Column -->
          <ng-container matColumnDef="contactEmail">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Contact Email</th>
            <td mat-cell *matCellDef="let device">{{ device.contactEmail || '-' }}</td>
          </ng-container>

          <!-- Actions Column -->
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef class="actions-header">Actions</th>
            <td mat-cell *matCellDef="let device">
              <button mat-icon-button [matMenuTriggerFor]="menu" matTooltip="More actions">
                <mat-icon>more_vert</mat-icon>
              </button>
              <mat-menu #menu="matMenu">
                <button mat-menu-item (click)="viewConnections(device)">
                  <mat-icon color="primary">link</mat-icon>
                  <span>View Connections</span>
                </button>
                <button mat-menu-item (click)="openEditDeviceDialog(device)">
                  <mat-icon color="accent">edit</mat-icon>
                  <span>Edit</span>
                </button>
                <mat-divider></mat-divider>
                <button mat-menu-item (click)="deleteDevice(device)" class="delete-item">
                  <mat-icon color="warn">delete</mat-icon>
                  <span>Delete</span>
                </button>
              </mat-menu>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns; sticky: true"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
        </table>

        <!-- Empty state -->
        <div class="empty-state" *ngIf="dataSource.length === 0">
          <mat-icon>devices</mat-icon>
          <p>No external network devices found. Click "Add Device" to create one.</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .external-devices-list {
      display: flex;
      flex-direction: column;
      padding: 16px;
    }

    .list-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 16px;
      flex-wrap: wrap;
      gap: 16px;
    }

    .title-section {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .title-section h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 500;
    }

    .device-count {
      font-size: 12px;
      color: #666;
      background: #f5f5f5;
      padding: 2px 8px;
      border-radius: 12px;
    }

    .action-section {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .search-input {
      min-width: 200px;
    }

    .search-input mat-form-field {
      margin: 0;
    }

    .add-btn {
      margin-left: 8px;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 40px;
    }

    .table-container {
      overflow-x: auto;
      margin-top: 16px;
    }

    .devices-table {
      width: 100%;
    }

    .device-name {
      font-weight: 500;
    }

    .status-badge {
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 10px;
      margin-left: 8px;
    }

    .status-badge.inactive {
      background: #ffebee;
      color: #c62828;
    }

    .ip-cell {
      font-family: monospace;
      font-size: 12px;
    }

    .type-chip {
      font-size: 12px;
      font-weight: 500;
      text-transform: capitalize;
    }

    .actions-header {
      width: 40px;
      text-align: center;
    }

    .delete-item {
      color: #f44336 !important;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px;
      color: #999;
    }

    .empty-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      margin-bottom: 16px;
    }

    .empty-state p {
      margin: 0;
      font-size: 14px;
    }

    mat-divider {
      margin: 8px 0;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExternalDevicesListComponent implements OnInit, OnDestroy {
  /** Whether devices are being loaded. */
  isLoading = false;

  /** Search term for filtering devices. */
  searchTerm = '';

  /** The displayed external devices used by MatTableDataSource. */
  dataSource = new MatTableDataSource<ExternalNetworkDevice>();

  /** Column definitions for the table. */
  displayedColumns: string[] = [
    'name',
    'ipAddress',
    'deviceType',
    'vendor',
    'model',
    'contactEmail',
    'actions',
  ];

  /** Full array of loaded devices. */
  devices: ExternalNetworkDevice[] = [];

  /** The MatSort for column sorting. */
  sort = new MatSort();

  /** Subject to signal component destruction. */
  private destroy$ = new Subject<void>();

  /** Emits when devices are updated (for parent components). */
  devicesUpdated = new EventEmitter<void>();

  /**
   * Creates a new ExternalDevicesListComponent.
   *
   * @param networkService - The network service for API calls.
   * @param dialog - The Angular Material dialog service.
   */
  constructor(
    private networkService: NetworkService,
    public dialog: MatDialog
  ) { }

  /**
   * Lifecycle hook called after input binding.
   * Loads external devices from the service.
   */
  ngOnInit(): void {
    this.loadDevices();
  }

  /**
   * Lifecycle hook called before component destruction.
   * Cleans up subscriptions.
   */
  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Loads external devices from the service.
   */
  loadDevices(): void {
    this.isLoading = true;
    this.networkService.getExternalDevices().pipe(takeUntil(this.destroy$)).subscribe({
      next: (devices) => {
        this.devices = devices;
        this.dataSource.data = [...devices];
        if (this.sort) {
          this.dataSource.sort = this.sort;
        }
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to load external devices:', err);
        this.isLoading = false;
      },
    });
  }

  /**
   * Opens the Add Device dialog.
   */
  openAddDeviceDialog(): void {
    const formData: ExternalDeviceFormData = {
      device: null,
    };

    const dialogRef = this.dialog.open(ExternalDeviceFormDialogComponent, {
      data: formData,
      width: '600px',
      maxWidth: '90vw',
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.addDevice(result);
      }
    });
  }

  /**
   * Opens the Edit Device dialog pre-filled with device data.
   *
   * @param device - The device to edit.
   */
  openEditDeviceDialog(device: ExternalNetworkDevice): void {
    const formData: ExternalDeviceFormData = {
      device,
    };

    const dialogRef = this.dialog.open(ExternalDeviceFormDialogComponent, {
      data: formData,
      width: '600px',
      maxWidth: '90vw',
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.editDevice(device, result);
      }
    });
  }

  /**
   * Deletes a device after confirmation.
   *
   * @param device - The device to delete.
   */
  deleteDevice(device: ExternalNetworkDevice): void {
    const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
      data: {
        title: 'Delete External Device',
        message: `Are you sure you want to delete the device "${device.name}"?`,
        confirmLabel: 'Delete',
        cancelLabel: 'Cancel',
      } as ConfirmationDialogData,
    });

    dialogRef.afterClosed().subscribe((confirmed) => {
      if (confirmed) {
        this.confirmDeleteDevice(device);
      }
    });
  }

  /**
   * Confirms and executes device deletion.
   *
   * @param device - The device to delete.
   */
  confirmDeleteDevice(device: ExternalNetworkDevice): void {
    // Optimistic removal
    this.devices = this.devices.filter(d => d.id !== device.id);
    this.dataSource.data = this.dataSource.data.filter(d => d.id !== device.id);

    // Call service to delete
    this.networkService.deleteExternalDevice(device.id).subscribe({
      next: () => {
        this.devicesUpdated.emit();
      },
      error: (err) => {
        console.error('Failed to delete device:', err);
        this.loadDevices();
      },
    });
  }

  /**
   * Adds a new device.
   *
   * @param deviceData - The new device data.
   */
  addDevice(deviceData: Partial<ExternalNetworkDevice>): void {
    this.networkService.createExternalDevice(deviceData as any).subscribe({
      next: () => {
        this.loadDevices();
        this.devicesUpdated.emit();
      },
      error: (err) => {
        console.error('Failed to create device:', err);
        this.loadDevices();
      },
    });
  }

  /**
   * Updates an existing device.
   *
   * @param existingDevice - The existing device being updated.
   * @param deviceData - The updated device data.
   */
  editDevice(existingDevice: ExternalNetworkDevice, deviceData: Partial<ExternalNetworkDevice>): void {
    this.networkService.updateExternalDevice(existingDevice.id, deviceData as any).subscribe({
      next: () => {
        this.loadDevices();
        this.devicesUpdated.emit();
      },
      error: (err) => {
        console.error('Failed to update device:', err);
        this.loadDevices();
      },
    });
  }

  /**
   * Views connections for a device.
   * Emits the device ID for parent components to handle.
   *
   * @param device - The device to view connections for.
   */
  viewConnections(device: ExternalNetworkDevice): void {
    this.devicesUpdated.emit();
    // In integration, this would open a connection detail panel
    console.log('Viewing connections for device:', device.id);
  }

  /**
   * Applies search filtering to the data source.
   */
  applyFilter(): void {
    this.dataSource.filter = this.searchTerm.trim().toLowerCase();
  }

  /**
   * Gets the display label for a device type.
   *
   * @param type - The device type enum value.
   * @returns Display label string.
   */
  getDeviceTypeLabel(type: DeviceType | string): string {
    return DEVICE_TYPE_LABELS[type as DeviceType] || type;
  }
}



