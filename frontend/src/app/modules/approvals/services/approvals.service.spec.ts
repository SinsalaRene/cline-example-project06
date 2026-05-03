import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ApprovalsService } from './approvals.service';
import { ApprovalRequest, ApprovalComment, ApprovalListResponse } from '../models/approval.model';

describe('ApprovalsService', () => {
    let service: ApprovalsService;
    let httpTestingController: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [ApprovalsService]
        });

        service = TestBed.inject(ApprovalsService);
        httpTestingController = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpTestingController.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('getApprovals', () => {
        it('should return list of approvals', () => {
            const mockResponse: ApprovalListResponse = {
                items: [
                    {
                        id: '1',
                        rule_name: 'Test Rule',
                        rule_id: 'rule-1',
                        requestor: 'test@example.com',
                        request_type: 'create',
                        status: 'pending',
                        description: 'Test approval',
                        comments: [],
                        metadata: { rule_changes: { field: 'test' } },
                        priority: 'high',
                        requested_at: new Date().toISOString()
                    }
                ],
                total: 1,
                page: 1,
                pageSize: 20,
                totalPages: 1
            };

            service.getApprovals().subscribe(approvals => {
                expect(approvals.items.length).toBe(1);
                expect(approvals.items[0].status).toBe('pending');
            });

            const req = httpTestingController.expectOne('/api/v1/approvals');
            expect(req.request.method).toBe('GET');
            req.flush(mockResponse);
        });
    });

    describe('getApproval', () => {
        it('should return single approval', () => {
            const mockApproval: ApprovalRequest = {
                id: '1',
                rule_name: 'Test Rule',
                rule_id: 'rule-1',
                requestor: 'test@example.com',
                request_type: 'create',
                status: 'pending',
                description: 'Test approval',
                comments: [],
                metadata: { rule_changes: { field: 'test' } },
                priority: 'high',
                requested_at: new Date().toISOString()
            };

            service.getApproval('1').subscribe(approval => {
                expect(approval.id).toBe('1');
            });

            const req = httpTestingController.expectOne('/api/v1/approvals/1');
            expect(req.request.method).toBe('GET');
            req.flush(mockApproval);
        });
    });

    describe('approve', () => {
        it('should approve an approval', () => {
            const mockResult: ApprovalRequest = {
                id: '1',
                rule_name: 'Test Rule',
                rule_id: 'rule-1',
                requestor: 'test@example.com',
                request_type: 'create',
                status: 'approved',
                description: 'Test approval',
                comments: [],
                metadata: { rule_changes: { field: 'test' } },
                priority: 'high',
                requested_at: new Date().toISOString()
            };

            service.approve('1', { comment: 'Approved' }).subscribe(approval => {
                expect(approval.status).toBe('approved');
            });

            const req = httpTestingController.expectOne('/api/v1/approvals/1/approve');
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });
    });

    describe('reject', () => {
        it('should reject an approval', () => {
            const mockResult: ApprovalRequest = {
                id: '1',
                rule_name: 'Test Rule',
                rule_id: 'rule-1',
                requestor: 'test@example.com',
                request_type: 'create',
                status: 'rejected',
                description: 'Test approval',
                comments: [],
                metadata: { rule_changes: { field: 'test' } },
                priority: 'high',
                requested_at: new Date().toISOString()
            };

            service.reject('1', { reason: 'Too expensive' }).subscribe(approval => {
                expect(approval.status).toBe('rejected');
            });

            const req = httpTestingController.expectOne('/api/v1/approvals/1/reject');
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });
    });

    describe('addComment', () => {
        it('should add a comment to approval', () => {
            const mockComment: ApprovalComment = {
                id: '2',
                author: 'admin',
                text: 'New comment',
                created_at: new Date().toISOString()
            };

            service.addComment('1', 'New comment').subscribe(comment => {
                expect(comment.text).toBe('New comment');
            });

            const req = httpTestingController.expectOne('/api/v1/approvals/1/comments');
            expect(req.request.method).toBe('POST');
            req.flush(mockComment);
        });
    });

    describe('getComments', () => {
        it('should return comments for an approval', () => {
            const mockComments: ApprovalComment[] = [
                {
                    id: '1',
                    author: 'admin',
                    text: 'First comment',
                    created_at: new Date().toISOString()
                }
            ];

            service.getComments('1').subscribe(comments => {
                expect(comments.length).toBe(1);
            });

            const req = httpTestingController.expectOne('/api/v1/approvals/1/comments');
            expect(req.request.method).toBe('GET');
            req.flush(mockComments);
        });
    });

    describe('bulkApprove', () => {
        it('should approve multiple approvals', () => {
            const mockResult = { success: 2, failed: 0, errors: [] };

            service.bulkApprove(['1', '2'], 'Bulk approved').subscribe(result => {
                expect(result.success).toBe(2);
                expect(result.failed).toBe(0);
            });

            const req = httpTestingController.expectOne('/api/v1/approvals/bulk/approve');
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });
    });

    describe('bulkReject', () => {
        it('should reject multiple approvals', () => {
            const mockResult = { success: 2, failed: 0, errors: [] };

            service.bulkReject(['1', '2'], 'Too expensive').subscribe(result => {
                expect(result.success).toBe(2);
                expect(result.failed).toBe(0);
            });

            const req = httpTestingController.expectOne('/api/v1/approvals/bulk/reject');
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });
    });

    describe('getStatusDisplay', () => {
        it('should return correct display info for pending', () => {
            const result = service.getStatusDisplay('pending');
            expect(result.label).toBe('Pending');
            expect(result.color).toBe('#ff9800');
        });

        it('should return correct display info for approved', () => {
            const result = service.getStatusDisplay('approved');
            expect(result.label).toBe('Approved');
            expect(result.color).toBe('#4caf50');
        });

        it('should return fallback for unknown status', () => {
            const result = service.getStatusDisplay('unknown');
            expect(result.label).toBe('unknown');
        });
    });
});
