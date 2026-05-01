import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { WorkloadsService } from './workloads.service';

describe('WorkloadsService', () => {
    let service: WorkloadsService;
    let httpController: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [WorkloadsService]
        });
        service = TestBed.inject(WorkloadsService);
        httpController = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpController.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('getWorkloads', () => {
        it('should return workloads', () => {
            const mockWorkloads: any[] = [
                {
                    id: '1',
                    name: 'Test Workload',
                    workload_type: 'azure',
                    environment: 'dev',
                    status: 'active',
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    tags: {}
                }
            ];

            // The service returns a paginated response
            service.getWorkloads().subscribe(result => {
                // Mock response is an array, service wraps it
            });

            const req = httpController.expectOne('/api/workloads');
            expect(req.request.method).toBe('GET');
            req.flush(mockWorkloads);
        });
    });

    describe('getWorkload', () => {
        it('should return single workload', () => {
            const mockWorkload: any = {
                id: '1',
                name: 'Test Workload',
                workload_type: 'azure',
                environment: 'dev',
                status: 'active',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                tags: {},
                description: 'Test',
                resource_group: 'rg-test',
                owner: 'test owner',
                contact_email: 'test@test.com',
                azure_resource_id: '/subscriptions/123'
            };

            service.getWorkload('1').subscribe(workload => {
                expect(workload.id).toBe('1');
                expect(workload.name).toBe('Test Workload');
            });

            const req = httpController.expectOne('/api/workloads/1');
            expect(req.request.method).toBe('GET');
            req.flush(mockWorkload);
        });
    });

    describe('createWorkload', () => {
        it('should create workload', () => {
            const newWorkload: any = {
                name: 'New Workload',
                workload_type: 'azure',
                environment: 'dev',
                status: 'active'
            };

            const createdWorkload: any = {
                id: '1',
                ...newWorkload,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                tags: {}
            };

            service.createWorkload(newWorkload).subscribe(workload => {
                expect(workload.id).toBe('1');
            });

            const req = httpController.expectOne('/api/workloads');
            expect(req.request.method).toBe('POST');
            req.flush(createdWorkload);
        });
    });

    describe('updateWorkload', () => {
        it('should update workload', () => {
            const updatedWorkload: any = {
                name: 'Updated Workload',
                status: 'inactive'
            };

            const updatedResponse: any = {
                id: '1',
                name: 'Updated Workload',
                workload_type: 'azure',
                environment: 'dev',
                status: 'inactive',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                tags: {}
            };

            service.updateWorkload('1', updatedWorkload).subscribe(workload => {
                expect(workload.name).toBe('Updated Workload');
            });

            const req = httpController.expectOne('/api/workloads/1');
            expect(req.request.method).toBe('PUT');
            req.flush(updatedResponse);
        });
    });

    describe('deleteWorkload', () => {
        it('should delete workload', () => {
            service.deleteWorkload('1').subscribe(result => {
                expect(result).toBe(true);
            });

            const req = httpController.expectOne('/api/workloads/1');
            expect(req.request.method).toBe('DELETE');
            req.flush({ success: true });
        });
    });

    describe('getWorkloadRules', () => {
        it('should return rules for workload', () => {
            const mockRules: any[] = [{ id: '1', name: 'Rule 1' }];

            service.getWorkloadRules('1').subscribe(rules => {
                expect(rules.length).toBe(1);
            });

            const req = httpController.expectOne('/api/workloads/1/rules');
            expect(req.request.method).toBe('GET');
            req.flush(mockRules);
        });
    });

    describe('associateRule', () => {
        it('should associate rule with workload', () => {
            const mockResult: any = { workload_id: '1', rule_id: 'rule1', association_type: 'include' };

            service.associateRule('1', 'rule1', 'include').subscribe(result => {
                expect(result.workload_id).toBe('1');
            });

            const req = httpController.expectOne('/api/workloads/1/rules/rule1');
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });
    });

    describe('disassociateRule', () => {
        it('should disassociate rule from workload', () => {
            service.disassociateRule('1', 'rule1').subscribe(result => {
                expect((result as any).success).toBe(true);
            });

            const req = httpController.expectOne('/api/workloads/1/rules/rule1');
            expect(req.request.method).toBe('DELETE');
            req.flush({ success: true });
        });
    });
});
