import { Component, DebugElement } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoadingDirective } from './loading.directive';
import { By } from '@angular/platform-browser';

/**
 * Test component that provides a template for the loading directive.
 */
@Component({
    template: `
    <ng-template [appLoading]="observableValue">
        <span class="content">Loaded Content</span>
    </ng-template>
  `,
    standalone: true,
    imports: [LoadingDirective],
})
class TestHostComponent {
    /** The value bound to the loading directive. */
    observableValue: unknown = null;
}

/**
 * Unit tests for LoadingDirective.
 *
 * Covers:
 * - Loading state when value is null/undefined
 * - Content state when value is truthy
 * - Toggle between loading and content states
 * - Empty string and false values
 */
describe('LoadingDirective', () => {
    let fixture: ComponentFixture<TestHostComponent>;
    let component: TestHostComponent;
    let debugElement: DebugElement;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [TestHostComponent, LoadingDirective],
        }).compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(TestHostComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
        debugElement = fixture.debugElement;
    });

    it('should create the component', () => {
        expect(component).toBeTruthy();
    });

    it('should show a loading placeholder when value is null', () => {
        component.observableValue = null;
        fixture.detectChanges();

        const loadingSpans = debugElement.queryAll(By.css('[role="status"]'));
        expect(loadingSpans.length).toBe(1);
    });

    it('should show a loading placeholder when value is undefined', () => {
        component.observableValue = undefined;
        fixture.detectChanges();

        const loadingSpans = debugElement.queryAll(By.css('[role="status"]'));
        expect(loadingSpans.length).toBe(1);
    });

    it('should show content when value is truthy', () => {
        component.observableValue = { data: 'test' };
        fixture.detectChanges();

        const content = debugElement.query(By.css('.content'));
        expect(content).toBeTruthy();
        expect(content?.nativeElement.textContent).toContain('Loaded Content');
    });

    it('should show a loading placeholder when value is an empty string', () => {
        component.observableValue = '';
        fixture.detectChanges();

        const loadingSpans = debugElement.queryAll(By.css('[role="status"]'));
        expect(loadingSpans.length).toBe(1);
    });

    it('should show a loading placeholder when value is false', () => {
        component.observableValue = false;
        fixture.detectChanges();

        const loadingSpans = debugElement.queryAll(By.css('[role="status"]'));
        expect(loadingSpans.length).toBe(1);
    });

    it('should toggle from loading to content when value becomes truthy', () => {
        component.observableValue = null;
        fixture.detectChanges();

        // Verify loading state
        let loadingSpans = debugElement.queryAll(By.css('[role="status"]'));
        expect(loadingSpans.length).toBe(1);

        // Switch to content state
        component.observableValue = { loaded: true };
        fixture.detectChanges();

        // Verify content is shown
        const content = debugElement.query(By.css('.content'));
        expect(content).toBeTruthy();
    });

    it('should toggle from content to loading when value becomes falsy', () => {
        component.observableValue = { loaded: true };
        fixture.detectChanges();

        // Verify content state
        let content = debugElement.query(By.css('.content'));
        expect(content).toBeTruthy();

        // Switch to loading state
        component.observableValue = null;
        fixture.detectChanges();

        // Verify loading is shown
        const loadingSpans = debugElement.queryAll(By.css('[role="status"]'));
        expect(loadingSpans.length).toBe(1);
    });

    it('should not update view when value has not changed', () => {
        component.observableValue = { data: 'test' };
        fixture.detectChanges();

        const initialContent = debugElement.query(By.css('.content'));
        expect(initialContent).toBeTruthy();

        // Set same value (no change)
        component.observableValue = { data: 'test' };
        fixture.detectChanges();

        // Content should still be there
        const content = debugElement.query(By.css('.content'));
        expect(content).toBeTruthy();
    });

    it('should clear the view on destroy', () => {
        component.observableValue = { loaded: true };
        fixture.detectChanges();

        // Destroy the component
        fixture.destroy();

        // After destroy, the view should be cleared
        const content = debugElement.query(By.css('.content'));
        expect(content).toBeNull();
    });
});