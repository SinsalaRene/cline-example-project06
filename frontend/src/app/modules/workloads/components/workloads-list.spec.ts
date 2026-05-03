import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBarModule } from '@angular/material/snack-bar';

import { WorkloadsListComponent } from './workloads-list.component';
import { WorkloadsService } from '../services/workloads.service';

describe('WorkloadsListComponent', () => {
    let component: WorkloadsListComponent;
    let fixture: ComponentFixture<WorkloadsListComponent>;
    let mockWorkloadsService: any;

    beforeEach(waitForAsync(() => {
        mockWorkloadsService = {
            getWorkloads: () => ({ subscribe: () => { } }),
            deleteWorkload: () => ({ subscribe: () => { } }),
            refreshWorkloads: () => { }
        };

        TestBed.configureTestingModule({
            imports: [
                WorkloadsListComponent,
                ReactiveFormsModule,
                MatTableModule,
                MatPaginatorModule,
                MatSortModule,
                MatIconModule,
                MatButtonModule,
                MatInputModule,
                MatCheckboxModule,
                MatSnackBarModule
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
        component.dataSource.data = [];
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;
        expect(compiled.querySelector('.no-data-message')?.textContent).toContain('No workloads found');
    });
});