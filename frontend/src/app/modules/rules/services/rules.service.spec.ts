import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { RulesService, FirewallRule, PaginatedResponse, BulkOperationResult } from './rules.service';

describe('RulesService', () => {
    let service: RulesService;
    let httpTestingController: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [RulesService]
        });

        service = TestBed.inject(RulesService);
        httpTestingController = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpTestingController.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('getRules', () => {
        it('should return paginated list of firewall rules', () => {
            const mockResponse: PaginatedResponse<FirewallRule> = {
                items: [
                    { id: '1', rule_collection_name: 'Rule 1', priority: 100, action: 'Allow', protocol: 'TCP', status: 'active', created_at: '', updated_at: '' },
                    { id: '2', rule_collection_name: 'Rule 2', priority: 200, action: 'Deny', protocol: 'UDP', status: 'active', created_at: '', updated_at: '' }
                ],
                total: 2,
                page: 1,
                pageSize: 50,
                totalPages: 1
            };

            service.getRules(1, 50).subscribe((response: PaginatedResponse<FirewallRule>) => {
                expect(response.items.length).toBe(2);
                expect(response.items[0].rule_collection_name).toBe('Rule 1');
            });

            const req = httpTestingController.expectOne('/api/v1/rules?page=1&page_size=50');
            expect(req.request.method).toBe('GET');
            req.flush(mockResponse);
        });

        it('should support filtering by status', () => {
            const mockResponse: PaginatedResponse<FirewallRule> = {
                items: [{ id: '1', rule_collection_name: 'Rule 1', priority: 100, action: 'Allow', protocol: 'TCP', status: 'active', created_at: '', updated_at: '' }],
                total: 1,
                page: 1,
                pageSize: 50,
                totalPages: 1
            };

            service.getRules(1, 50, 'active').subscribe((response: PaginatedResponse<FirewallRule>) => {
                expect(response.items.length).toBe(1);
            });

            const req = httpTestingController.expectOne('/api/v1/rules?page=1&page_size=50&status=active');
            expect(req.request.method).toBe('GET');
            req.flush(mockResponse);
        });

        it('should support pagination', () => {
            const mockResponse: PaginatedResponse<FirewallRule> = {
                items: [],
                total: 0,
                page: 1,
                pageSize: 20,
                totalPages: 0
            };

            service.getRules(1, 20).subscribe((response: PaginatedResponse<FirewallRule>) => {
                expect(response.items.length).toBe(0);
            });

            const req = httpTestingController.expectOne('/api/v1/rules?page=1&page_size=20');
            expect(req.request.method).toBe('GET');
            req.flush(mockResponse);
        });
    });

    describe('getRule', () => {
        it('should return single firewall rule', () => {
            const mockRule: FirewallRule = {
                id: '1',
                rule_collection_name: 'Test Rule',
                priority: 100,
                action: 'Allow',
                protocol: 'TCP',
                status: 'active',
                created_at: '',
                updated_at: ''
            };

            service.getRule('1').subscribe((rule: FirewallRule) => {
                expect(rule.id).toBe('1');
                expect(rule.rule_collection_name).toBe('Test Rule');
            });

            const req = httpTestingController.expectOne('/api/v1/rules/1');
            expect(req.request.method).toBe('GET');
            req.flush(mockRule);
        });
    });

    describe('createRule', () => {
        it('should create a new firewall rule', () => {
            const newRule: Partial<FirewallRule> = {
                rule_collection_name: 'New Rule',
                priority: 500,
                action: 'Allow',
                protocol: 'TCP'
            };
            const createdRule: FirewallRule = {
                id: '3',
                rule_collection_name: 'New Rule',
                priority: 500,
                action: 'Allow',
                protocol: 'TCP',
                status: 'active',
                created_at: '',
                updated_at: ''
            };

            service.createRule(newRule).subscribe((rule: FirewallRule) => {
                expect(rule.id).toBe('3');
                expect(rule.rule_collection_name).toBe('New Rule');
            });

            const req = httpTestingController.expectOne('/api/v1/rules');
            expect(req.request.method).toBe('POST');
            expect(req.request.body).toEqual(newRule);
            req.flush(createdRule);
        });
    });

    describe('updateRule', () => {
        it('should update an existing firewall rule', () => {
            const updatedRule: Partial<FirewallRule> = {
                rule_collection_name: 'Updated Rule',
                priority: 150,
                action: 'Deny',
                protocol: 'UDP'
            };
            const savedRule: FirewallRule = {
                id: '1',
                rule_collection_name: 'Updated Rule',
                priority: 150,
                action: 'Deny',
                protocol: 'UDP',
                status: 'active',
                created_at: '',
                updated_at: ''
            };

            service.updateRule('1', updatedRule).subscribe((rule: FirewallRule) => {
                expect(rule.rule_collection_name).toBe('Updated Rule');
            });

            const req = httpTestingController.expectOne('/api/v1/rules/1');
            expect(req.request.method).toBe('PUT');
            expect(req.request.body).toEqual(updatedRule);
            req.flush(savedRule);
        });
    });

    describe('deleteRule', () => {
        it('should delete a firewall rule', () => {
            service.deleteRule('1').subscribe((response: void) => {
                expect(response).toBeUndefined();
            });

            const req = httpTestingController.expectOne('/api/v1/rules/1');
            expect(req.request.method).toBe('DELETE');
            req.flush({});
        });
    });

    describe('duplicateRule', () => {
        it('should duplicate a firewall rule', () => {
            const newRule: FirewallRule = {
                id: '2',
                rule_collection_name: 'Rule 1 (Copy)',
                priority: 100,
                action: 'Allow',
                protocol: 'TCP',
                status: 'active',
                created_at: '',
                updated_at: ''
            };

            service.duplicateRule('1', 'Rule 1 (Copy)').subscribe((rule: FirewallRule) => {
                expect(rule.id).toBe('2');
            });

            const req = httpTestingController.expectOne('/api/v1/rules/1/duplicate');
            expect(req.request.method).toBe('POST');
            req.flush(newRule);
        });
    });

    describe('bulkDelete', () => {
        it('should bulk delete rules', () => {
            service.bulkDelete(['1', '2']).subscribe((res: BulkOperationResult) => {
                expect(res.success).toBe(2);
                expect(res.failed).toBe(0);
            });

            const req1 = httpTestingController.expectOne('/api/v1/rules/1');
            expect(req1.request.method).toBe('DELETE');
            req1.flush({});

            const req2 = httpTestingController.expectOne('/api/v1/rules/2');
            expect(req2.request.method).toBe('DELETE');
            req2.flush({});
        });
    });

    describe('validateRule', () => {
        it('should validate a firewall rule before creation', () => {
            const rule: Partial<FirewallRule> = {
                rule_collection_name: 'Test',
                priority: 100,
                action: 'Allow',
                protocol: 'TCP'
            };

            const result = service.validateRule(rule);
            expect(result.valid).toBe(true);
            expect(result.errors.length).toBe(0);
        });

        it('should return errors for invalid rule', () => {
            const rule: Partial<FirewallRule> = {
                rule_collection_name: '',
                action: '',
                protocol: ''
            };

            const result = service.validateRule(rule);
            expect(result.valid).toBe(false);
            expect(result.errors.length).toBeGreaterThan(0);
        });
    });

    describe('findDuplicates', () => {
        it('should find duplicate rules', () => {
            const existingRules: FirewallRule[] = [
                {
                    id: '1',
                    rule_collection_name: 'Existing Rule',
                    priority: 100,
                    action: 'Allow',
                    protocol: 'TCP',
                    status: 'active',
                    created_at: '',
                    updated_at: ''
                }
            ];

            const newRule: Partial<FirewallRule> = {
                rule_collection_name: 'Existing Rule',
                priority: 100,
                action: 'Allow',
                protocol: 'TCP'
            };

            const duplicates: FirewallRule[] = service.findDuplicates(existingRules, newRule);
            expect(duplicates.length).toBe(1);
        });
    });

    describe('getAllRules', () => {
        it('should return all rules as a flat array', () => {
            const mockResponse: PaginatedResponse<FirewallRule> = {
                items: [
                    { id: '1', rule_collection_name: 'Rule 1', priority: 100, action: 'Allow', protocol: 'TCP', status: 'active', created_at: '', updated_at: '' },
                    { id: '2', rule_collection_name: 'Rule 2', priority: 200, action: 'Deny', protocol: 'UDP', status: 'active', created_at: '', updated_at: '' }
                ],
                total: 2,
                page: 1,
                pageSize: 1000,
                totalPages: 1
            };

            service.getAllRules().subscribe((rules: FirewallRule[]) => {
                expect(rules.length).toBe(2);
            });

            const req = httpTestingController.expectOne('/api/v1/rules?page=1&page_size=1000');
            expect(req.request.method).toBe('GET');
            req.flush(mockResponse);
        });
    });

    describe('importRules', () => {
        it('should import rules sequentially', async () => {
            const newRule: FirewallRule = {
                id: '3',
                rule_collection_name: 'Imported Rule',
                priority: 300,
                action: 'Allow',
                protocol: 'TCP',
                status: 'active',
                created_at: '',
                updated_at: ''
            };

            service.createRule({ rule_collection_name: 'Imported Rule', priority: 300, action: 'Allow', protocol: 'TCP' })
                .subscribe(() => { });

            const req = httpTestingController.expectOne('/api/v1/rules');
            expect(req.request.method).toBe('POST');
            req.flush(newRule);

            const result = await service.importRules([
                { rule_collection_name: 'Imported Rule', priority: 300, action: 'Allow', protocol: 'TCP' }
            ]);

            expect(result.imported).toBe(1);
            expect(result.skipped).toBe(0);
        });
    });

    describe('exportRules', () => {
        it('should export rules as JSON', () => {
            const mockRules: FirewallRule[] = [
                { id: '1', rule_collection_name: 'Rule 1', priority: 100, action: 'Allow', protocol: 'TCP', status: 'active', created_at: '', updated_at: '' }
            ];

            service.exportRules(mockRules, 'json').subscribe((blob: Blob) => {
                expect(blob instanceof Blob).toBe(true);
            });
        });
    });
});