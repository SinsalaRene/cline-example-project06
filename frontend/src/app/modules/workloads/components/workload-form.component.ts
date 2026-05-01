import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { WorkloadsService } from '../services/workloads.service';
import { Workload, CreateWorkloadRequest, UpdateWorkloadRequest } from '../models/workload.model';

@Component({
    selector: 'app-workload-form',
    standalone: false,
    templateUrl: './workload-form.component.html',
    styleUrls: ['./workload-form.component.css']
})
export class WorkloadFormComponent implements OnInit {
    workloadForm: FormGroup;
    isLoading = false;
    isEditMode = false;
    workloadId: string = '';
    submitLoading = false;

    workloadTypes: Array<{ value: string; label: string; description: string }> = [];
    environments: Array<{ value: string; label: string }> = [];
    statuses: Array<{ value: string; label: string }> = [];

    constructor(
        private fb: FormBuilder,
        private route: ActivatedRoute,
        private workloadsService: WorkloadsService,
        private dialog: MatDialog,
        private snackBar: MatSnackBar,
        private router: Router
    ) {
        this.workloadForm = this.fb.group({
            name: ['', [Validators.required]],
            description: [''],
            workload_type: ['', [Validators.required]],
            resource_group: [''],
            azure_resource_id: [''],
            environment: ['', [Validators.required]],
            status: ['active'],
            owner: [''],
            contact_email: [''],
            tags: [{}]
        });

        this.workloadTypes = this.workloadsService.getWorkloadTypeOptions();
        this.environments = this.workloadsService.getEnvironmentOptions();
        this.statuses = this.workloadsService.getStatusOptions();
    }

    ngOnInit(): void {
        this.workloadId = this.route.snapshot.paramMap.get('id') || '';
        this.isEditMode = !!this.workloadId;

        if (this.isEditMode) {
            this.loadWorkload(this.workloadId);
        }
    }

    loadWorkload(id: string): void {
        this.isLoading = true;
        this.workloadsService.getWorkload(id).subscribe({
            next: (workload: Workload) => {
                this.workloadForm.patchValue({
                    name: workload.name,
                    description: workload.description,
                    workload_type: workload.workload_type,
                    resource_group: workload.resource_group,
                    azure_resource_id: workload.azure_resource_id,
                    environment: workload.environment,
                    status: workload.status,
                    owner: workload.owner,
                    contact_email: workload.contact_email,
                    tags: workload.tags || {}
                });
                this.isLoading = false;
            },
            error: (error) => {
                this.isLoading = false;
                this.snackBar.open('Error loading workload: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    onSubmit(): void {
        if (this.workloadForm.invalid) {
            this.workloadForm.markAllAsTouched();
            return;
        }

        this.submitLoading = true;
        const formData = this.workloadForm.value;

        if (this.isEditMode) {
            const updateRequest: UpdateWorkloadRequest = {
                name: formData.name,
                description: formData.description,
                workload_type: formData.workload_type,
                resource_group: formData.resource_group,
                azure_resource_id: formData.azure_resource_id,
                environment: formData.environment,
                status: formData.status,
                owner: formData.owner,
                contact_email: formData.contact_email,
                tags: formData.tags
            };

            this.workloadsService.updateWorkload(this.workloadId, updateRequest).subscribe({
                next: (workload: Workload) => {
                    this.submitLoading = false;
                    this.snackBar.open('Workload updated successfully', 'Close', { duration: 3000 });
                    this.router.navigate(['/workloads', this.workloadId]);
                },
                error: (error) => {
                    this.submitLoading = false;
                    this.snackBar.open('Error updating workload: ' + error.message, 'Close', { duration: 3000 });
                }
            });
        } else {
            const createRequest: CreateWorkloadRequest = {
                name: formData.name,
                description: formData.description,
                workload_type: formData.workload_type,
                resource_group: formData.resource_group,
                azure_resource_id: formData.azure_resource_id,
                environment: formData.environment,
                owner: formData.owner,
                contact_email: formData.contact_email,
                tags: formData.tags
            };

            this.workloadsService.createWorkload(createRequest).subscribe({
                next: (workload: Workload) => {
                    this.submitLoading = false;
                    this.snackBar.open('Workload created successfully', 'Close', { duration: 3000 });
                    this.router.navigate(['/workloads', workload.id]);
                },
                error: (error) => {
                    this.submitLoading = false;
                    this.snackBar.open('Error creating workload: ' + error.message, 'Close', { duration: 3000 });
                }
            });
        }
    }

    onCancel(): void {
        this.router.navigate(['/workloads']);
    }

    getTagsArray(): Array<{ key: string; value: string }> {
        const tags = this.workloadForm.get('tags')?.value || {};
        return Object.entries(tags).map(([key, value]) => ({ key, value }));
    }

    addTag(): { key: string; value: string } {
        const tag = { key: '', value: '' };
        this.workloadForm.get('tags')?.value && Object.entries(this.workloadForm.get('tags')?.value).forEach(([k, v]) => {
            // Already in tags
        });
        return tag;
    }

    removeTag(index: number): void {
        const tags = this.workloadForm.get('tags')?.value || {};
        const entries = Object.entries(tags);
        entries.splice(index, 1);
        this.workloadForm.get('tags')?.setValue(Object.fromEntries(entries));
    }
}