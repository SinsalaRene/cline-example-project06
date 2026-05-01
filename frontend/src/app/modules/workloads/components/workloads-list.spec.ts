import { ComponentFixture, TestBed, fakeAsync, tick, waitForAsync } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatTableModule, MatPaginatorModule, MatSortModule } from '@angular/material';
import { MatIconModule, MatButtonModule, MatInputModule } from '@angular/material';
import { MatProgressBarModule, MatCheckboxModule } from '@angular/material';

import { WorkloadsListComponent } from './workloads-list.component';
import { WorkloadsService } from '../services/workloads.service';

describe('WorkloadsListComponent', () => {
    let component: WorkloadsListComponent;
    let fixture: ComponentFixture<WorkloadsListComponent>;
    let mockWorkloadsService: any;

    beforeEach(waitForAsync(() => {
        mockWorkloadsService = {
            getWorkloads: () => { },
            deleteWorkload: () => { },
            refreshWorkloads: () => { }
        };

        TestBed.configureTestingModule({
            declarations: [WorkloadsListComponent],
            imports: [
                ReactiveFormsModule,
                MatTableModule,
                MatPaginatorModule,
                MatSortModule,
                MatIconModule,
                MatButtonModule,
                MatInputModule,
                MatProgressBarModule,
                MatCheckboxModule
            ],
            providers: [{ provide: WorkloadsService, useValue: mockWorkloadsService }]
        }).compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(WorkloadsListComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should have empty message when no workloads', () => {
        component.workloads = [];
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;
        expect(compiled.querySelector('.no-data-message')?.textContent).toContain('No workloads found');
    });
});