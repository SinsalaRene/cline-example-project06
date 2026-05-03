import { Component, OnInit, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { RulesService } from '../services/rules.service';

interface FirewallRule {
    id?: string;
    rule_collection_name: string;
    priority: number;
    action: string;
    protocol?: string;
    source_addresses?: string[];
    destination_addresses?: string[];
    status?: string;
    created_at?: string;
    updated_at?: string;
}

@Component({
    selector: 'app-rules-list',
    standalone: true,
    imports: [
        CommonModule,
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        MatFormFieldModule,
        MatInputModule,
        MatButtonModule,
        MatIconModule,
        MatProgressSpinnerModule,
        MatChipsModule,
        MatCardModule,
    ],
    template: `
        <div class="rules-list-container">
            <mat-card>
                <mat-card-header>
                    <mat-card-title>
                        <h1>Firewall Rules</h1>
                    </mat-card-title>
                </mat-card-header>

                <mat-card-content>
                    <!-- Search and Actions -->
                    <div class="toolbar">
                        <mat-form-field class="search-field">
                            <mat-label>Search rules...</mat-label>
                            <input matInput (keyup)="applyFilter($event)" placeholder="Search by name, IP, port...">
                            <mat-icon matSuffix>search</mat-icon>
                        </mat-form-field>
                        <button mat-raised-button color="primary" (click)="refreshData()">
                            <mat-icon>refresh</mat-icon>
                            Refresh
                        </button>
                    </div>

                    @if (isLoading()) {
                        <div class="loading-container">
                            <mat-spinner diameter="50"></mat-spinner>
                            <p>Loading firewall rules...</p>
                        </div>
                    } @else {
                        <!-- Rules Table -->
                        <div class="table-container">
                            <table mat-table [dataSource]="dataSource" matSort class="rules-table">
                                <!-- Name Column -->
                                <ng-container matColumnDef="rule_collection_name">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Rule Name</th>
                                    <td mat-cell *matCellDef="let rule">{{ rule.rule_collection_name }}</td>
                                </ng-container>

                                <!-- Priority Column -->
                                <ng-container matColumnDef="priority">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Priority</th>
                                    <td mat-cell *matCellDef="let rule">{{ rule.priority }}</td>
                                </ng-container>

                                <!-- Action Column -->
                                <ng-container matColumnDef="action">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Action</th>
                                    <td mat-cell *matCellDef="let rule">
                                        <mat-chip [class.allow-chip]="rule.action === 'Allow'" 
                                                  [class.deny-chip]="rule.action === 'Deny'">
                                            {{ rule.action }}
                                        </mat-chip>
                                    </td>
                                </ng-container>

                                <!-- Protocol Column -->
                                <ng-container matColumnDef="protocol">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Protocol</th>
                                    <td mat-cell *matCellDef="let rule">{{ rule.protocol || 'Any' }}</td>
                                </ng-container>

                                <!-- Source Column -->
                                <ng-container matColumnDef="source_addresses">
                                    <th mat-header-cell *matHeaderCellDef>Source</th>
                                    <td mat-cell *matCellDef="let rule">
                                        {{ rule.source_addresses?.join(', ') || 'Any' }}
                                    </td>
                                </ng-container>

                                <!-- Destination Column -->
                                <ng-container matColumnDef="destination_addresses">
                                    <th mat-header-cell *matHeaderCellDef>Destination</th>
                                    <td mat-cell *matCellDef="let rule">
                                        {{ rule.destination_addresses?.join(', ') || 'Any' }}
                                    </td>
                                </ng-container>

                                <!-- Status Column -->
                                <ng-container matColumnDef="status">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Status</th>
                                    <td mat-cell *matCellDef="let rule">
                                        <mat-chip [class.active-chip]="rule.status === 'active'" 
                                                  [class.inactive-chip]="rule.status !== 'active'">
                                            {{ rule.status || 'unknown' }}
                                        </mat-chip>
                                    </td>
                                </ng-container>

                                <!-- Created At Column -->
                                <ng-container matColumnDef="created_at">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Created</th>
                                    <td mat-cell *matCellDef="let rule">{{ rule.created_at | date:'short' }}</td>
                                </ng-container>

                                <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                                <tr mat-row *matRowDef="let row; columns: displayedColumns;" 
                                    class="table-row"></tr>
                            </table>
                        </div>

                        <mat-paginator [pageSizeOptions]="[10, 25, 50, 100]" 
                                       showFirstLastButtons 
                                       aria-label="Select page of firewall rules">
                        </mat-paginator>
                    }
                </mat-card-content>
            </mat-card>
        </div>
    `,
    styles: [`
        .rules-list-container {
            padding: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }

        mat-card {
            margin-bottom: 20px;
        }

        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            gap: 16px;
        }

        .search-field {
            flex: 1;
            max-width: 400px;
        }

        .loading-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
            gap: 16px;
        }

        .table-container {
            overflow-x: auto;
            margin-bottom: 16px;
        }

        .rules-table {
            width: 100%;
        }

        .table-row {
            cursor: pointer;
        }

        .table-row:hover {
            background-color: rgba(0, 0, 0, 0.04);
        }

        mat-chip {
            font-size: 12px;
        }

        .allow-chip {
            background-color: #4caf50 !important;
            color: white !important;
        }

        .deny-chip {
            background-color: #f44336 !important;
            color: white !important;
        }

        .active-chip {
            background-color: #2196f3 !important;
            color: white !important;
        }

        .inactive-chip {
            background-color: #9e9e9e !important;
            color: white !important;
        }
    `]
})
export class RulesListComponent implements OnInit {
    @ViewChild(MatPaginator) paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    displayedColumns: string[] = [
        'rule_collection_name',
        'priority',
        'action',
        'protocol',
        'source_addresses',
        'destination_addresses',
        'status',
        'created_at'
    ];

    dataSource = new MatTableDataSource<FirewallRule>();
    isLoading = signal(true);

    constructor(private rulesService: RulesService) { }

    ngOnInit(): void {
        this.loadRules();
    }

    loadRules(): void {
        this.isLoading.set(true);
        this.rulesService.getRules().subscribe({
            next: (response) => {
                this.dataSource.data = response.items || [];
                this.dataSource.paginator = this.paginator;
                this.dataSource.sort = this.sort;
                this.isLoading.set(false);
            },
            error: (error) => {
                console.error('Error loading rules:', error);
                this.isLoading.set(false);
            }
        });
    }

    applyFilter(event: Event): void {
        const filterValue = (event.target as HTMLInputElement).value;
        this.dataSource.filter = filterValue.trim().toLowerCase();

        if (this.dataSource.paginator) {
            this.dataSource.paginator.firstPage();
        }
    }

    refreshData(): void {
        this.loadRules();
    }
}
