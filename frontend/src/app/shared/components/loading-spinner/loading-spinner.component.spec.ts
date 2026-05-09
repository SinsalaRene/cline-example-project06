import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { LoadingSpinnerComponent, SpinnerSize, SpinnerMode } from './loading-spinner.component';

/**
 * Unit tests for LoadingSpinnerComponent.
 *
 * Covers:
 * - Default inputs (size=medium, mode=inline)
 * - Size inputs (small, medium, large) with diameter computation
 * - Mode inputs (inline, overlay)
 * - Dynamic size changes via ngOnChanges
 */
describe('LoadingSpinnerComponent', () => {
    let component: LoadingSpinnerComponent;
    let fixture: ComponentFixture<LoadingSpinnerComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [LoadingSpinnerComponent],
        }).compileComponents();

        fixture = TestBed.createComponent(LoadingSpinnerComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create the component', () => {
        expect(component).toBeTruthy();
    });

    it('should have default size medium (diameter=40)', () => {
        expect(component.size).toEqual('medium');
        expect(component.diameter).toEqual(40);
    });

    it('should have default mode inline', () => {
        expect(component.mode).toEqual('inline');
    });

    it('should render a spinner for inline mode', () => {
        component.mode = 'inline';
        component.size = 'medium';
        fixture.detectChanges();
        const spinner = fixture.nativeElement.querySelector('mat-progress-spinner');
        expect(spinner).toBeTruthy();
    });

    it('should render an overlay with a spinner for overlay mode', () => {
        component.mode = 'overlay';
        fixture.detectChanges();
        const overlay = fixture.nativeElement.querySelector('.loading-spinner-overlay');
        expect(overlay).toBeTruthy();
    });

    /**
     * Verify diameter values for each size configuration.
     */
    it('should set diameter=28 for size=small', () => {
        component.size = 'small';
        fixture.detectChanges();
        expect(component.diameter).toEqual(28);
    });

    it('should set diameter=40 for size=medium', () => {
        component.size = 'medium';
        fixture.detectChanges();
        expect(component.diameter).toEqual(40);
    });

    it('should set diameter=64 for size=large', () => {
        component.size = 'large';
        fixture.detectChanges();
        expect(component.diameter).toEqual(64);
    });

    it('should update diameter when size input changes', fakeAsync(() => {
        expect(component.diameter).toEqual(40);
        component.size = 'large';
        fixture.detectChanges();
        expect(component.diameter).toEqual(64);
        component.size = 'small';
        fixture.detectChanges();
        expect(component.diameter).toEqual(28);
    }));

    it('should display overlay with fixed positioning styles', () => {
        component.mode = 'overlay';
        fixture.detectChanges();
        const overlay = fixture.nativeElement.querySelector('.loading-spinner-overlay');
        expect(overlay.style.position).toEqual('fixed');
        expect(overlay.style.zIndex).toEqual('9999');
    });
});