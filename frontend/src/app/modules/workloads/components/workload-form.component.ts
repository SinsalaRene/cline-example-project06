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
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { WorkloadsService } from '../services/workloads.service';
import { Workload, CreateWorkloadRequest, UpdateWorkloadRequest } from '../models/workload.model';

/**
 * WorkloadFormComponent - Creates and edits workloads via reactive forms.
 *
 * @component
 * @description A dual-mode form component that handles both creating new workloads
 * and editing existing ones. Uses reactive form validation with required fields
 * for name, workload_type, and environment.
 *
 * - When accessed via `/workloads/new`, operates in create mode.
 * - When accessed via `/workloads/:id/edit`, loads existing data in edit mode.
 *
 * Form fields:
 * - name (required), workload_type (required dropdown), environment (required dropdown)
 * - description (optional textarea)
 * - resource_group, azure_resource_id, owner, contact_email (optional text fields)
 * - status (dropdown, defaults to 'active')
 * - tags (key-value pairs)
 *
 * @example
 * ```html
 * <!-- Accessed via: /workloads/new or /workloads/:id/edit -->
 * ```
 */
@Component({
    selector: 'app-workload-form',
    standalone: false,
    templateUrl: './workload-form.component.html',
    styleUrls: ['./workload-form.component.css']
})
export class WorkloadFormComponent implements OnInit {
    /** The reactive form group for all workload fields. */
    workloadForm: FormGroup;
    /** Indicates whether workload data is currently being loaded for editing. */
    isLoading = false;
    /** Whether the form is in edit mode (true) or create mode (false). */
    isEditMode = false;
    /** The workload ID being edited (empty string when creating). */
    workloadId: string = '';
    /** Indicates whether a submit operation is in progress. */
    submitLoading = false;

    /** Available workload type options populated from the service. */
    workloadTypes: Array<{ value: string; label: string; description: string }> = [];
    /** Available environment options populated from the service. */
    environments: Array<{ value: string; label: string }> = [];
    /** Available status options populated from the service. */
    statuses: Array<{ value: string; label: string }> = [];

    /**
     * Creates an instance of WorkloadFormComponent.
     * Initializes the reactive form with validation rules.
     */
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

    /**
     * Initializes the component by determining mode and loading data.
     */
    ngOnInit(): void {
        this.workloadId = this.route.snapshot.paramMap.get('id') || '';
        this.isEditMode = !!this.workloadId;

        if (this.isEditMode) {
            this.loadWorkload(this.workloadId);
        }
    }

    /**
     * Loads existing workload data into the form for editing.
     *
     * @param id - The workload identifier to load.
     */
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

    /**
     * Submits the form to create or update a workload.
     * Marks all fields as touched to trigger validation errors.
     */
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

    /**
     * Cancels the form operation and navigates back to the workload list.
     */
    onCancel(): void {
        this.router.navigate(['/workloads']);
    }

    /**
     * Converts the tags form value to an array for template display.
     *
     * @returns Array of { key, value } objects.
     */
    getTagsArray(): Array<{ key: string; value: string }> {
        const tags = this.workloadForm.get('tags')?.value || {};
        return Object.entries(tags).map(([key, value]) => ({ key, value: String(value) }));
    }

    /**
     * Returns a new empty tag object for template use.
     *
     * @returns A { key: string; value: string } object.
     */
    addTag(): { key: string; value: string } {
        const tag = { key: '', value: '' };
        this.workloadForm.get('tags')?.value && Object.entries(this.workloadForm.get('tags')?.value).forEach(([k, v]) => {
            // Already in tags
        });
        return tag;
    }

    /**
     * Adds a new empty tag key-value pair to the form.
     */
    addTagField(): void {
        const tags = this.workloadForm.get('tags')?.value || {};
        const newTags: Record<string, any> = { ...tags, '': '' };
        this.workloadForm.get('tags')?.setValue(newTags);
    }

    /**
     * Removes a tag at the specified index.
     *
     * @param index - The zero-based index of the tag to remove.
     */
    removeTag(index: number): void {
        const tags = this.workloadForm.get('tags')?.value || {};
        const entries = Object.entries(tags);
        entries.splice(index, 1);
        this.workloadForm.get('tags')?.setValue(Object.fromEntries(entries));
    }
}
