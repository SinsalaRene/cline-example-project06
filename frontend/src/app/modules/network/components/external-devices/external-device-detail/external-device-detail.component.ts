/**
 * External Device Detail Component
 *
 * Displays detailed information about an external network device including
 * all its properties and a list of connections to/from this device.
 *
 * Features:
 * - Card-based display of all device properties
 * - List of connections to/from this device
 * - Edit and Delete buttons
 *
 * @module external-device-detail
 * @author Network Module Team
 * @since 1.0.0
 */

import { Component, OnInit, Input, Output, EventEmitter, ChangeDetectionStrategy, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { Subject, takeUntil } from 'rxjs';

import { ExternalNetworkDevice, DeviceType, DEVICE_TYPE_LABELS } from '../../../models/network.model';
import { NetworkService } from '../../../services/network.service';
import { NetworkConnection, ConnectionType, CONNECTION_TYPE_LABELS } from '../../../models/network.model';

/**
 * External Device Detail Component.
 *
 * @selector app-external-device-detail
 * @standalone
 */
@Component({
  selector: 'app-external-device-detail',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatDividerModule,
    MatChipsModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatTableModule,
  ],
  template: `
    <div class="device-detail" *ngIf="device">
      <!-- Device Info Card -->
      <mat-card class="device-info-card">
        <mat-card-header>
          <mat-card-title>
            <mat-icon class="device-icon" color="primary">{{ getDeviceIcon(device.deviceType) }}</mat-icon>
            {{ device.name }}
          </mat-card-title>
          <mat-card-subtitle>
            <span class="device-type-chip">
              {{ getDeviceTypeLabel(device.deviceType) }}
            </span>
            <span *ngIf="device.vendor" class="vendor-badge">{{ device.vendor }}</span>
          </mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">IP Address</span>
              <span class="info-value">
                <mat-icon color="accent" class="info-icon">public</mat-icon>
                {{ device.ipAddress || 'N/A' }}
              </span>
            </div>
            <div class="info-item" *ngIf="device.model">
              <span class="info-label">Model</span>
              <span class="info-value">{{ device.model }}</span>
            </div>
            <div class="info-item" *ngIf="device.contactName">
              <span class="info-label">Contact</span>
              <span class="info-value">{{ device.contactName }}</span>
            </div>
            <div class="info-item" *ngIf="device.contactEmail">
              <span class="info-label">Email</span>
              <span class="info-value">
                <mat-icon color="accent" class="info-icon">email</mat-icon>
                {{ device.contactEmail }}
              </span>
            </div>
            <div class="info-item" *ngIf="device.contactPhone">
              <span class="info-label">Phone</span>
              <span class="info-value">
                <mat-icon color="accent" class="info-icon">phone</mat-icon>
                {{ device.contactPhone }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">Status</span>
              <span class="info-value">
                <mat-icon [color]="device.isActive ? 'primary' : 'warn'" class="info-icon">
                  {{ device.isActive ? 'check_circle' : 'cancel' }}
                </mat-icon>
                {{ device.isActive ? 'Active' : 'Inactive' }}
              </span>
            </div>
            <div class="info-item full-width" *ngIf="device.notes">
              <span class="info-label">Notes</span>
              <span class="info-value">{{ device.notes }}</span>
            </div>
            <div class="info-item full-width" *ngIf="device.tags?.length">
              <span class="info-label">Tags</span>
              <span class="tags-container">
                <mat-chip *ngFor="let tag of device.tags.split(', ').filter(t => t)">{{ tag }}</mat-chip>
              </span>
            </div>
          </div>
        </mat-card-content>
        <mat-card-actions align="end">
          <button mat-raised-button color="primary" (click)="edit.emit()">
            <mat-icon matPrefix>edit</mat-icon>
            Edit
          </button>
          <button mat-raised-button color="warn" (click)="delete.emit()">
            <mat-icon matPrefix>delete</mat-icon>
            Delete
          </button>
        </mat-card-actions>
      </mat-card>

      <!-- Connections Section -->
      <mat-card class="connections-card" *ngIf="connections.length > 0">
        <mat-card-header>
          <mat-card-title>Network Connections</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <table mat-table [dataSource]="dataSource">
            <!-- Source Column -->
            <ng-container matColumnDef="source">
              <th mat-header-cell *matHeaderCellDef>Source</th>
              <td mat-cell *matCellDef="let conn">{{ getSourceName(conn) }}</td>
            </ng-container>

            <!-- Destination Column -->
            <ng-container matColumnDef="destination">
              <th mat-header-cell *matHeaderCellDef>Destination</th>
              <td mat-cell *matCellDef="let conn">{{ getDestinationName(conn) }}</td>
            </ng-container>

            <!-- Connection Type Column -->
            <ng-container matColumnDef="connectionType">
              <th mat-header-cell *matHeaderCellDef>Type</th>
              <td mat-cell *matCellDef="let conn">
                <mat-chip>{{ getConnectionTypeLabel(conn.connectionType) }}</mat-chip>
              </td>
            </ng-container>

            <!-- Description Column -->
            <ng-container matColumnDef="description">
              <th mat-header-cell *matHeaderCellDef>Description</th>
              <td mat-cell *matCellDef="let conn">{{ conn.description || '-' }}</td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
          </table>
        </mat-card-content>
      </mat-card>

      <!-- Empty connections message -->
      <div class="empty-state" *ngIf="connections.length === 0">
        <mat-icon>link_off</mat-icon>
        <p>No connections found for this device.</p>
      </div>

      <!-- Loading -->
      <div class="loading-container" *ngIf="isLoading">
        <mat-progress-spinner mode="indeterminate" diameter="40"></mat-progress-spinner>
      </div>
    </div>
  `,
  styles: [`
    .device-detail {
      padding: 16px;
    }

    .device-info-card {
      margin-bottom: 16px;
    }

    .device-info-card mat-card-header {
      margin-bottom: 16px;
    }

    .device-info-card mat-card-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .device-info-card mat-card-title .device-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
    }

    .device-info-card mat-card-subtitle {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .device-type-chip {
      font-size: 12px;
      font-weight: 500;
      background: #e3f2fd;
      color: #1976d2;
      padding: 2px 8px;
      border-radius: 12px;
      text-transform: capitalize;
    }

    .vendor-badge {
      font-size: 12px;
      color: #666;
      background: #f5f5f5;
      padding: 2px 8px;
      border-radius: 12px;
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }

    .info-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .info-item.full-width {
      grid-column: 1 / -1;
    }

    .info-label {
      font-size: 12px;
      color: #666;
      text-transform: uppercase;
    }

    .info-value {
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .info-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .tags-container {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }

    .connections-card {
      margin-bottom: 16px;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px;
      color: #999;
      text-align: center;
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

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 40px;
    }

    mat-divider {
      margin: 8px 0;
    }

    table {
      width: 100%;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExternalDeviceDetailComponent implements OnInit, OnDestroy {
  /** The external device to display. */
  @Input() device: ExternalNetworkDevice | null = null;

  /** Emits when the user clicks Edit. */
  @Output() edit = new EventEmitter<void>();

  /** Emits when the user clicks Delete. */
  @Output() delete = new EventEmitter<void>();

  /** Connection data source for the table. */
  dataSource = new MatTableDataSource<NetworkConnection>();

  /** Displayed columns for the connections table. */
  displayedColumns: string[] = ['source', 'destination', 'connectionType', 'description'];

  /** Whether connections are being loaded. */
  isLoading = false;

  /** All connections for this device. */
  connections: NetworkConnection[] = [];

  /** Subject to signal component destruction. */
  private destroy$ = new Subject<void>();

  /**
   * Creates a new ExternalDeviceDetailComponent.
   *
   * @param networkService - The network service for API calls.
   */
  constructor(private networkService: NetworkService) { }

  /**
   * Lifecycle hook called after input binding.
   * Loads connections for the device.
   */
  ngOnInit(): void {
    if (this.device) {
      this.loadConnections();
    }
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
   * Sets the device and loads connections when device input changes.
   *
   * @param val - The new device value.
   */
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  static ngOnChanges(_changes: any): void { }

  /**
   * Loads connections for the device.
   */
  loadConnections(): void {
    if (!this.device) return;

    this.isLoading = true;
    this.networkService.getConnectionsByDevice(this.device.id).pipe(takeUntil(this.destroy$)).subscribe({
      next: (connections) => {
        this.connections = connections;
        this.dataSource.data = connections;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to load connections:', err);
        this.isLoading = false;
      },
    });
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

  /**
   * Gets the Material icon for a device type.
   *
   * @param type - The device type enum value.
   * @returns Material icon name.
   */
  getDeviceIcon(type: DeviceType | string): string {
    switch (type) {
      case DeviceType.ROUTER:
        return 'router';
      case DeviceType.SWITCH:
        return 'dns';
      case DeviceType.FIREWALL:
        return 'security';
      default:
        return 'devices';
    }
  }

  /**
   * Gets the display label for a connection type.
   *
   * @param type - The connection type enum value.
   * @returns Display label string.
   */
  getConnectionTypeLabel(type: ConnectionType | string): string {
    return CONNECTION_TYPE_LABELS[type as ConnectionType] || type;
  }

  /**
   * Gets the source name for display.
   *
   * @param conn - The connection.
   * @returns Source name string.
   */
  getSourceName(conn: NetworkConnection): string {
    return `${conn.sourceType}:${conn.sourceId}`;
  }

  /**
   * Gets the destination name for display.
   *
   * @param conn - The connection.
   * @returns Destination name string.
   */
  getDestinationName(conn: NetworkConnection): string {
    return `${conn.destinationType}:${conn.destinationId}`;
  }
}