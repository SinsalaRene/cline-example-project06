import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { RulesService } from './rules.service';

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
        it('should return list of firewall rules', () => {
            const mockRules = [
                { id: '1', name: 'Rule 1', priority: 100, action: 'ALLOW' },
                { id: '2', name: 'Rule 2', priority: 200, action: 'DENY' }
            ];

            service.getRules().subscribe(rules => {
                expect(rules.length).toBe(2);
                expect(rules[0].name).toBe('Rule 1');
            });

            const req = httpTestingController.expectOne('/api/rules');
            expect(req.request.method).toBe('GET');
            req.flush(mockRules);
        });

        it('should support filtering by action', () => {
            const mockRules = [{ id: '1', name: 'Rule 1', priority: 100, action: 'ALLOW' }];

            service.getRules({ action: 'ALLOW' }).subscribe(rules => {
                expect(rules.length).toBe(1);
                expect(rules[0].action).toBe('ALLOW');
            });

            const req = httpTestingController.expectOne('/api/rules?action=ALLOW');
            expect(req.request.method).toBe('GET');
            req.flush(mockRules);
        });

        it('should support pagination', () => {
            const mockRules = [];

            service.getRules({ page: 1, pageSize: 20 }).subscribe(rules => {
                expect(rules.length).toBe(0);
            });

            const req = httpTestingController.expectOne('/api/rules?page=1&page_size=20');
            expect(req.request.method).toBe('GET');
            req.flush(mockRules);
        });
    });

    describe('getRuleById', () => {
        it('should return single firewall rule', () => {
            const mockRule = { id: '1', name: 'Test Rule', priority: 100, action: 'ALLOW' };

            service.getRuleById('1').subscribe(rule => {
                expect(rule.id).toBe('1');
                expect(rule.name).toBe('Test Rule');
            });

            const req = httpTestingController.expectOne('/api/rules/1');
            expect(req.request.method).toBe('GET');
            req.flush(mockRule);
        });
    });

    describe('createRule', () => {
        it('should create a new firewall rule', () => {
            const newRule = {
                name: 'New Rule',
                priority: 500,
                action: 'ALLOW',
                source: '192.168.1.0/24',
                destination: '10.0.0.0/8',
                protocol: 'TCP',
                port: 443
            };
            const createdRule = { id: '3', ...newRule };

            service.createRule(newRule).subscribe(rule => {
                expect(rule.id).toBe('3');
                expect(rule.name).toBe('New Rule');
            });

            const req = httpTestingController.expectOne('/api/rules');
            expect(req.request.method).toBe('POST');
            expect(req.request.body).toEqual(newRule);
            req.flush(createdRule);
        });
    });

    describe('updateRule', () => {
        it('should update an existing firewall rule', () => {
            const updatedRule = {
                name: 'Updated Rule',
                priority: 150,
                action: 'DENY',
                source: '172.16.0.0/12',
                destination: '192.168.0.0/16',
                protocol: 'UDP',
                port: 8080
            };
            const savedRule = { id: '1', ...updatedRule };

            service.updateRule('1', updatedRule).subscribe(rule => {
                expect(rule.name).toBe('Updated Rule');
            });

            const req = httpTestingController.expectOne('/api/rules/1');
            expect(req.request.method).toBe('PUT');
            expect(req.request.body).toEqual(updatedRule);
            req.flush(savedRule);
        });
    });

    describe('deleteRule', () => {
        it('should delete a firewall rule', () => {
            service.deleteRule('1').subscribe(response => {
                expect(response).toBeTruthy();
            });

            const req = httpTestingController.expectOne('/api/rules/1');
            expect(req.request.method).toBe('DELETE');
            req.flush({});
        });
    });

    describe('validateRule', () => {
        it('should validate a firewall rule before creation', () => {
            const rule = { name: 'Test', priority: 100, action: 'ALLOW' };

            service.validateRule(rule).subscribe(result => {
                expect(result.valid).toBe(true);
            });

            const req = httpTestingController.expectOne('/api/rules/validate');
            expect(req.request.method).toBe('POST');
            req.flush({ valid: true, errors: [] });
        });
    });

    describe('getRuleStats', () => {
        it('should return rule statistics', () => {
            const mockStats = {
                totalRules: 150,
                allowRules: 100,
                denyRules: 50,
                activeRules: 120
            };

            service.getRuleStats().subscribe(stats => {
                expect(stats.totalRules).toBe(150);
                expect(stats.allowRules).toBe(100);
            });

            const req = httpTestingController.expectOne('/api/rules/stats');
            expect(req.request.method).toBe('GET');
            req.flush(mockStats);
        });
    });
});