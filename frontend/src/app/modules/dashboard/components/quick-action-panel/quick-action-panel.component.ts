import { Component, Input, Output, EventEmitter } from '@angular/core';
import { QuickAction } from '../../services/dashboard-stat.service';

@Component({
    selector: 'app-quick-action-panel',
    templateUrl: './quick-action-panel.component.html',
    styleUrls: ['./quick-action-panel.component.css'],
})
export class QuickActionPanelComponent {
    @Input() actions: QuickAction[] = [];
    @Output() actionClicked = new EventEmitter<QuickAction>();

    onActionClick(action: QuickAction): void {
        this.actionClicked.emit(action);
    }
}