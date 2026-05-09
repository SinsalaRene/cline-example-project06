/**
 * Impact Analysis Dialog Component
 *
 * Displays a comprehensive impact analysis of NSG rule changes in a Material dialog.
 * Shows side-by-side comparison of "Before" vs "After" rules, affected subnets,
 * newly reachable external devices, and blocked access.
 *
 * Algorithm:
 * 1. Load current NSG rules and compare with proposed rules
 * 2. Identify added rules (yellow), removed rules (red), unchanged rules (green)
 * 3. Compute affected subnets by analyzing which subnets have NSGs impacted
 * 4. Determine newly reachable external devices from added rules
 * 5. Determine blocked devices from removed rules
 * 6. Show warning banner if existing access is being removed
 *
 * @module impact-analysis-dialog
 * @author Network Module Team
 * @since 1.0.0
 */

import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';

import { ImpactAnalyzerService } from '../../services/impact-analyzer.service';
import {
  NSGRule,
  NetworkSecurityGroup,
  Subnet,
  ExternalNetworkDevice,
  Access,
  Direction,
  Protocol,
  RuleComparison,
  RuleChangeType,
  AffectedSubnet,
  ReachableDevice,
  ImpactResult,
  NetworkConnection
} from '../../models/network.model';
import { NetworkService } from '../../services/network.service';
import { takeUntil } from 'rxjs/operators';
import { Subject } from 'rxjs';

/**
 * Dialog data interface for impact analysis.
 */
export interface ImpactAnalysisData {
  /** The NSG ID being modified. */
  nsgId: string;
  /** The proposed new set of NSG rules. */
  newRules: NSGRule[];
  /** Optional title for the dialog. */
  title?: string;
}

/**
 * Dialog result interface for impact analysis.
 */
export interface ImpactAnalysisResult {
  /** Whether the user confirmed the changes. */
  confirmed: boolean;
  /** The impact result data. */
  impact: ImpactResult | null;
}

/**
 * Display interface for affected subnet in the dialog template.
 */
interface DisplayAffectedSubnet {
  subnetName: string;
  subnetAddress: string;
  nsgName: string;
  affectedByRules: string[];
}

/**
 * Display interface for reachable external device in the dialog template.
 */
interface DisplayReachableDevice {
  deviceName: string;
  deviceIp: string;
  deviceType: string;
  enablingRules: string[];
}

/**
 * Display interface for blocked device in the dialog template.
 */
interface DisplayBlockedDevice {
  deviceName: string;
  deviceIp: string;
  removedRules: string[];
}

/**
 * Impact Analysis Dialog Component.
 *
 * @selector app-impact-analysis-dialog
 * @standalone
 */
@Component({
  selector: 'app-impact-analysis-dialog',
  standalone: true,
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
    MatInputModule,
    MatFormFieldModule,
  ],
  template: `
    <div class="impact-analysis-dialog">
      <!-- Dialog Header -->
      <div class="dialog-header">
        <h2 mat-dialog-title>
          <mat-icon color="warning">analysis</mat-icon>
          {{ data.title || 'NSG Impact Analysis' }}
        </h2>
        <button mat-icon-button (click)="cancel()">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      <!-- Dialog Content -->
      <div mat-dialog-content class="dialog-content">
        <!-- Loading State -->
        <div class="loading-container" *ngIf="isLoading">
          <mat-progress-spinner mode="indeterminate" diameter="40"></mat-progress-spinner>
          <p>Analyzing impact of rule changes...</p>
        </div>

        <!-- Impact Results -->
        <div *ngIf="!isLoading && impactResult">
          <!-- Warning Banner -->
          <div class="warning-banner" *ngIf="impactResult.hasRemovedAccess">
            <mat-icon>warning</mat-icon>
            <span>Warning: This change will remove existing access for some devices.</span>
          </div>

          <!-- Summary Stats -->
          <div class="summary-stats">
            <div class="stat-item" *ngIf="impactResult.addedCount">
              <mat-icon color="primary">add_circle</mat-icon>
              <span>{{ impactResult.addedCount }} new</span>
            </div>
            <div class="stat-item" *ngIf="impactResult.modifiedCount">
              <mat-icon color="accent">edit</mat-icon>
              <span>{{ impactResult.modifiedCount }} modified</span>
            </div>
            <div class="stat-item" *ngIf="impactResult.removedCount">
              <mat-icon color="warn">remove_circle</mat-icon>
              <span>{{ impactResult.removedCount }} removed</span>
            </div>
            <div class="stat-item" *ngIf="impactResult.affectedSubnets?.length">
              <mat-icon color="primary">dns</mat-icon>
              <span>{{ impactResult.affectedSubnets.length }} subnets affected</span>
            </div>
            <div class="stat-item" *ngIf="impactResult.reachableDevices?.length">
              <mat-icon color="accent">device_hub</mat-icon>
              <span>{{ impactResult.reachableDevices.length }} devices affected</span>
            </div>
          </div>

          <mat-divider></mat-divider>

          <!-- Before vs After Rules Comparison -->
          <section class="rules-section">
            <h3>
              <mat-icon color="primary">table_chart</mat-icon>
              Rule Comparison ({{ displayBeforeRules.length }} before / {{ displayAfterRules.length }} after)
            </h3>
            <div class="rules-comparison">
              <!-- Before Rules -->
              <div class="rules-column before">
                <h4>Before (Current Rules)</h4>
                <div class="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Rule Name</th>
                        <th>Priority</th>
                        <th>Direction</th>
                        <th>Source</th>
                        <th>Destination</th>
                        <th>Action</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let rule of displayBeforeRules">
                        <td>{{ rule.name }}</td>
                        <td>{{ rule.priority }}</td>
                        <td>{{ rule.direction }}</td>
                        <td>{{ rule.sourceAddressPrefix || '*' }}</td>
                        <td>{{ rule.destinationAddressPrefix || '*' }}</td>
                        <td>
                          <mat-chip [color]="rule.access === Access.ALLOW ? 'primary' : 'warn'" style="font-size: 11px;">
                            {{ rule.access === Access.ALLOW ? 'Allow' : 'Deny' }}
                          </mat-chip>
                        </td>
                        <td>
                          <mat-icon [color]="getBeforeStatusColor(rule)" matTooltip="{{ getBeforeStatusTooltip(rule) }}">
                            {{ getBeforeStatusIcon(rule) }}
                          </mat-icon>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- After Rules -->
              <div class="rules-column after">
                <h4>After (Proposed Rules)</h4>
                <div class="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Rule Name</th>
                        <th>Priority</th>
                        <th>Direction</th>
                        <th>Source</th>
                        <th>Destination</th>
                        <th>Action</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let rule of displayAfterRules">
                        <td>{{ rule.name }}</td>
                        <td>{{ rule.priority }}</td>
                        <td>{{ rule.direction }}</td>
                        <td>{{ rule.sourceAddressPrefix || '*' }}</td>
                        <td>{{ rule.destinationAddressPrefix || '*' }}</td>
                        <td>
                          <mat-chip [color]="rule.access === Access.ALLOW ? 'primary' : 'warn'" style="font-size: 11px;">
                            {{ rule.access === Access.ALLOW ? 'Allow' : 'Deny' }}
                          </mat-chip>
                        </td>
                        <td>
                          <mat-icon [color]="getAfterStatusColor(rule)">
                            {{ getAfterStatusIcon(rule) }}
                          </mat-icon>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </section>

          <!-- Affected Subnets -->
          <section class="subnets-section">
            <h3>
              <mat-icon color="primary">dns</mat-icon>
              Affected Subnets ({{ displayAffectedSubnets.length }})
            </h3>
            <div class="subnet-list" *ngIf="displayAffectedSubnets.length; else noSubnets">
              <div class="subnet-item" *ngFor="let subnet of displayAffectedSubnets">
                <div class="subnet-info">
                  <span class="subnet-name">{{ subnet.subnetName }}</span>
                  <span class="subnet-address">{{ subnet.subnetAddress }}</span>
                  <span class="nsg-name">{{ subnet.nsgName }}</span>
                </div>
                <div class="affecting-rules">
                  <span class="label">Affected by:</span>
                  <mat-chip *ngFor="let rule of subnet.affectedByRules" style="font-size: 10px;">
                    {{ rule }}
                  </mat-chip>
                </div>
              </div>
            </div>
            <ng-template #noSubnets>
              <p class="no-data">No subnets are affected by the proposed changes.</p>
            </ng-template>
          </section>

          <!-- Newly Reachable External Devices -->
          <section class="devices-section">
            <h3>
              <mat-icon color="primary">device_hub</mat-icon>
              Devices Gaining Access ({{ displayGainingAccessDevices.length }})
            </h3>
            <div class="device-list" *ngIf="displayGainingAccessDevices.length; else noGainingDevices">
              <div class="device-item" *ngFor="let device of displayGainingAccessDevices">
                <div class="device-info">
                  <span class="device-name">{{ device.deviceName }}</span>
                  <span class="device-ip">{{ device.deviceIp }}</span>
                  <span class="device-type">{{ device.deviceType }}</span>
                </div>
                <div class="enabling-rules">
                  <span class="label">Enabled by:</span>
                  <mat-chip *ngFor="let rule of device.enablingRules" style="font-size: 10px;">
                    {{ rule }}
                  </mat-chip>
                </div>
              </div>
            </div>
            <ng-template #noGainingDevices>
              <p class="no-data">No devices are gaining access from the proposed changes.</p>
            </ng-template>

            <h3 style="margin-top: 16px;">
              <mat-icon color="warn">block</mat-icon>
              Devices Losing Access ({{ displayLosingAccessDevices.length }})
            </h3>
            <div class="device-list" *ngIf="displayLosingAccessDevices.length; else noLosingDevices">
              <div class="device-item lost-access" *ngFor="let device of displayLosingAccessDevices">
                <div class="device-info">
                  <span class="device-name">{{ device.deviceName }}</span>
                  <span class="device-ip">{{ device.deviceIp }}</span>
                  <span class="device-type">{{ device.deviceType }}</span>
                </div>
                <div class="removed-rules">
                  <span class="label">Access removed by:</span>
                  <mat-chip *ngFor="let rule of device.removedRules" color="warn" style="font-size: 10px;">
                    {{ rule }}
                  </mat-chip>
                </div>
              </div>
            </div>
            <ng-template #noLosingDevices>
              <p class="no-data">No devices are losing access from the proposed changes.</p>
            </ng-template>
          </section>
        </div>
      </div>

      <!-- Dialog Actions -->
      <div mat-dialog-actions align="end" class="dialog-actions">
        <button mat-raised-button (click)="cancel()" color="primary">
          <mat-icon matPrefix>cancel</mat-icon>
          Cancel
        </button>
        <button mat-raised-button color="primary" (click)="confirm()" [disabled]="isLoading">
          <mat-icon matPrefix>check</mat-icon>
          Confirm Changes
        </button>
      </div>
    </div>
  `,
  styles: [`
    .impact-analysis-dialog {
      min-width: 700px;
      max-width: 90vw;
    }

    .dialog-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .dialog-header h2 {
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .dialog-content {
      max-height: 70vh;
      overflow-y: auto;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px;
      gap: 16px;
    }

    .warning-banner {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      background: #fff3e0;
      border: 1px solid #ffb74d;
      border-radius: 4px;
      color: #e65100;
      margin-bottom: 16px;
      font-weight: 500;
    }

    .warning-banner mat-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
    }

    .summary-stats {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      padding: 12px 0;
      margin-bottom: 16px;
    }

    .stat-item {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: #f5f5f5;
      border-radius: 4px;
      font-size: 13px;
    }

    .stat-item mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    section {
      margin-bottom: 24px;
    }

    section h3 {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 12px 0;
      font-size: 15px;
      color: #333;
    }

    .rules-comparison {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .rules-column h4 {
      margin: 0 0 8px 0;
      padding-bottom: 8px;
      border-bottom: 2px solid #ccc;
      font-size: 13px;
    }

    .rules-column.before h4 {
      border-color: #9e9e9e;
    }

    .rules-column.after h4 {
      border-color: #4caf50;
    }

    .table-container {
      max-height: 300px;
      overflow-y: auto;
      border: 1px solid #e0e0e0;
      border-radius: 4px;
    }

    .table-container table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }

    .table-container th {
      position: sticky;
      top: 0;
      background: #f5f5f5;
      padding: 6px 8px;
      text-align: left;
      font-weight: 600;
      border-bottom: 2px solid #e0e0e0;
    }

    .table-container td {
      padding: 4px 8px;
      border-bottom: 1px solid #f0f0f0;
    }

    .table-container tr:hover {
      background: #fafafa;
    }

    .subnets-section .subnet-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .subnet-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: #f5f5f5;
      border-radius: 4px;
      border-left: 3px solid #4caf50;
    }

    .subnet-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .subnet-name {
      font-weight: 600;
    }

    .subnet-address {
      font-size: 12px;
      color: #666;
    }

    .nsg-name {
      font-size: 11px;
      color: #1976d2;
    }

    .affecting-rules {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
    }

    .affecting-rules .label {
      font-size: 11px;
      color: #666;
    }

    .devices-section h3 {
      margin-top: 16px;
    }

    .devices-section .device-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .device-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: #e8f5e9;
      border-radius: 4px;
      border-left: 3px solid #4caf50;
    }

    .device-item.lost-access {
      background: #ffebee;
      border-left: 3px solid #f44336;
    }

    .device-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .device-name {
      font-weight: 600;
    }

    .device-ip {
      font-size: 12px;
      color: #666;
    }

    .device-type {
      font-size: 11px;
      color: #1976d2;
    }

    .enabling-rules {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
    }

    .removed-rules {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
    }

    .enabling-rules .label,
    .removed-rules .label {
      font-size: 11px;
      color: #666;
    }

    .no-data {
      color: #999;
      font-style: italic;
      margin: 8px 0;
    }

    .dialog-actions {
      padding-top: 8px;
    }

    .dialog-actions button {
      margin-left: 8px;
    }

    mat-chip {
      margin: 0 2px;
    }

    @media (max-width: 900px) {
      .rules-comparison {
        grid-template-columns: 1fr;
      }

      .impact-analysis-dialog {
        min-width: 100vw;
      }
    }
  `]
})
export class ImpactAnalysisDialogComponent {
  /** Subject to signal component destruction. */
  private destroy$ = new Subject<void>();

  /** The dialog data (NSG ID and new rules). */
  data: ImpactAnalysisData;

  /** Whether impact analysis is loading. */
  isLoading = true;

  /** The computed impact result. */
  impactResult: ImpactResult | null = null;

  /** Current NSG rules (before changes). */
  currentRules: NSGRule[] = [];

  /** Displayed columns for before rules table. */
  displayedBeforeColumns: string[] = ['name', 'priority', 'direction', 'source', 'destination', 'action', 'status'];

  /** Displayed columns for after rules table. */
  displayedAfterColumns: string[] = ['name', 'priority', 'direction', 'source', 'destination', 'action', 'status'];

  /** Comparison data for display. */
  comparison: RuleComparison[] = [];

  /** Display data for affected subnets. */
  displayAffectedSubnets: DisplayAffectedSubnet[] = [];

  /** Display data for devices gaining access. */
  displayGainingAccessDevices: DisplayReachableDevice[] = [];

  /** Display data for devices losing access. */
  displayLosingAccessDevices: DisplayBlockedDevice[] = [];

  /**
   * Creates a new ImpactAnalysisDialogComponent.
   *
   * @param dialogRef - Reference to the Material dialog reference.
   * @param data - Dialog data containing NSG ID and new rules.
   * @param impactAnalyzer - The impact analysis service.
   * @param networkService - The network service for data fetching.
   * @param snackBar - Material snack bar for notifications.
   */
  constructor(
    public dialogRef: MatDialogRef<ImpactAnalysisDialogComponent>,
    @Inject(MAT_DIALOG_DATA) data: ImpactAnalysisData,
    private impactAnalyzer: ImpactAnalyzerService,
    private networkService: NetworkService,
    private snackBar: MatSnackBar
  ) {
    this.data = data;
  }

  /**
   * Lifecycle hook called after the dialog is initialized.
   * Loads current NSG rules and performs impact analysis.
   */
  ngOnInit(): void {
    this.loadImpactAnalysis();
  }

  /**
   * Loads current NSG rules and computes impact analysis.
   */
  private loadImpactAnalysis(): void {
    this.isLoading = true;

    // Load current NSG rules
    this.networkService.getNsg(this.data.nsgId).pipe(takeUntil(this.destroy$)).subscribe({
      next: (nsg: NetworkSecurityGroup) => {
        this.currentRules = nsg.rules || [];

        // Get subnets for this NSG
        this.networkService.getSubnets().pipe(takeUntil(this.destroy$)).subscribe({
          next: (subnets: Subnet[]) => {
            const subnetFilter = subnets.filter(s => s.nsgId === this.data.nsgId || s.id === this.data.nsgId);

            // Get external devices
            this.networkService.getExternalDevices().pipe(takeUntil(this.destroy$)).subscribe({
              next: (devices: ExternalNetworkDevice[]) => {
                // Get connections
                this.networkService.getConnections().pipe(takeUntil(this.destroy$)).subscribe({
                  next: (connections) => {
                    // Build NSG map
                    const nsgMap = new Map<string, NetworkSecurityGroup>();
                    nsgMap.set(nsg.id, nsg);

                    // Run full impact analysis
                    const result = this.impactAnalyzer.analyzeNsgImpact(
                      this.data.nsgId,
                      this.currentRules,
                      this.data.newRules,
                      subnetFilter,
                      devices,
                      connections,
                      nsgMap
                    );

                    this.impactResult = result;
                    this.comparison = result.ruleComparisons;

                    // Transform affected subnets for display
                    this.displayAffectedSubnets = (result.affectedSubnets || []).map(as => ({
                      subnetName: as.subnet.name,
                      subnetAddress: as.subnet.addressPrefix,
                      nsgName: as.nsg?.name || 'N/A',
                      affectedByRules: [
                        ...(as.newlyAllowedRules || []).map(r => r.newRule?.name || r.oldRule?.name || '?'),
                        ...(as.newlyDeniedRules || []).map(r => r.newRule?.name || r.oldRule?.name || '?'),
                        ...(as.unchangedAffectingRules || []).filter(r => r.changeType === RuleChangeType.UNCHANGED).map(r => r.newRule?.name || r.oldRule?.name || '?')
                      ]
                    }));

                    // Transform reachable devices for display
                    const gaining: DisplayReachableDevice[] = [];
                    const losing: DisplayBlockedDevice[] = [];

                    (result.reachableDevices || []).forEach(rd => {
                      const ruleNames = (rd.responsibleRules || []).map(r => r.newRule?.name || r.oldRule?.name || '?');

                      if (rd.gainsAccess) {
                        gaining.push({
                          deviceName: rd.device.name,
                          deviceIp: rd.device.ipAddress || 'N/A',
                          deviceType: this.getDeviceTypeLabel(rd.device.deviceType),
                          enablingRules: ruleNames
                        });
                      } else {
                        losing.push({
                          deviceName: rd.device.name,
                          deviceIp: rd.device.ipAddress || 'N/A',
                          removedRules: ruleNames
                        });
                      }
                    });

                    this.displayGainingAccessDevices = gaining;
                    this.displayLosingAccessDevices = losing;
                    this.isLoading = false;
                  },
                  error: (err) => {
                    console.error('Failed to load connections:', err);
                    this.handleAnalysisError();
                  }
                });
              },
              error: (err) => {
                console.error('Failed to load external devices:', err);
                this.handleAnalysisError();
              }
            });
          },
          error: (err) => {
            console.error('Failed to load subnets:', err);
            this.handleAnalysisError();
          }
        });
      },
      error: (err) => {
        console.error('Failed to load NSG:', err);
        this.snackBar.open('Failed to load NSG details', 'Close', { duration: 5000 });
        this.handleAnalysisError();
      },
    });
  }

  /**
   * Handles analysis errors by showing a fallback view.
   */
  private handleAnalysisError(): void {
    this.impactResult = {
      nsgId: this.data.nsgId,
      ruleComparisons: this.impactAnalyzer.compareRules(this.currentRules, this.data.newRules),
      affectedSubnets: [],
      reachableDevices: [],
      hasRemovedAccess: false,
      addedCount: 0,
      removedCount: 0,
      modifiedCount: 0,
      unchangedCount: 0
    };
    this.displayAffectedSubnets = [];
    this.displayGainingAccessDevices = [];
    this.displayLosingAccessDevices = [];
    this.isLoading = false;
  }

  // ========================================================================
  // Computed display properties
  // ========================================================================

  /**
   * Gets the before rules for display (current rules with status indicators).
   */
  get displayBeforeRules(): NSGRule[] {
    return this.currentRules;
  }

  /**
   * Gets the after rules for display (proposed rules).
   */
  get displayAfterRules(): NSGRule[] {
    return this.data.newRules;
  }

  // ========================================================================
  // Status icon/color helpers
  // ========================================================================

  /**
   * Gets the status icon for a rule in the "Before" table.
   */
  getBeforeStatusIcon(rule: NSGRule): string {
    const comp = this.comparison.find(c => c.oldRule?.id === rule.id);
    if (comp) {
      if (comp.changeType === RuleChangeType.ADDED) return 'add_circle';
      if (comp.changeType === RuleChangeType.REMOVED) return 'remove_circle';
      if (comp.changeType === RuleChangeType.MODIFIED) return 'edit';
    }
    return 'check_circle';
  }

  /**
   * Gets the status color for a rule in the "Before" table.
   */
  getBeforeStatusColor(rule: NSGRule): string {
    const comp = this.comparison.find(c => c.oldRule?.id === rule.id);
    if (comp) {
      if (comp.changeType === RuleChangeType.ADDED) return 'accent';
      if (comp.changeType === RuleChangeType.REMOVED) return 'warn';
      if (comp.changeType === RuleChangeType.MODIFIED) return 'accent';
    }
    return 'default';
  }

  /**
   * Gets the status tooltip for a rule in the "Before" table.
   */
  getBeforeStatusTooltip(rule: NSGRule): string {
    const comp = this.comparison.find(c => c.oldRule?.id === rule.id);
    if (comp) {
      if (comp.changeType === RuleChangeType.ADDED) return 'Rule will be added';
      if (comp.changeType === RuleChangeType.REMOVED) return 'Rule will be removed';
      if (comp.changeType === RuleChangeType.MODIFIED) return `Modified: ${(comp.changedFields || []).join(', ')}`;
    }
    return 'No change';
  }

  /**
   * Gets the status icon for a rule in the "After" table.
   */
  getAfterStatusIcon(rule: NSGRule): string {
    const comp = this.comparison.find(c => c.newRule?.id === rule.id);
    if (comp) {
      if (comp.changeType === RuleChangeType.ADDED) return 'add_circle';
      if (comp.changeType === RuleChangeType.REMOVED) return 'remove_circle';
      if (comp.changeType === RuleChangeType.MODIFIED) return 'edit';
    }
    return 'check_circle';
  }

  /**
   * Gets the status color for a rule in the "After" table.
   */
  getAfterStatusColor(rule: NSGRule): string {
    const comp = this.comparison.find(c => c.newRule?.id === rule.id);
    if (comp) {
      if (comp.changeType === RuleChangeType.ADDED) return 'accent';
      if (comp.changeType === RuleChangeType.REMOVED) return 'warn';
      if (comp.changeType === RuleChangeType.MODIFIED) return 'accent';
    }
    return 'primary';
  }

  /**
   * Gets the device type display label.
   */
  getDeviceTypeLabel(deviceType: string): string {
    const labels: Record<string, string> = {
      'router': 'Router',
      'switch': 'Switch',
      'firewall': 'Firewall',
      'other': 'Other'
    };
    return labels[deviceType] || deviceType;
  }

  /**
   * Confirms the changes and closes the dialog.
   */
  confirm(): void {
    this.dialogRef.close({ confirmed: true, impact: this.impactResult });
  }

  /**
   * Cancels and closes the dialog without confirming.
   */
  cancel(): void {
    this.dialogRef.close({ confirmed: false, impact: null });
  }
}