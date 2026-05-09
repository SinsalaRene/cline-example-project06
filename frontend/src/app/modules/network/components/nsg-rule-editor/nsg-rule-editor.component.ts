/**
 * NSG Rule Editor Component
 *
 * A table-based inline editor for managing NSG rules within an NSG detail view.
 * Displays all rules in a sortable, draggable MatTable with inline edit/delete
 * actions and an "Add Rule" button that opens the rule form dialog.
 *
 * # Features
 *
 * - **MatTable** with columns: Name, Priority, Direction, Protocol, Source IP,
 *   Destination IP, Source Port, Destination Port, Access, Enabled, Actions
 * - **MatSort** for column-based sorting
 * - **CdkDragDrop** for manual priority reordering with visual drag handles
 * - **Add Rule** button opens `NsgRuleFormDialogComponent` for creating new rules
 * - **Edit** button in each row opens the dialog pre-filled with rule data
 * - **Delete** button opens `ConfirmationDialogComponent` for confirmation
 * - **Auto-save** on reorder via `reorderNsgRules` service method
 *
 * # Data Flow
 *
 * ```
 * NsgDetailPanel (parent)
 *   └── NsgRuleEditor (this component)
 *        ├── NsgRuleFormDialog (add/edit)
 *        └── ConfirmationDialog (delete)
 * ```
 *
 * @module nsg-rule-editor-component
 * @author Network Module Team
 * @since 1.0.0
 */

import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, ChangeDetectionStrategy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatExpansionModule } from '@angular/material/expansion';
import { CdkDrag, CdkDragDrop, CdkDropList, CdkDragHandle } from '@angular/cdk/drag-drop';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { Subject, takeUntil } from 'rxjs';
import { NetworkService } from '../../services/network.service';
import { NSGRule, Direction, Access, Protocol, CreateNsgRuleRequest, ImpactResult, RuleChangeType, Subnet, ExternalNetworkDevice, NetworkConnection } from '../../models/network.model';
import { NsgRuleFormDialogComponent, NsgRuleFormData } from '../nsg-rule-form-dialog/nsg-rule-form-dialog.component';
import { ConfirmationDialogComponent } from '../../../workloads/components/confirmation-dialog.component';
import { ImpactAnalysisDialogComponent } from '../impact-analysis/impact-analysis-dialog.component';
import { ImpactAnalyzerService } from '../../services/impact-analyzer.service';

/**
 * Display type for NSG rule table rows.
 * Extends NSGRule with additional display fields.
 */
export type NSGRuleDisplay = NSGRule & {
  /** Display label for the direction. */
  directionLabel?: string;
  /** Display label for the access type. */
  accessLabel?: string;
  /** Display label for the protocol. */
  protocolLabel?: string;
};

/**
 * NSG Rule Editor Component.
 *
 * Provides a full-featured table for managing NSG rules including:
 * - Sorting by column
 * - Drag-and-drop reordering
 * - Adding new rules via dialog
 * - Editing existing rules via pre-filled dialog
 * - Deleting rules with confirmation
 *
 * @selector app-nsg-rule-editor
 * @standalone
 */
@Component({
  selector: 'app-nsg-rule-editor',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatSortModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatExpansionModule,
    MatChipsModule,
    CdkDrag,
    CdkDropList,
    CdkDragHandle,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatDividerModule,
  ],
  template: `
    <div class="rule-editor">
      <!-- Header -->
      <div class="editor-header">
        <h3>NSG Rules</h3>
        <div class="header-actions">
          <button
            mat-raised-button
            color="primary"
            (click)="openAddRuleDialog()"
            [disabled]="isLoading"
          >
            <mat-icon>add</mat-icon>
            Add Rule
          </button>
          <button
            mat-stroked-button
            color="accent"
            (click)="reviewImpact()"
            [disabled]="isLoading || _displayedRules.length === 0"
            *ngIf="!showImpactSummary"
          >
            <mat-icon>assessment</mat-icon>
            Review Impact
          </button>
        </div>
      </div>

      <mat-divider />

      <!-- Impact Summary (collapsible) -->
      <mat-expansion-panel *ngIf="showImpactSummary && impactSummary && _displayedRules.length > 0" class="impact-summary-panel">
        <mat-expansion-panel-header>
          <mat-panel-title>
            <mat-icon color="accent">assessment</mat-icon>
            Impact Analysis Summary
          </mat-panel-title>
          <mat-panel-description color="accent">
            {{ impactSummary.addedCount }} new · {{ impactSummary.modifiedCount }} modified · {{ impactSummary.removedCount }} removed
            <button mat-icon-button matExpansionPanelIndicator aria-label="Close impact summary">
              <mat-icon>close</mat-icon>
            </button>
          </mat-panel-description>
        </mat-expansion-panel-header>

        <div class="impact-summary-content">
          <!-- Warning Banner -->
          <div class="warning-banner" *ngIf="impactSummary.hasRemovedAccess">
            <mat-icon color="warn">warning</mat-icon>
            <span>Warning: Changes remove existing access</span>
          </div>

          <!-- Summary Chips -->
          <div class="impact-chips">
            <mat-chip-listbox>
              <mat-chip color="accent" selected>{{ impactSummary.addedCount }} New</mat-chip>
              <mat-chip color="warn" selected>{{ impactSummary.removedCount }} Removed</mat-chip>
              <mat-chip color="primary" selected>{{ impactSummary.modifiedCount }} Modified</mat-chip>
              <mat-chip>{{ impactSummary.unchangedCount }} Unchanged</mat-chip>
            </mat-chip-listbox>
          </div>

          <!-- Affected Subnets -->
          <div class="impact-section" *ngIf="impactSummary.affectedSubnets?.length">
            <h4>Affected Subnets</h4>
            <div class="subnet-list">
              <div class="subnet-item" *ngFor="let subnet of impactSummary.affectedSubnets">
                <span class="subnet-name">{{ subnet.subnetName }}</span>
                <span class="subnet-cidr">{{ subnet.subnetCidr }}</span>
                <span class="rule-ref">Rules: {{ subnet.affectedRuleNames?.join(', ') || 'N/A' }}</span>
              </div>
            </div>
          </div>

          <!-- Newly Reachable Devices -->
          <div class="impact-section" *ngIf="impactSummary.reachableDevices?.length">
            <h4>Newly Reachable External Devices</h4>
            <div class="device-list">
              <div class="device-item" *ngFor="let device of impactSummary.reachableDevices">
                <span class="device-name">{{ device.deviceName }}</span>
                <span class="device-ip">{{ device.deviceIp }}</span>
                <span *ngIf="device.gainsAccess" class="gain-badge">Gains Access</span>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="impact-actions">
            <button mat-raised-button color="primary" (click)="openImpactDialog()">
              <mat-icon>visibility</mat-icon>
              Full Impact Analysis
            </button>
            <button mat-button (click)="dismissImpactSummary()">
              Dismiss
            </button>
          </div>
        </div>
      </mat-expansion-panel>

      <!-- Loading spinner -->
      <div class="loading-container" *ngIf="isLoading">
        <mat-progress-spinner
          mode="indeterminate"
          diameter="40"
        ></mat-progress-spinner>
      </div>

      <!-- Rules Table -->
      <div class="table-container" *ngIf="!isLoading">
        <div class="rules-table-wrapper" cdkDropList (cdkDropListDropped)="onDrop($event)">
          <table mat-table [dataSource]="dataSource" matSort>

            <!-- Drag Handle Column -->
            <ng-container matColumnDef="dragHandle">
              <th mat-header-cell *matHeaderCellDef>
                <mat-icon class="drag-icon">drag_handle</mat-icon>
              </th>
              <td mat-cell *matCellDef="let rule">
                <div class="drag-handle" cdkDragHandle>
                  <mat-icon>drag_handle</mat-icon>
                </div>
              </td>
            </ng-container>

            <!-- Name Column -->
            <ng-container matColumnDef="name">
              <th mat-header-cell *matHeaderCellDef mat-sort-header>Rule Name</th>
              <td mat-cell *matCellDef="let rule">{{ rule.name }}</td>
            </ng-container>

            <!-- Priority Column -->
            <ng-container matColumnDef="priority">
              <th mat-header-cell *matHeaderCellDef mat-sort-header>Priority</th>
              <td mat-cell *matCellDef="let rule">{{ rule.priority }}</td>
            </ng-container>

            <!-- Direction Column -->
            <ng-container matColumnDef="direction">
              <th mat-header-cell *matHeaderCellDef mat-sort-header>Direction</th>
              <td mat-cell *matCellDef="let rule">
                <span [class.inbound]="rule.direction === Direction.INBOUND"
                      [class.outbound]="rule.direction === Direction.OUTBOUND">
                  {{ rule.directionLabel || rule.direction }}
                </span>
              </td>
            </ng-container>

            <!-- Protocol Column -->
            <ng-container matColumnDef="protocol">
              <th mat-header-cell *matHeaderCellDef mat-sort-header>Protocol</th>
              <td mat-cell *matCellDef="let rule">{{ rule.protocolLabel || rule.protocol }}</td>
            </ng-container>

            <!-- Source IP Column -->
            <ng-container matColumnDef="sourceAddressPrefix">
              <th mat-header-cell *matHeaderCellDef mat-sort-header>Source IP</th>
              <td mat-cell *matCellDef="let rule" class="ip-cell">{{ rule.sourceAddressPrefix || '*' }}</td>
            </ng-container>

            <!-- Destination IP Column -->
            <ng-container matColumnDef="destinationAddressPrefix">
              <th mat-header-cell *matHeaderCellDef mat-sort-header>Dest IP</th>
              <td mat-cell *matCellDef="let rule" class="ip-cell">{{ rule.destinationAddressPrefix || '*' }}</td>
            </ng-container>

            <!-- Source Port Column -->
            <ng-container matColumnDef="sourcePortRange">
              <th mat-header-cell *matHeaderCellDef mat-sort-header>Source Port</th>
              <td mat-cell *matCellDef="let rule">{{ rule.sourcePortRange || '*' }}</td>
            </ng-container>

            <!-- Destination Port Column -->
            <ng-container matColumnDef="destinationPortRange">
              <th mat-header-cell *matHeaderCellDef mat-sort-header>Dest Port</th>
              <td mat-cell *matCellDef="let rule">{{ rule.destinationPortRange || '*' }}</td>
            </ng-container>

            <!-- Access Column -->
            <ng-container matColumnDef="access">
              <th mat-header-cell *matHeaderCellDef mat-sort-header>Access</th>
              <td mat-cell *matCellDef="let rule">
                <span [class.allow]="rule.access === Access.ALLOW"
                      [class.deny]="rule.access === Access.DENY">
                  {{ rule.accessLabel || rule.access }}
                </span>
              </td>
            </ng-container>

            <!-- Enabled Column -->
            <ng-container matColumnDef="isEnabled">
              <th mat-header-cell *matHeaderCellDef mat-sort-header>Enabled</th>
              <td mat-cell *matCellDef="let rule">
                <mat-icon [class.enabled]="rule.isEnabled" [class.disabled]="!rule.isEnabled"
                          [matTooltip]="rule.isEnabled ? 'Enabled' : 'Disabled'">
                  {{ rule.isEnabled ? 'check_circle' : 'cancel' }}
                </mat-icon>
              </td>
            </ng-container>

            <!-- Actions Column -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef>Actions</th>
              <td mat-cell *matCellDef="let rule">
                <button mat-icon-button color="accent" (click)="openEditRuleDialog(rule)" matTooltip="Edit Rule">
                  <mat-icon>edit</mat-icon>
                </button>
                <button mat-icon-button color="warn" (click)="deleteRule(rule)" matTooltip="Delete Rule">
                  <mat-icon>delete</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns; sticky: true"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"
                [class.dragging]="isDragging"
                cdkDrag
              >
            </tr>
          </table>

          <!-- Empty state -->
          <div class="empty-state" *ngIf="dataSource.length === 0">
            <mat-icon>gavel</mat-icon>
            <p>No NSG rules configured. Click "Add Rule" to create one.</p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .rule-editor {
      display: flex;
      flex-direction: column;
      padding: 16px;
    }

    .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 16px;
    }

    .editor-header h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 500;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 40px;
    }

    .table-container {
      overflow-x: auto;
      max-height: 600px;
      overflow-y: auto;
    }

    .rules-table-wrapper {
      display: inline-block;
      min-width: 100%;
    }

    .rules-table-wrapper [cdkDropList] {
      min-height: 44px;
    }

    table {
      width: 100%;
      min-width: 1200px;
    }

    th {
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
    }

    td {
      font-size: 13px;
    }

    .drag-handle {
      cursor: move;
      padding: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .drag-handle:hover {
      background: rgba(0, 0, 0, 0.04);
      border-radius: 4px;
    }

    .drag-icon {
      cursor: move;
    }

    .ip-cell {
      font-family: monospace;
      font-size: 12px;
    }

    .allow {
      color: #4caf50;
      font-weight: 500;
    }

    .deny {
      color: #f44336;
      font-weight: 500;
    }

    .inbound {
      color: #2196f3;
    }

    .outbound {
      color: #ff9800;
    }

    .enabled {
      color: #4caf50;
    }

    .disabled {
      color: #9e9e9e;
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

    .header-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .impact-summary-panel {
      margin: 16px;
    }

    .impact-summary-content {
      padding: 8px 0;
    }

    .warning-banner {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      background: rgba(244, 67, 54, 0.1);
      border: 1px solid rgba(244, 67, 54, 0.3);
      border-radius: 4px;
      margin-bottom: 16px;
      color: #c62828;
    }

    .warning-banner mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    .impact-chips {
      margin-bottom: 16px;
    }

    .impact-section {
      margin-bottom: 16px;
    }

    .impact-section h4 {
      margin: 0 0 8px 0;
      font-size: 14px;
      font-weight: 500;
      color: #666;
    }

    .subnet-list,
    .device-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .subnet-item,
    .device-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      background: #f5f5f5;
      border-radius: 4px;
      font-size: 13px;
    }

    .subnet-name {
      font-weight: 500;
    }

    .subnet-cidr {
      color: #666;
      font-size: 12px;
    }

    .rule-ref {
      color: #999;
      font-size: 11px;
      font-style: italic;
    }

    .device-name {
      font-weight: 500;
    }

    .device-ip {
      color: #666;
      font-size: 12px;
      font-family: monospace;
    }

    .gain-badge {
      background: #4caf50;
      color: white;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
    }

    .impact-actions {
      display: flex;
      gap: 8px;
      margin-top: 16px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NsgRuleEditorComponent implements OnInit, OnDestroy {
  /** The NSG ID this editor is for. */
  @Input() nsgId!: string;

  /** The NSG name for display. */
  @Input() nsgName = 'Network Security Group';

  /** Emits when rules are updated. */
  @Output() rulesUpdated = new EventEmitter<void>();

  /** Emits when a rule is deleted. */
  @Output() ruleDeleted = new EventEmitter<string>();

  /** Enum references for template binding. */
  readonly Direction = Direction;
  readonly Access = Access;
  readonly Protocol = Protocol;

  /** Whether rules are being loaded. */
  isLoading = false;

  /** The displayed NSG rules used by MatTableDataSource. */
  dataSource = new MatTableDataSource<NSGRuleDisplay>();

  /** Column definitions for the table. */
  displayedColumns: string[] = [
    'dragHandle',
    'name',
    'priority',
    'direction',
    'protocol',
    'sourceAddressPrefix',
    'destinationAddressPrefix',
    'sourcePortRange',
    'destinationPortRange',
    'access',
    'isEnabled',
    'actions',
  ];

  /** The MatSort for column sorting. */
  @ViewChild(MatSort) set matSort(sort: MatSort) {
    this._sort = sort;
    if (this.dataSource) {
      this.dataSource.sort = this._sort;
    }
  }
  private _sort = new MatSort();

  /** Whether a drag operation is in progress. */
  isDragging = false;

  /** Local copy of displayed rules for drag-drop. */
  private _displayedRules: NSGRuleDisplay[] = [];

  /** Subject to signal component destruction. */
  private destroy$ = new Subject<void>();

  /** Whether to show the impact summary panel. */
  showImpactSummary = false;

  /** The computed impact summary for the current rules. */
  impactSummary: ImpactResult | null = null;

  /** Impact analyzer service for computing rule change impacts. */
  private impactAnalyzer = new ImpactAnalyzerService();

  /**
   * Creates a new NsgRuleEditorComponent.
   *
   * @param networkService - The network service for API calls.
   * @param dialog - The Angular Material dialog service.
   * @param snackBar - The Material snack bar service.
   */
  constructor(
    private networkService: NetworkService,
    public dialog: MatDialog,
    private snackBar: MatSnackBar
  ) { }

  /**
   * Lifecycle hook called after input binding.
   * Loads the NSG rules from the service.
   */
  ngOnInit(): void {
    if (this.nsgId) {
      this.loadRules();
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
   * Loads NSG rules from the service and displays them in the table.
   * Maps raw rule data to display format with label fields.
   *
   * Comment on priority validation: Rules are loaded sorted by priority
   * ascending by the backend. The display preserves this order so that
   * drag-drop reordering maintains the expected priority sequence.
   */
  loadRules(): void {
    this.isLoading = true;
    this.networkService.getNsgRules(this.nsgId).pipe(takeUntil(this.destroy$)).subscribe({
      next: (rules) => {
        this._displayedRules = rules
          .sort((a, b) => a.priority - b.priority)
          .map((rule) => ({
            ...rule,
            directionLabel: this._getDirectionLabel(rule.direction),
            accessLabel: this._getAccessLabel(rule.access),
            protocolLabel: rule.protocol,
          }));
        this.dataSource.data = [...this._displayedRules];
        if (this._sort) {
          this.dataSource.sort = this._sort;
        }
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to load NSG rules:', err);
        this.isLoading = false;
      },
    });
  }

  /**
   * Opens the Add Rule dialog.
   * Passes existing rules for priority uniqueness validation.
   */
  openAddRuleDialog(): void {
    const formData: NsgRuleFormData = {
      nsgId: this.nsgId,
      existingRules: this._displayedRules,
      rule: null,
    };

    const dialogRef = this.dialog.open(NsgRuleFormDialogComponent, {
      data: formData,
      width: '700px',
      maxWidth: '90vw',
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.addRule(result);
      }
    });
  }

  /**
   * Opens the Edit Rule dialog pre-filled with rule data.
   *
   * @param rule - The rule to edit.
   */
  openEditRuleDialog(rule: NSGRuleDisplay): void {
    const formData: NsgRuleFormData = {
      nsgId: this.nsgId,
      existingRules: this._displayedRules,
      rule,
    };

    const dialogRef = this.dialog.open(NsgRuleFormDialogComponent, {
      data: formData,
      width: '700px',
      maxWidth: '90vw',
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.editRule(rule, result);
      }
    });
  }

  /**
   * Deletes a rule after confirming via confirmation dialog.
   *
   * @param rule - The rule to delete.
   */
  deleteRule(rule: NSGRuleDisplay): void {
    const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
      data: {
        title: 'Delete NSG Rule',
        message: `Are you sure you want to delete the rule "${rule.name}" (priority ${rule.priority})?`,
        confirmLabel: 'Delete',
        cancelLabel: 'Cancel',
      },
    });

    dialogRef.afterClosed().subscribe((confirmed) => {
      if (confirmed) {
        this.confirmDeleteRule(rule);
      }
    });
  }

  /**
   * Confirms and executes rule deletion.
   * Removes from the table first, then calls the service.
   *
   * @param rule - The rule to delete.
   */
  confirmDeleteRule(rule: NSGRuleDisplay): void {
    // Optimistic removal from table
    this._displayedRules = this._displayedRules.filter((r) => r.id !== rule.id);
    this.dataSource.data = [...this._displayedRules];
    this.ruleDeleted.emit(rule.id);

    // Call service to delete
    this.networkService.deleteNsgRule(rule.id).subscribe({
      next: () => {
        this.rulesUpdated.emit();
      },
      error: (err) => {
        console.error('Failed to delete rule:', err);
        // Rollback on error
        this.loadRules();
      },
    });
  }

  /**
   * Adds a new rule by calling the service.
   * On success, reloads the rules from the server.
   *
   * @param ruleData - The new rule data.
   */
  addRule(ruleData: Partial<NSGRule>): void {
    this.networkService.createNsgRule(this.nsgId, ruleData as CreateNsgRuleRequest).subscribe({
      next: () => {
        this.loadRules();
        this.rulesUpdated.emit();
      },
      error: (err) => {
        console.error('Failed to create rule:', err);
        this.loadRules();
      },
    });
  }

  /**
   * Updates an existing rule by calling the service.
   * On success, reloads the rules from the server.
   *
   * @param existingRule - The existing rule being updated.
   * @param ruleData - The updated rule data.
   */
  editRule(existingRule: NSGRuleDisplay, ruleData: Partial<NSGRule>): void {
    this.networkService.updateNsgRule(existingRule.id, ruleData as Partial<CreateNsgRuleRequest>).subscribe({
      next: () => {
        this.loadRules();
        this.rulesUpdated.emit();
      },
      error: (err) => {
        console.error('Failed to update rule:', err);
        this.loadRules();
      },
    });
  }

  /**
   * Handles drag-and-drop reordering of rules.
   *
   * When rules are reordered via drag-and-drop, this method:
   * 1. Updates the internal _displayedRules array order
   * 2. Updates the dataSource to match
   * 3. Calls reorderNsgRules service method to persist new order
   *
   * The backend will update priorities based on the new order.
   *
   * @param event - The CdkDragDrop event containing old and new positions.
   */
  onDrop(event: CdkDragDrop<NSGRuleDisplay[]>): void {
    const prevIndex = event.previousIndex;
    const moveIndex = event.currentIndex;

    if (prevIndex !== moveIndex) {
      // Move the rule in the displayed array
      const movedItem = this._displayedRules.splice(moveIndex, 1)[0];
      this._displayedRules.splice(prevIndex, 0, movedItem);
      this.dataSource.data = [...this._displayedRules];

      // Build the rule order request with new positions
      const ruleOrder = this._displayedRules.map((rule, index) => ({
        nsgRuleId: rule.id,
        position: index,
      }));

      // Persist the new order to the backend
      this.networkService.reorderNsgRules(this.nsgId, { ruleOrder }).subscribe({
        next: () => {
          this.rulesUpdated.emit();
        },
        error: (err) => {
          console.error('Failed to reorder rules:', err);
          // Rollback on error
          this.loadRules();
        },
      });
    }
  }

  /**
   * Gets the display label for a direction enum value.
   *
   * @param direction - The Direction enum value.
   * @returns The display label string.
   */
  private _getDirectionLabel(direction: Direction | string): string {
    const labels: Record<string, string> = {
      [Direction.INBOUND]: 'Inbound',
      [Direction.OUTBOUND]: 'Outbound',
    };
    return labels[direction] || direction;
  }

  /**
   * Gets the display label for an access enum value.
   *
   * @param access - The Access enum value.
   * @returns The display label string.
   */
  private _getAccessLabel(access: Access | string): string {
    const labels: Record<string, string> = {
      [Access.ALLOW]: 'Allow',
      [Access.DENY]: 'Deny',
    };
    return labels[access] || access;
  }

  // ==========================================================================
  // Impact Analysis Integration
  // ==========================================================================

  /**
   * Reviews the impact of current rules by opening the full impact analysis dialog.
   *
   * This method computes the impact of the current rules by comparing them against
   * a hypothetical "empty" rule set (no rules = all denied by default in Azure NSG).
   * It then opens the ImpactAnalysisDialog with the comparison results.
   */
  reviewImpact(): void {
    if (!this.nsgId || this._displayedRules.length === 0) {
      this.snackBar.open('Add at least one rule before reviewing impact', 'Close', { duration: 3000 });
      return;
    }

    // Compute impact: all current rules are "new" (compared against empty set)
    const emptyRules: NSGRule[] = [];
    const currentRules: NSGRule[] = this._displayedRules;

    const impact = this.impactAnalyzer.analyzeNsgImpact(
      this.nsgId,
      emptyRules,
      currentRules
    );

    // Show inline summary
    this.impactSummary = impact;
    this.showImpactSummary = true;
  }

  /**
   * Opens the full impact analysis dialog with detailed before/after comparison.
   *
   * This is useful when editing a specific rule and wanting to see the full impact
   * of that single change.
   */
  openImpactDialog(): void {
    if (!this.impactSummary) {
      this.snackBar.open('No impact data available', 'Close', { duration: 3000 });
      return;
    }

    const dialogRef = this.dialog.open(ImpactAnalysisDialogComponent, {
      width: '1200px',
      data: {
        nsgId: this.nsgId,
        impactResult: this.impactSummary,
        title: 'Full Impact Analysis',
      },
    });

    dialogRef.afterClosed().subscribe(() => {
      // Could apply changes here if user confirmed
    });
  }

  /**
   * Dismisses the impact summary panel.
   */
  dismissImpactSummary(): void {
    this.showImpactSummary = false;
    this.impactSummary = null;
  }
}
