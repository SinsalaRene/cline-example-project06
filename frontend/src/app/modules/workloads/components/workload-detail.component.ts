import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatTableModule } from '@angular/material/table';
import { FormsModule } from '@angular/forms';
import { WorkloadsService } from '../services/workloads.service';
import { Workload } from '../models/workload.model';
import { ConfirmationDialogComponent } from './confirmation-dialog.component';

interface RuleSummary {
    id: string;
    name: string;
    priority: number;
    action: string;
    protocol: string;
    associatedType: 'include' | 'exclude';
}

@Component({
    selector: 'app-workload-detail',
    standalone: false,
    templateUrl: './workload-detail.component.html',
    styleUrls: ['./workload-detail.component.css']
})
export class WorkloadDetailComponent implements OnInit {
    workload: Workload | null = null;
    isLoading = true;
    workloadId: string = '';
    rules: RuleSummary[] = [];
    associatedRules: RuleSummary[] = [];
    availableRules: RuleSummary[] = [];

    constructor(
        private route: ActivatedRoute,
        private workloadsService: WorkloadsService,
        private dialog: MatDialog,
        private snackBar: MatSnackBar,
        private router: Router
    ) { }

    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.workloadId = id;
            this.loadWorkload(id);
        }
    }

    loadWorkload(id: string): void {
        this.isLoading = true;
        this.workloadsService.getWorkload(id).subscribe({
            next: (workload: Workload) => {
                this.workload = workload;
                this.loadAssociatedRules(id);
                this.isLoading = false;
            },
            error: (error) => {
                this.isLoading = false;
                this.snackBar.open('Error loading workload: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    loadAssociatedRules(id: string): void {
        this.workloadsService.getWorkloadRules(id).subscribe({
            next: (rules: any[]) => {
                this.associatedRules = rules.map((r: any) => ({
                    id: r.id,
                    name: r.name || r.rule_collection_name,
                    priority: r.priority,
                    action: r.action,
                    protocol: r.protocol,
                    associatedType: 'include'
                }));
            },
            error: (error) => {
                this.snackBar.open('Error loading rules: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    associateRule(ruleId: string, associationType: 'include' | 'exclude'): void {
        if (!this.workloadId) return;

        this.workloadsService.associateRule(this.workloadId, ruleId, associationType).subscribe({
            next: () => {
                this.snackBar.open('Rule associated successfully', 'Close', { duration: 3000 });
                this.loadAssociatedRules(this.workloadId);
            },
            error: (error) => {
                this.snackBar.open('Error associating rule: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    disassociateRule(ruleId: string): void {
        if (!this.workloadId) return;

        this.workloadsService.disassociateRule(this.workloadId, ruleId).subscribe({
            next: () => {
                this.snackBar.open('Rule disassociated successfully', 'Close', { duration: 3000 });
                this.loadAssociatedRules(this.workloadId);
            },
            error: (error) => {
                this.snackBar.open('Error disassociating rule: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    deleteWorkload(): void {
        if (!this.workload || !this.workloadId) return;

        const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
            data: {
                title: 'Delete Workload',
                message: `Are you sure you want to delete "${this.workload.name}"? This action cannot be undone.`,
                confirmLabel: 'Delete',
                cancelLabel: 'Cancel'
            }
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result) {
                this.workloadsService.deleteWorkload(this.workloadId!).subscribe({
                    next: () => {
                        this.snackBar.open('Workload deleted successfully', 'Close', { duration: 3000 });
                        this.router.navigate(['/workloads']);
                    },
                    error: (error) => {
                        this.snackBar.open('Error deleting workload: ' + error.message, 'Close', { duration: 3000 });
                    }
                });
            }
        });
    }

    editWorkload(): void {
        if (this.workloadId) {
            this.router.navigate(['/workloads', this.workloadId, 'edit']);
        }
    }

    formatDateTime(date: string): string {
        return new Date(date).toLocaleString();
    }

    getTagsArray(): Array<{ key: string; value: string }> {
        if (!this.workload?.tags) return [];
        return Object.entries(this.workload.tags).map(([key, value]) => ({ key, value }));
    }
}