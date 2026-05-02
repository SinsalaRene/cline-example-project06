import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ApprovalsService } from './approvals.service';
import { ApprovalStatus, ApprovalType, Approval } from '../models/approval.model';

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

    describe('getPendingApprovals', () => {
        it('should return list of pending approvals', () => {
            const mockApprovals: Approval[] = [
                {
                    id: '1',
                    type: ApprovalType.MANUAL,
                    status: ApprovalStatus.PENDING,
                    description: 'Test approval',
                    createdAt: new Date(),
                    expiresAt: new Date()
                }
            ];

            service.getPendingApprovals().subscribe(approvals => {
                expect(approvals.length).toBe(1);
                expect(approvals[0].status).toBe(ApprovalStatus.PENDING);
            });

            const req = httpTestingController.expectOne('/api/approvals/pending');
            expect(req.request.method).toBe('GET');
            req.flush(mockApprovals);
        });
    });

    describe('getApprovalById', () => {
        it('should return single approval', () => {
            const mockApproval: Approval = {
                id: '1',
                type: ApprovalType.MANUAL,
                status: ApprovalStatus.PENDING,
                description: 'Test approval',
                createdAt: new Date(),
                expiresAt: new Date()
            };

            service.getApprovalById('1').subscribe(approval => {
                expect(approval.id).toBe('1');
            });

            const req = httpTestingController.expectOne('/api/approvals/1');
            expect(req.request.method).toBe('GET');
            req.flush(mockApproval);
        });
    });

    describe('approve', () => {
        it('should approve an approval', () => {
            const mockResult = { success: true };

            service.approve('1', { comment: 'Approved' }).subscribe(result => {
                expect(result.success).toBe(true);
            });

            const req = httpTestingController.expectOne('/api/approvals/1/approve');
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });
    });

    describe('reject', () => {
        it('should reject an approval', () => {
            const mockResult = { success: true };

            service.reject('1', { reason: 'Too expensive' }).subscribe(result => {
                expect(result.success).toBe(true);
            });

            const req = httpTestingController.expectOne('/api/approvals/1/reject');
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });
    });

    describe('getApprovalComments', () => {
        it('should return comments for an approval', () => {
            const mockComments = [
                { id: '1', approvalId: '1', comment: 'First comment', author: 'admin' }
            ];

            service.getApprovalComments('1').subscribe(comments => {
                expect(comments.length).toBe(1);
            });

            const req = httpTestingController.expectOne('/api/approvals/1/comments');
            expect(req.request.method).toBe('GET');
            req.flush(mockComments);
        });
    });

    describe('addComment', () => {
        it('should add a comment to approval', () => {
            const mockComment = { id: '2', approvalId: '1', comment: 'New comment', author: 'admin' };

            service.addComment('1', { text: 'New comment' }).subscribe(comment => {
                expect(comment.comment).toBe('New comment');
            });

            const req = httpTestingController.expectOne('/api/approvals/1/comments');
            expect(req.request.method).toBe('POST');
            req.flush(mockComment);
        });
    });

    describe('getBulkActions', () => {
        it('should return pending approval ids', () => {
            const mockResult = { pendingIds: ['1', '2'] };

            service.getBulkActions().subscribe(result => {
                expect(result.pendingIds.length).toBe(2);
            });

            const req = httpTestingController.expectOne('/api/approvals/bulk-actions');
            expect(req.request.method).toBe('GET');
            req.flush(mockResult);
        });
    });

    describe('bulkApprove', () => {
        it('should approve multiple approvals', () => {
            const mockResult = { approved: 2, failed: 0 };

            service.bulkApprove(['1', '2'], { comment: 'Bulk approved' }).subscribe(result => {
                expect(result.approved).toBe(2);
                expect(result.failed).toBe(0);
            });

            const req = httpTestingController.expectOne('/api/approvals/bulk-approve');
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });
    });

    describe('bulkReject', () => {
        it('should reject multiple approvals', () => {
            const mockResult = { rejected: 2, failed: 0 };

            service.bulkReject(['1', '2'], { reason: 'Too expensive' }).subscribe(result => {
                expect(result.rejected).toBe(2);
                expect(result.failed).toBe(0);
            });

            const req = httpTestingController.expectOne('/api/approvals/bulk-reject');
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });
    });
});