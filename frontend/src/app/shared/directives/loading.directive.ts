import {
    Directive,
    ViewContainerRef,
    TemplateRef,
    Input,
    OnDestroy,
    OnInit,
} from '@angular/core';

/**
 * LoadingDirective - Structural directive that shows a loading indicator while an Observable is falsy.
 *
 * Usage:
 * ```html
 * <!-- Shows loading indicator until data$ emits a truthy value -->
 * <ng-template [appLoading]="data$ | async">
 *     <p>Content loaded: {{ data.name }}</p>
 * </ng-template>
 * ```
 *
 * The directive replaces the host element's content with a loading indicator
 * while the bound observable is null, undefined, or emits a falsy value.
 * Once a truthy value is emitted, the original template content is displayed.
 *
 * @example
 * ```html
 * <table>
 *   <ng-template [appLoading]="rows$ | async">
 *     <tr *ngFor="let row of rows"><td>{{ row }}</td></tr>
 *   </ng-template>
 * </table>
 * ```
 */
@Directive({
    selector: '[appLoading]',
    standalone: true,
})
export class LoadingDirective implements OnDestroy {
    /**
     * The value bound to the *appLoading directive.
     * The directive monitors this value to determine loading state.
     * When falsy (null, undefined, or any falsy value), a loading indicator is shown.
     * When truthy, the template content is displayed.
     */
    @Input() set appLoading(value: unknown) {
        this.updateView(value);
    }

    /**
     * Tracks the last seen value to avoid redundant view updates.
     */
    private lastValue: unknown = undefined;

    /**
     * Creates the embedded view for the content template.
     */
    private createContentView(): void {
        this.viewContainer.clear();
        if (this.template) {
            this.viewContainer.createEmbeddedView(this.template);
        }
    }

    /**
     * Updates the view based on the current value.
     * Shows loading indicator for falsy values, template content for truthy values.
     *
     * @param value - The current bound value to evaluate.
     */
    private updateView(value: unknown): void {
        // Skip if the value hasn't changed
        if (value === this.lastValue) {
            return;
        }
        this.lastValue = value;

        const isLoading = value === null || value === undefined || value === false || value === '';

        if (isLoading) {
            this.viewContainer.clear();
        } else {
            this.createContentView();
        }
    }

    constructor(
        private template: TemplateRef<unknown>,
        private viewContainer: ViewContainerRef
    ) {
        // Initialize with current state
        this.updateView(this.lastValue);
    }

    /**
     * Cleans up the view on destroy.
     */
    ngOnDestroy(): void {
        this.viewContainer.clear();
    }
}