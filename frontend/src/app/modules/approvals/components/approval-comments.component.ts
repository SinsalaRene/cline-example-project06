import { Component, OnInit, Input, Output, EventEmitter, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormControl, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApprovalsService } from '../services/approvals.service';
import { ApprovalComment } from '../models/approval.model';
import { Subscription } from 'rxjs';

@Component({
    selector: 'app-approval-comments',
    template: `
        <div class="comments-section">
            <div class="comments-header">
                <h3 class="comments-title">
                    <mat-icon>chat_bubble</mat-icon>
                    Comments ({{comments.length}})
                </h3>
                <button *ngIf="comments.length > 0" mat-button color="warn" (click)="clearAll()" class="clear-btn">
                    <mat-icon>delete_sweep</mat-icon> Clear All
                </button>
            </div>

            <!-- Comment list -->
            <div class="comments-list" *ngIf="comments.length > 0; else emptyComments">
                <div class="comment-item" *ngFor="let comment of comments" [class.is-own]="comment.author === currentUser">
                    <div class="comment-avatar" [ngClass]="getAvatarClass(comment.author)">
                        {{ getInitials(comment.author) }}
                    </div>
                    <div class="comment-content">
                        <div class="comment-header">
                            <span class="comment-author">{{ comment.author }}</span>
                            <span class="comment-time">{{ comment.created_at | date:'medium' }}</span>
                        </div>
                        <div class="comment-text">{{ comment.text }}</div>
                        <div class="comment-actions" *ngIf="canDelete(comment)">
                            <button mat-button color="warn" size="small" (click)="deleteComment(comment)">
                                <mat-icon>delete</mat-icon>
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Empty state -->
            <ng-template #emptyComments>
                <div class="comments-empty">
                    <mat-icon class="empty-icon">chat_bubble_outline</mat-icon>
                    <p>No comments yet</p>
                    <span>Be the first to add a comment</span>
                </div>
            </ng-template>

            <!-- Comment input -->
            <div class="comment-input-section" *ngIf="isPending">
                <mat-form-field appearance="outline" class="comment-field" subscriptSizing="dynamic">
                    <mat-label>Add a comment...</mat-label>
                    <textarea
                        matInput
                        [formControl]="commentForm"
                        [placeholder]="isReply ? 'Reply to thread...' : 'Add a comment...'"
                        rows="3"
                        cdkTextareaAutosize
                        #commentInput
                    ></textarea>
                    <mat-hint align="end">{{commentForm.value.text?.length || 0}}/1000</mat-hint>
                    <mat-error *ngIf="commentForm.errors?.['required']" class="comment-error">
                        Comment is required
                    </mat-error>
                    <mat-error *ngIf="commentForm.errors?.['minlength']" class="comment-error">
                        Comment must be at least 2 characters
                    </mat-error>
                </mat-form-field>

                <div class="comment-actions-bar">
                    <button
                        mat-raised-button
                        color="primary"
                        (click)="submitComment()"
                        [disabled]="!commentForm.valid"
                    >
                        <mat-icon>send</mat-icon>
                        {{ isReply ? 'Reply' : 'Post Comment' }}
                    </button>
                    <button
                        mat-stroked-button
                        color="primary"
                        (click)="addNotification()"
                        *ngIf="!isNotificationMode"
                    >
                        <mat-icon>notifications</mat-icon>
                        Add Notification
                    </button>
                </div>
            </div>
        </div>
    `,
    styles: [`
        .comments-section {
            padding: 16px;
        }

        .comments-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #e0e0e0;
        }

        .comments-title {
            margin: 0;
            font-size: 18px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .clear-btn {
            padding: 0 8px;
        }

        .comments-list {
            max-height: 400px;
            overflow-y: auto;
            margin-bottom: 16px;
        }

        .comment-item {
            display: flex;
            gap: 12px;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
            transition: background-color 0.2s;
        }

        .comment-item:hover {
            background-color: #f5f5f5;
        }

        .comment-item.is-own {
            background-color: #e3f2fd;
        }

        .comment-avatar {
            flex-shrink: 0;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 500;
            font-size: 14px;
            color: #fff;
        }

        .avatar-default { background-color: #9e9e9e; }
        .avatar-blue { background-color: #2196f3; }
        .avatar-green { background-color: #4caf50; }
        .avatar-orange { background-color: #ff9800; }
        .avatar-purple { background-color: #9c27b0; }
        .avatar-red { background-color: #f44336; }

        .comment-content {
            flex: 1;
            min-width: 0;
        }

        .comment-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }

        .comment-author {
            font-weight: 500;
            font-size: 14px;
        }

        .comment-time {
            font-size: 12px;
            color: #9e9e9e;
        }

        .comment-text {
            font-size: 14px;
            line-height: 1.5;
            color: #333;
            word-break: break-word;
        }

        .comment-actions {
            margin-top: 8px;
        }

        .comments-empty {
            text-align: center;
            padding: 40px 20px;
            color: #9e9e9e;
        }

        .empty-icon {
            font-size: 48px;
            width: 48px;
            height: 48px;
            margin-bottom: 8px;
        }

        .comments-empty p {
            margin: 0 0 4px 0;
            font-size: 14px;
        }

        .comments-empty span {
            font-size: 12px;
            color: #bdbdbd;
        }

        .comment-input-section {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #e0e0e0;
        }

        .comment-field {
            width: 100%;
        }

        .comment-actions-bar {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 12px;
        }

        .comment-error {
            font-size: 12px;
        }

        @media (max-width: 600px) {
            .comment-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 4px;
            }
        }
    `],
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatButtonModule,
        MatInputModule,
        MatFormFieldModule,
        MatIconModule,
        MatChipsModule,
        MatCardModule,
        MatSnackBarModule
    ],
    standalone: true
})
export class ApprovalCommentsComponent implements OnInit {
    @Input() approvalId: string = '';
    @Input() comments: ApprovalComment[] = [];
    @Input() currentUser: string = '';
    @Input() canDelete: (comment: ApprovalComment) => boolean = () => false;
    @Input() isPending: boolean = true;
    @Input() isReply: boolean = false;
    @Input() isNotificationMode: boolean = false;

    @Output() commentAdded = new EventEmitter<{ text: string; isNotification: boolean }>();
    @Output() commentDeleted = new EventEmitter<string>();
    @Output() clearAllComments = new EventEmitter<void>();

    commentForm: any;
    subscription: Subscription | null = null;
    commentSubscriptions: Subscription[] = [];
    private commentFormSubscription: Subscription | null = null;

    constructor(
        private approvalsService: ApprovalsService,
        private snackBar: MatSnackBar
    ) { }

    ngOnInit(): void {
        this.commentForm = new FormControl({});
        this.commentForm.setValue({ text: '' });

        // Subscribe to form value changes
        this.commentFormSubscription = this.commentForm.valueChanges.subscribe(value => {
            console.log('Comment form value changed:', value);
        });
    }

    ngOnDestroy(): void {
        if (this.commentFormSubscription) {
            this.commentFormSubscription.unsubscribe();
        }
        this.commentSubscriptions.forEach(sub => sub.unsubscribe());
    }

    submitComment(): void {
        const value = this.commentForm.value;
        const text = value?.text?.trim() || '';

        if (!text) {
            return;
        }

        this.commentAdded.emit({ text, isNotification: this.isNotificationMode });
        this.commentForm.reset({ text: '' });
    }

    deleteComment(comment: ApprovalComment): void {
        this.commentDeleted.emit(comment.id);
    }

    clearAll(): void {
        this.clearAllComments.emit();
    }

    addNotification(): void {
        this.commentForm.patchValue({ text: '' });
        this.commentForm.get('text')?.focus();
    }

    getInitials(name: string): string {
        const parts = name.split(' ');
        if (parts.length >= 2) {
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }
        return name.substring(0, 2).toUpperCase();
    }

    getAvatarClass(author: string): string {
        const colors = ['avatar-blue', 'avatar-green', 'avatar-orange', 'avatar-purple', 'avatar-red'];
        let hash = 0;
        for (let i = 0; i < author.length; i++) {
            hash = author.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length] || 'avatar-default';
    }
}