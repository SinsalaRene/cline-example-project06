import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { HttpRequest, HttpEventType } from '@angular/common/http';
import { ApprovalsService } from './approvals.service';
import {
    ApprovalRequest,
    ApprovalFilter,
    ApprovalComment,
    BulkActionResult
} from '../models/approval.model';

describe('ApprovalsService', () => {
    let service: ApprovalsService;
    let httpMock: HttpTestingController;

    const mockApproval: ApprovalRequest = {
        id: '1',
        rule_name: 'Test Rule',
        rule_id: 'rule-123',
        requestor: 'John Doe',
        request_type: 'create',
        status: 'pending',
        description: 'Test description',
        requested_at: '2024-01-01T10:00:00Z',
        due_at: '2024-01-02T10:00:00Z',
        priority: 'high',
        comments: [],
        metadata: {
            rule_changes: { field: 'test_field' }
        }
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [ApprovalsService]
        });
        service = TestBed.inject(ApprovalsService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpMock.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('getApprovals', () => {
        it('should return a list of approvals', () => {
            const mockListResponse = {
                items: [mockApproval],
                total: 1,
                page: 1,
                pageSize: 20,
                totalPages: 1
            };

            service.getApprovals(1, 20).subscribe(response => {
                expect(response.total).toBe(1);
                expect(response.items.length).toBe(1);
                expect(response.items[0].id).toBe('1');
            });

            const req = httpMock.expectOne(`${service['baseUrl']}?page=1&page_size=20`);
            expect(req.request.method).toBe('GET');
            req.flush(mockListResponse);
        });

        it('should apply filters when provided', () => {
            const filters: ApprovalFilter = {
                searchQuery: 'test',
                statusFilter: 'pending',
                typeFilter: 'create',
                priorityFilter: 'high'
            };

            service.getApprovals(1, 20, filters).subscribe();
            const req = httpMock.expectOne(
                `${service['baseUrl']}?page=1&page_size=20&search=test&status=pending&type=create&priority=high`
            );
            expect(req.request.method).toBe('GET');
            req.flush({ items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 });
        });
    });

    describe('getApproval', () => {
        it('should return a single approval', () => {
            service.getApproval('1').subscribe(approval => {
                expect(approval.id).toBe('1');
                expect(approval.rule_name).toBe('Test Rule');
            });

            const req = httpMock.expectOne(`${service['baseUrl']}/1`);
            expect(req.request.method).toBe('GET');
            req.flush(mockApproval);
        });
    });

    describe('approve', () => {
        it('should approve an approval request', () => {
            const updatedApproval = { ...mockApproval, status: 'approved', approved_by: 'Admin' };
            service.approve('1').subscribe(approval => {
                expect(approval.status).toBe('approved');
            });

            const req = httpMock.expectOne(`${service['baseUrl']}/1/approve`);
            expect(req.request.method).toBe('POST');
            req.flush(updatedApproval);
        });
    });

    describe('reject', () => {
        it('should reject an approval request', () => {
            const updatedApproval = { ...mockApproval, status: 'rejected', rejection_reason: 'Too many changes' };
            service.reject('1', { reason: 'Too many changes' }).subscribe(approval => {
                expect(approval.status).toBe('rejected');
            });

            const req = httpMock.expectOne(`${service['baseUrl']}/1/reject`);
            expect(req.request.method).toBe('POST');
            req.flush(updatedApproval);
        });
    });

    describe('addComment', () => {
        it('should add a comment to an approval', () => {
            const mockComment: ApprovalComment = {
                id: 'comment-1',
                author: 'Admin',
                text: 'Test comment',
                created_at: new Date().toISOString()
            };

            service.addComment('1', 'Test comment').subscribe(comment => {
                expect(comment.text).toBe('Test comment');
                expect(comment.author).toBe('Admin');
            });

            const req = httpMock.expectOne(`${service['baseUrl']}/1/comments`);
            expect(req.request.method).toBe('POST');
            req.flush(mockComment);
        });
    });

    describe('getComments', () => {
        it('should return comments for an approval', () => {
            const mockComments: ApprovalComment[] = [{
                id: 'comment-1',
                author: 'Admin',
                text: 'Comment 1',
                created_at: new Date().toISOString()
            }];

            service.getComments('1').subscribe(comments => {
                expect(comments.length).toBe(1);
                expect(comments[0].text).toBe('Comment 1');
            });

            const req = httpMock.expectOne(`${service['baseUrl']}/1/comments`);
            expect(req.request.method).toBe('GET');
            req.flush(mockComments);
        });
    });

    describe('deleteComment', () => {
        it('should delete a comment', () => {
            service.deleteComment('1', 'comment-1').subscribe();
            const req = httpMock.expectOne(`${service['baseUrl']}/1/comments/comment-1`);
            expect(req.request.method).toBe('DELETE');
            req.flush({});
        });
    });

    describe('bulk operations', () => {
        it('should bulk approve approvals', () => {
            const mockResult: BulkActionResult = { success: 2, failed: 0, errors: [] };
            service.bulkApprove(['1', '2'], 'Bulk approve').subscribe(result => {
                expect(result.success).toBe(2);
            });

            const req = httpMock.expectOne(`${service['baseUrl']}/bulk/approve`);
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });

        it('should bulk reject approvals', () => {
            const mockResult: BulkActionResult = { success: 1, failed: 0, errors: [] };
            service.bulkReject(['1'], 'Too many changes').subscribe(result => {
                expect(result.success).toBe(1);
            });

            const req = httpMock.expectOne(`${service['baseUrl']}/bulk/reject`);
            expect(req.request.method).toBe('POST');
            req.flush(mockResult);
        });
    });

    describe('utility methods', () => {
        it('should correctly determine if an approval is expired', () => {
            const future = new Date();
            future.setDate(future.getDate() + 1);
            const past = new Date();
            past.setDate(past.getDate() - 1);

            const notExpired = { ...mockApproval, due_at: future.toISOString() };
            const expired = { ...mockApproval, due_at: past.toISOString() };

            expect(service.isExpired(notExpired)).toBe(false);
            expect(service.isExpired(expired)).toBe(true);
        });

        it('should return status display info', () => {
            const pending = service.getStatusDisplay('pending');
            expect(pending.label).toBe('Pending');
            expect(pending.color).toBe('#ff9800');

            const approved = service.getStatusDisplay('approved');
            expect(approved.label).toBe('Approved');
            expect(approved.color).toBe('#4caf50');
        });

        it('should return priority display info', () => {
            const low = service.getPriorityDisplay('low');
            expect(low.label).toBe('Low');

            const urgent = service.getPriorityDisplay('urgent');
            expect(urgent.label).toBe('Urgent');
        });

        it('should format dates correctly', () => {
            const date = service.formatDate('2024-01-15T10:30:00Z');
            expect(date).toBeDefined();
        });

        it('should return relative time', () => {
            const now = new Date().toISOString();
            expect(service.getRelativeTime(now)).toContain('just now');
        });
    });
});