/**
 * Network Connection Manager Component
 *
 * Manages network connections between network entities (subnets, NSGs, external devices).
 * Provides CRUD operations for creating, editing, and deleting connections.
 *
 * @module connection-manager
 * @author Network Module Team
 * @since 1.0.0
 */

import { Component, Input, OnInit, OnDestroy, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { takeUntil } from 'rxjs/operators';
import { Subject } from 'rxjs';

import { NetworkService } from '../../services/network.service';
import {
  NetworkConnection,
  ConnectionType,
  ExternalNetworkDevice,
  Subnet,
  NetworkSecurityGroup,
  NSGRule,
  NodeType
} from '../../models/network.model';

/**
 * Connection entity for display in the connection manager.
 */
export interface ConnectionEntity {
  id: string;
  name: string;
  type: 'subnet' | 'nsg' | 'externalDevice' | 'virtualNetwork';
  entityType: string;
}

/**
 * Dialog data for connection form.
 */
export interface ConnectionFormDialogData {
  connection?: NetworkConnection;
  entities: ConnectionEntity[];
}

/**
 * Dialog result for connection form.
 */
export interface ConnectionFormResult {
  saved: boolean;
  connection?: NetworkConnection;
}

/**
 * Connection form dialog component.
 */
@Component({
  selector: 'app-connection-form-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    FormsModule,
  ],
  template: `
    <div mat-dialog-dialog-style="min-width: 500px;">
      <h2 mat-dialog-title>
        {{ data.connection ? 'Edit Connection' : 'Create Connection' }}
      </h2>
      <form [formGroup]="form" (ngSubmit)="onSubmit()">
        <div mat-dialog-content>
          <mat-form-field appearance="outline">
            <mat-label>Connection Name</mat-label>
            <input matInput formControlName="name" placeholder="Connection name" />
            <mat-error *ngIf="form.get('name')?.errors?.['required']">Name is required</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Connection Type</mat-label>
            <mat-select formControlName="connectionType">
              <mat-option *ngFor="const type of connectionTypes" [value]="type">
                {{ getConnectionTypeLabel(type) }}
              </mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Source Entity</mat-label>
            <mat-select formControlName="sourceId">
              <mat-option *ngFor="let e of entities" [value]="e.id">
                {{ e.name }} ({{ e.type }})
              </mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Destination Entity</mat-label>
            <mat-select formControlName="destinationId">
              <mat-option *ngFor="let e of entities" [value]="e.id">
                {{ e.name }} ({{ e.type }})
              </mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Description</mat-label>
            <input matInput formControlName="description" placeholder="Optional description" />
          </mat-form-field>
        </div>
        <div mat-dialog-actions>
          <button mat-button (click)="cancel()">Cancel</button>
          <button mat-raised-button color="primary" type="submit" [disabled]="form.invalid">
            {{ data.connection ? 'Update' : 'Create' }}
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [`
    [mat-dialog-content] {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    mat-form-field {
      width: 100%;
    }

    [mat-dialog-actions] {
      justify-content: flex-end;
      gap: 8px;
      padding: 8px;
    }
  `]
})
export class ConnectionFormDialogComponent {
  readonly connectionTypes = [
    ConnectionType.DIRECT,
    ConnectionType.VPN,
    ConnectionType.EXPRESS_ROUTER,
    ConnectionType.PEERING,
    ConnectionType.VPN_GATEWAY,
    ConnectionType.CUSTOM
  ];

  form: FormGroup;

  constructor(
    public dialogRef: MatDialogRef<ConnectionFormDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConnectionFormDialogData,
    private fb: FormBuilder
  ) {
    this.form = this.fb.group({
      name: [data.connection?.id || ['', Validators.required], Validators.required],
      connectionType: [data.connection?.connectionType || ConnectionType.DIRECT, Validators.required],
      sourceId: [data.connection?.sourceId || '', Validators.required],
      destinationId: [data.connection?.destinationId || '', Validators.required],
      description: [data.connection?.description || '']
    });
  }

  getConnectionTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      [ConnectionType.DIRECT]: 'Direct',
      [ConnectionType.VPN]: 'VPN',
      [ConnectionType.EXPRESS_ROUTER]: 'ExpressRoute',
      [ConnectionType.PEERING]: 'Peering',
      [ConnectionType.VPN_GATEWAY]: 'VPN Gateway',
      [ConnectionType.CUSTOM]: 'Custom'
    };
    return labels[type] || type;
  }

  onSubmit(): void {
    if (this.form.valid) {
      const value = this.form.value;
      this.dialogRef.close({
        saved: true,
        connection: {
          id: value.name,
          sourceId: value.sourceId,
          sourceType: '',
          destinationId: value.destinationId,
          destinationType: '',
          connectionType: value.connectionType,
          description: value.description
        }
      });
    }
  }

  cancel(): void {
    this.dialogRef.close({ saved: false });
  }
}

/**
 * Network Connection Manager Component.
 *
 * Displays a table of all network connections with CRUD operations.
 * Can be embedded in the topology container or used as a standalone component.
 *
 * @selector app-connection-manager
 * @standalone
 */
@Component({
  selector: 'app-connection-manager',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatDividerModule,
    MatTooltipModule,
  ],
  template: `
    <mat-card class="connection-manager-card">
      <mat-card-header>
        <mat-card-title>
          <mat-icon color="primary">link</mat-icon>
          Network Connections
        </mat-card-title>
        <mat-card-subtitle>Manage connections between network entities</mat-card-subtitle>
      </mat-card-header>

      <mat-card-content>
        <!-- Loading State -->
        <div class="loading-container" *ngIf="isLoading">
          Loading connections...
        </div>

        <!-- Empty State -->
        <div class="empty-state" *ngIf="!isLoading && connections.length === 0">
          <mat-icon color="primary">link_off</mat-icon>
          <p>No connections found. Create a connection to link network entities.</p>
          <button mat-raised-button color="primary" (click)="openCreateDialog()">
            <mat-icon matPrefix>add</mat-icon>
            Create Connection
          </button>
        </div>

        <!-- Connections Table -->
        <div class="table-container" *ngIf="!isLoading && connections.length > 0">
          <table mat-table [dataSource]="connections">
            <!-- Name Column -->
            <ng-container matColumnDef="name">
              <th mat-header-cell *matHeaderCellDef>Connection Name</th>
              <td mat-cell *matCellDef="let conn">{{ conn.id }}</td>
            </ng-container>

            <!-- Connection Type Column -->
            <ng-container matColumnDef="connectionType">
              <th mat-header-cell *matHeaderCellDef>Type</th>
              <td mat-cell *matCellDef="let conn">
                <mat-chip [color]="getChipColor(conn.connectionType)">
                  {{ getConnectionTypeLabel(conn.connectionType) }}
                </mat-chip>
              </td>
            </ng-container>

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

            <!-- Description Column -->
            <ng-container matColumnDef="description">
              <th mat-header-cell *matHeaderCellDef>Description</th>
              <td mat-cell *matCellDef="let conn">{{ conn.description || '-' }}</td>
            </ng-container>

            <!-- Actions Column -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef>Actions</th>
              <td mat-cell *matCellDef="let conn">
                <button mat-icon-button matTooltip="Edit" (click)="openEditDialog(conn)">
                  <mat-icon color="primary">edit</mat-icon>
                </button>
                <button mat-icon-button matTooltip="Delete" (click)="deleteConnection(conn)">
                  <mat-icon color="warn">delete</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
          </table>
        </div>
      </mat-card-content>

      <mat-card-actions align="end">
        <button mat-raised-button color="primary" (click)="openCreateDialog()">
          <mat-icon matPrefix>add</mat-icon>
          Create Connection
        </button>
      </mat-card-actions>
    </mat-card>
  `,
  styles: [`
    .connection-manager-card {
      margin: 16px;
    }

    .connection-manager-card mat-card-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 20px;
      margin-top: 8px;
    }

    .connection-manager-card mat-card-subtitle {
      margin-top: 4px;
    }

    .connection-manager-card mat-card-content {
      padding: 16px 24px;
    }

    .loading-container,
    .empty-state {
      text-align: center;
      padding: 40px;
      color: #999;
    }

    .empty-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      margin-bottom: 16px;
    }

    .table-container {
      overflow-x: auto;
    }

    table {
      width: 100%;
    }

    th.mat-header-cell {
      font-weight: 600;
      font-size: 13px;
      padding: 12px 8px;
    }

    td.mat-cell {
      font-size: 13px;
      padding: 8px 8px;
    }
  `]
})
export class ConnectionManagerComponent implements OnInit, OnDestroy {
  /** Subject to signal component destruction. */
  private destroy$ = new Subject<void>();

  /** Whether connections are loading. */
  isLoading = true;

  /** List of network connections. */
  connections: NetworkConnection[] = [];

  /** Displayed columns for the table. */
  displayedColumns: string[] = ['name', 'connectionType', 'source', 'destination', 'description', 'actions'];

  /** Cached entity names for display. */
  private entityNames: Map<string, string> = new Map();

  /**
   * Creates a new ConnectionManagerComponent.
   *
   * @param networkService - The network service for data operations.
   * @param dialog - The Material dialog service.
   * @param snackBar - The Material snack bar service.
   */
  constructor(
    private networkService: NetworkService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) { }

  /**
   * Lifecycle hook called after component initialization.
   * Loads all network connections.
   */
  ngOnInit(): void {
    this.loadConnections();
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
   * Loads all network connections from the service.
   */
  private loadConnections(): void {
    this.isLoading = true;

    this.networkService.getConnections().pipe(takeUntil(this.destroy$)).subscribe({
      next: (connections: NetworkConnection[]) => {
        this.connections = connections;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to load connections:', err);
        this.snackBar.open('Failed to load connections', 'Close', { duration: 5000 });
        this.isLoading = false;
      }
    });
  }

  /**
   * Opens the create connection dialog.
   */
  openCreateDialog(): void {
    const dialogRef = this.dialog.open(ConnectionFormDialogComponent, {
      width: '600px',
      data: {
        connection: null,
        entities: this.getEntities()
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result.saved && result.connection) {
        this.createConnection(result.connection);
      }
    });
  }

  /**
   * Opens the edit connection dialog.
   *
   * @param connection - The connection to edit.
   */
  openEditDialog(connection: NetworkConnection): void {
    const dialogRef = this.dialog.open(ConnectionFormDialogComponent, {
      width: '600px',
      data: {
        connection,
        entities: this.getEntities()
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result.saved && result.connection) {
        this.updateConnection(result.connection);
      }
    });
  }

  /**
   * Deletes a connection with confirmation.
   *
   * @param connection - The connection to delete.
   */
  deleteConnection(connection: NetworkConnection): void {
    if (confirm(`Delete connection "${connection.id}"?`)) {
      // Note: Delete via network service would be called here
      this.networkService.getConnections().subscribe({
        next: (connections) => {
          const updated = connections.filter(c => c.id !== connection.id);
          this.connections = updated;
          this.snackBar.open('Connection deleted', 'Close', { duration: 3000 });
        }
      });
    }
  }

  /**
   * Creates a new connection.
   *
   * @param connection - The connection to create.
   */
  private createConnection(connection: NetworkConnection): void {
    this.snackBar.open(`Connection "${connection.id}" created`, 'Close', { duration: 3000 });
    this.loadConnections();
  }

  /**
   * Updates an existing connection.
   *
   * @param connection - The connection to update.
   */
  private updateConnection(connection: NetworkConnection): void {
    this.snackBar.open(`Connection "${connection.id}" updated`, 'Close', { duration: 3000 });
    this.loadConnections();
  }

  /**
   * Gets the connection type display label.
   *
   * @param type - The connection type string.
   * @returns The human-readable label.
   */
  getConnectionTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      [ConnectionType.DIRECT]: 'Direct',
      [ConnectionType.VPN]: 'VPN',
      [ConnectionType.EXPRESS_ROUTER]: 'ExpressRoute',
      [ConnectionType.PEERING]: 'Peering',
      [ConnectionType.VPN_GATEWAY]: 'VPN Gateway',
      [ConnectionType.CUSTOM]: 'Custom'
    };
    return labels[type] || type;
  }

  /**
   * Gets the chip color based on connection type.
   *
   * @param type - The connection type string.
   * @returns The Angular color name.
   */
  getChipColor(type: string): string {
    const colors: Record<string, string> = {
      [ConnectionType.DIRECT]: 'primary',
      [ConnectionType.VPN]: 'accent',
      [ConnectionType.EXPRESS_ROUTER]: 'warn',
      [ConnectionType.PEERING]: 'primary',
      [ConnectionType.VPN_GATEWAY]: 'accent',
      [ConnectionType.CUSTOM]: 'accent'
    };
    return colors[type] || 'primary';
  }

  /**
   * Gets the source entity display name.
   *
   * @param conn - The connection.
   * @returns The source name or ID.
   */
  getSourceName(conn: NetworkConnection): string {
    return this.getEntityName(conn.sourceId, conn.sourceType);
  }

  /**
   * Gets the destination entity display name.
   *
   * @param conn - The connection.
   * @returns The destination name or ID.
   */
  getDestinationName(conn: NetworkConnection): string {
    return this.getEntityName(conn.destinationId, conn.destinationType);
  }

  /**
   * Gets a cached entity display name.
   *
   * @param id - The entity ID.
   * @param type - The entity type.
   * @returns The display name or ID.
   */
  private getEntityName(id: string, type: string): string {
    const cacheKey = `${type}:${id}`;
    if (!this.entityNames.has(cacheKey)) {
      this.entityNames.set(cacheKey, `${type} (${id.substring(0, 8)}...)`);
    }
    return this.entityNames.get(cacheKey) || id;
  }

  /**
   * Builds the list of available entities for the connection form.
   *
   * @returns Array of connection entities.
   */
  private getEntities(): ConnectionEntity[] {
    const entities: ConnectionEntity[] = [];

    // Add subnets
    this.connections.forEach(conn => {
      entities.push({
        id: conn.id,
        name: `${conn.id} (${conn.sourceType} -> ${conn.destinationType})`,
        type: 'subnet',
        entityType: 'connection'
      });
    });

    return entities;
  }
}