/**
 * NSG Detail Panel Component
 *
 * Displays detailed properties of a Network Security Group (NSG) including
 * name, location, resource group, tags, sync status, and rule count.
 * Provides actions for syncing to Azure, viewing audit, and navigating back.
 *
 * # Features
 *
 * - **NSG Properties Card**: Shows name, location, resource group, tags
 * - **Sync Status Badge**: Color-coded badge (green/yellow/red/gray)
 * - **Sync to Azure Button**: Triggers sync and updates status badge
 * - **Rule Count Display**: Shows total number of rules
 * - **Audit Link**: Navigates to audit page for this NSG
 * - **Embedded Rule Editor**: Hosts `NsgRuleEditorComponent` below properties
 *
 * # Data Flow
 *
 * ```
 * TopologyContainer
 *   └── NetworkGraphComponent (click NSG node)
 *        └── NSG Detail Panel (side panel / drawer)
 *             ├── NsgRuleEditor (embedded)
 *             └── Sync / Audit actions
 * ```
 *
 * @module nsg-detail-panel-component
 * @author Network Module Team
 * @since 1.0.0
 */

import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialogModule } from '@angular/material/dialog';
import { Router, RouterModule } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { NetworkService } from '../../services/network.service';
import { NetworkSecurityGroup, SyncStatus } from '../../models/network.model';
import { NsgRuleEditorComponent } from '../nsg-rule-editor/nsg-rule-editor.component';

/**
 * NSG Detail Panel Component.
 *
 * Presents NSG metadata and provides actions for managing the NSG.
 * Hosts the NsgRuleEditor component for inline rule management.
 *
 * @selector app-nsg-detail-panel
 * @standalone
 */
@Component({
    selector: 'app-nsg-detail-panel',
    standalone: true,
    imports: [
        CommonModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        MatProgressSpinnerModule,
        MatChipsModule,
        MatDividerModule,
        MatTooltipModule,
        MatDialogModule,
        RouterModule,
        NsgRuleEditorComponent,
    ],
    template: `
    <div class="nsg-detail-panel" [class.expanded]="isOpen">
      <!-- Panel Header -->
      <div class="panel-header">
        <div class="header-title">
          <mat-icon color="accent">shield</mat-icon>
          <h2>NSG Details</h2>
        </div>
        <button mat-icon-button (click)="closePanel()" matTooltip="Close Panel">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      <mat-divider />

      <!-- Loading State -->
      <div class="loading-state" *ngIf="!nsg && !error">
        <mat-progress-spinner mode="indeterminate" diameter="40"></mat-progress-spinner>
        <p>Loading NSG details...</p>
      </div>

      <!-- Error State -->
      <div class="error-state" *ngIf="error">
        <mat-icon color="error">error_outline</mat-icon>
        <p>{{ error }}</p>
        <button mat-raised-button (click)="loadNsg()" color="warn">Retry</button>
      </div>

      <!-- NSG Properties -->
      <ng-container *ngIf="nsg">
        <!-- Sync Status Section -->
        <div class="sync-section">
          <h3>Sync Status</h3>
          <div class="sync-status-row">
            <!-- Sync Status Badge: green=synced, yellow=pending, red=failed, gray=never synced -->
            <span
              class="sync-badge"
              [class.synced]="syncStatus === SyncStatus.APPLIED"
              [class.pending]="syncStatus === SyncStatus.PENDING"
              [class.failed]="syncStatus === SyncStatus.FAILED"
              [class.never-synced]="!syncStatus"
              [matTooltip]="syncTooltipText"
            >
              <mat-icon [class.synced-icon]="syncStatus === SyncStatus.APPLIED"
                        [class.pending-icon]="syncStatus === SyncStatus.PENDING"
                        [class.failed-icon]="syncStatus === SyncStatus.FAILED">
                {{ getStatusIcon() }}
              </mat-icon>
              {{ syncStatusLabel }}
            </span>
            <button
              mat-raised-button
              color="primary"
              (click)="syncToAzure()"
              [disabled]="isSyncing"
              [matTooltip]="'Sync NSG configuration to Azure'"
            >
              <mat-icon>{{ isSyncing ? 'hourglass_empty' : 'sync' }}</mat-icon>
              {{ isSyncing ? 'Syncing...' : 'Sync to Azure' }}
            </button>
          </div>
          <p class="sync-detail" *ngIf="nsg.lastSyncedAt">
            Last synced: {{ nsg.lastSyncedAt | date:'medium' }}
          </p>
        </div>

        <mat-divider />

        <!-- NSG Properties -->
        <div class="properties-section">
          <h3>Properties</h3>
          <div class="property-row">
            <span class="property-label">Name</span>
            <span class="property-value">{{ nsg.name }}</span>
          </div>
          <div class="property-row">
            <span class="property-label">Location</span>
            <span class="property-value">{{ nsg.location }}</span>
          </div>
          <div class="property-row">
            <span class="property-label">Resource Group</span>
            <span class="property-value">{{ nsg.resourceGroup }}</span>
          </div>
          <div class="property-row" *ngIf="nsg.subscriptionId">
            <span class="property-label">Subscription ID</span>
            <span class="property-value">{{ nsg.subscriptionId }}</span>
          </div>
          <div class="property-row" *ngIf="nsg.tags">
            <span class="property-label">Tags</span>
            <span class="property-value">{{ nsg.tags }}</span>
          </div>
          <div class="property-row">
            <span class="property-label">Rules</span>
            <span class="property-value">{{ ruleCount }}</span>
          </div>
        </div>

        <mat-divider />

        <!-- Action Buttons -->
        <div class="actions-section">
          <button
            mat-raised-button
            color="accent"
            (click)="viewAudit()"
            [matTooltip]="'View NSG Audit Log'"
          >
            <mat-icon>assessment</mat-icon>
            View NSG Audit
          </button>
          <button
            mat-raised-button
            color="primary"
            (click)="goBack()"
            [matTooltip]="'Back to Topology'"
          >
            <mat-icon>arrow_back</mat-icon>
            Back to Topology
          </button>
        </div>

        <mat-divider />

        <!-- Embedded Rule Editor -->
        <div class="rule-editor-section">
          <app-nsg-rule-editor
            [nsgId]="nsg.id"
            [nsgName]="nsg.name"
            (rulesUpdated)="onRulesUpdated()"
            (ruleDeleted)="onRuleDeleted($event)"
          ></app-nsg-rule-editor>
        </div>
      </ng-container>
    </div>
  `,
    styles: [`
    .nsg-detail-panel {
      display: flex;
      flex-direction: column;
      background: #fff;
      border-left: 1px solid #e0e0e0;
      height: 100%;
      overflow-y: auto;
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      background: #f5f5f5;
    }

    .header-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .header-title h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 500;
    }

    .loading-state,
    .error-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px 24px;
      text-align: center;
      gap: 16px;
    }

    .loading-state mat-progress-spinner,
    .error-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
    }

    .loading-state p,
    .error-state p {
      margin: 0;
      color: #666;
    }

    .error-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #f44336;
    }

    .sync-section {
      padding: 16px 20px;
    }

    .sync-section h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #666;
      text-transform: uppercase;
    }

    .sync-status-row {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .sync-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      border-radius: 16px;
      font-size: 13px;
      font-weight: 500;
      cursor: default;
    }

    .sync-badge.synced {
      background: #e8f5e9;
      color: #2e7d32;
    }

    .sync-badge.pending {
      background: #fff3e0;
      color: #f57c00;
    }

    .sync-badge.failed {
      background: #ffebee;
      color: #c62828;
    }

    .sync-badge.never-synced {
      background: #eceff1;
      color: #78909c;
    }

    .sync-badge mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .sync-detail {
      margin: 8px 0 0 0;
      font-size: 12px;
      color: #999;
    }

    .properties-section {
      padding: 16px 20px;
    }

    .properties-section h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #666;
      text-transform: uppercase;
    }

    .property-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding: 6px 0;
      border-bottom: 1px solid #f0f0f0;
    }

    .property-label {
      font-size: 13px;
      color: #666;
      font-weight: 500;
    }

    .property-value {
      font-size: 13px;
      color: #333;
      text-align: right;
      max-width: 60%;
      word-break: break-word;
    }

    .actions-section {
      display: flex;
      gap: 12px;
      padding: 16px 20px;
      flex-wrap: wrap;
    }

    .rule-editor-section {
      padding: 0 20px 20px 20px;
    }
  `],
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NsgDetailPanelComponent implements OnInit, OnDestroy {
    /** The NSG ID to display. */
    @Input() nsgId!: string;

    /** Whether the panel is open/visible. */
    @Input() isOpen = true;

    /** Emits when the panel is closed. */
    @Output() panelClosed = new EventEmitter<void>();

    /** Enum reference for template binding. */
    readonly SyncStatus = SyncStatus;

    /** The loaded NSG data. */
    nsg: NetworkSecurityGroup | null = null;

    /** Error message if loading fails. */
    error: string | null = null;

    /** Whether sync operation is in progress. */
    isSyncing = false;

    /** Subject for cleanup. */
    private destroy$ = new Subject<void>();

    /**
     * Creates a new NsgDetailPanelComponent.
     *
     * @param networkService - The network service for API calls.
     * @param router - The Angular router for navigation.
     */
    constructor(
        private networkService: NetworkService,
        private router: Router
    ) { }

    /**
     * Lifecycle hook called after input binding.
     * Loads the NSG data and rule count.
     */
    ngOnInit(): void {
        if (this.nsgId) {
            this.loadNsg();
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
     * Loads the NSG data from the service.
     */
    loadNsg(): void {
        this.error = null;
        this.networkService.getNsg(this.nsgId).pipe(takeUntil(this.destroy$)).subscribe({
            next: (nsg) => {
                this.nsg = nsg;
                this.error = null;
            },
            error: (err) => {
                this.error = `Failed to load NSG: ${err.message}`;
                this.nsg = null;
            },
        });
    }

    /**
     * Gets the number of rules for this NSG.
     *
     * @returns The rule count.
     */
    get ruleCount(): number {
        return this.nsg?.rules?.length || 0;
    }

    /**
     * Gets the sync status enum value.
     *
     * @returns The sync status, or undefined if never synced.
     */
    get syncStatus(): SyncStatus | undefined {
        return this.nsg?.syncStatus;
    }

    /**
     * Gets the display label for the sync status badge.
     *
     * Comment on sync status:
     * - **APPLIED (green)**: NSG is synchronized with Azure
     * - **PENDING (yellow)**: Sync is in progress or needs attention
     * - **FAILED (red)**: Sync operation failed
     * - **undefined (gray)**: NSG has never been synced
     */
    get syncStatusLabel(): string {
        switch (this.syncStatus) {
            case SyncStatus.APPLIED:
                return 'Synced';
            case SyncStatus.PENDING:
                return 'Pending';
            case SyncStatus.FAILED:
                return 'Failed';
            default:
                return 'Never Synced';
        }
    }

    /**
     * Gets the tooltip text for the sync status.
     */
    get syncTooltipText(): string {
        switch (this.syncStatus) {
            case SyncStatus.APPLIED:
                return 'NSG is synchronized with Azure';
            case SyncStatus.PENDING:
                return 'Sync is in progress or needs attention';
            case SyncStatus.FAILED:
                return 'Sync operation failed';
            default:
                return 'NSG has never been synced to Azure';
        }
    }

    /**
     * Gets the icon for the current sync status.
     */
    getStatusIcon(): string {
        switch (this.syncStatus) {
            case SyncStatus.APPLIED:
                return 'check_circle';
            case SyncStatus.PENDING:
                return 'hourglass_top';
            case SyncStatus.FAILED:
                return 'error';
            default:
                return 'help_outline';
        }
    }

    /**
     * Syncs the NSG configuration to Azure.
     *
     * Shows a spinner during sync and updates the status badge on success.
     */
    syncToAzure(): void {
        if (!this.nsg) return;

        this.isSyncing = true;
        this.networkService.syncNsgToAzure(this.nsg.id).pipe(takeUntil(this.destroy$)).subscribe({
            next: () => {
                this.isSyncing = false;
                // Reload NSG to get updated sync status
                this.loadNsg();
            },
            error: (err) => {
                this.isSyncing = false;
                this.error = `Sync failed: ${err.message}`;
            },
        });
    }

    /**
     * Navigates to the NSG audit page.
     */
    viewAudit(): void {
        if (this.nsgId) {
            this.router.navigate(['/audit', 'resource', 'nsg', this.nsgId]);
        }
    }

    /**
     * Closes the panel and emits the panelClosed event.
     */
    closePanel(): void {
        this.isOpen = false;
        this.panelClosed.emit();
    }

    /**
     * Navigates back to the topology view.
     */
    goBack(): void {
        this.router.navigate(['/network', 'topology']);
    }

    /**
     * Handles rule update events from the embedded rule editor.
     */
    onRulesUpdated(): void {
        // Reload NSG to get updated rule count
        if (this.nsgId) {
            this.loadNsg();
        }
    }

    /**
     * Handles rule deletion events from the embedded rule editor.
     *
     * @param ruleId - The ID of the deleted rule.
     */
    onRuleDeleted(ruleId: string): void {
        console.log('Rule deleted:', ruleId);
    }
}