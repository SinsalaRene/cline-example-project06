import { Component, ElementRef, Input, OnChanges, SimpleChanges, Renderer2 } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

/**
 * Configuration for spinner sizes.
 * Maps size tokens to Angular Material diameter values and CSS sizing.
 */
export type SpinnerSize = 'small' | 'medium' | 'large';

/**
 * Configuration for spinner display modes.
 * - `inline`: Renders the spinner inline within the document flow.
 * - `overlay`: Renders the spinner as a fixed-position overlay covering the entire screen.
 */
export type SpinnerMode = 'inline' | 'overlay';

/**
 * Loading Spinner Component
 *
 * A reusable spinner component that displays an Angular Material progress
 * spinner with configurable size and display mode.
 *
 * Usage (inline mode):
 *   `<app-loading-spinner size="medium"></app-loading-spinner>`
 *
 * Usage (overlay mode):
 *   `<app-loading-spinner size="large" mode="overlay"></app-loading-spinner>`
 *
 * @example
 * ```html
 * <!-- Medium inline spinner -->
 * <app-loading-spinner size="medium"></app-loading-spinner>
 *
 * <!-- Large overlay spinner -->
 * <app-loading-spinner [size]="large" mode="overlay"></app-loading-spinner>
 * ```
 */
@Component({
    selector: 'app-loading-spinner',
    standalone: true,
    imports: [CommonModule, MatProgressSpinnerModule],
    template: `
    <!-- Inline mode: just show the spinner -->
    <ng-container *ngIf="mode === 'inline'">
      <mat-progress-spinner
        [color]="'accent'"
        [mode]="'indeterminate'"
        [diameter]="diameter"
      ></mat-progress-spinner>
    </ng-container>

    <!-- Overlay mode: fixed full-screen overlay with centered spinner -->
    <ng-container *ngIf="mode === 'overlay'">
      <div class="loading-spinner-overlay">
        <mat-progress-spinner
          [color]="'accent'"
          [mode]="'indeterminate'"
          [diameter]="diameter"
          class="loading-spinner-centered"
        ></mat-progress-spinner>
      </div>
    </ng-container>
  `,
    styles: [`
    /* Overlay mode styles */
    .loading-spinner-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    }

    .loading-spinner-centered {
      display: block;
    }
  `],
})
export class LoadingSpinnerComponent implements OnChanges {
    /**
     * The visual size of the spinner.
     * - `small`: Compact spinner for inline use within dense content areas.
     * - `medium`: Default size for standard loading states.
     * - `large`: Prominent spinner for overlay mode or prominent loading states.
     */
    @Input() size: SpinnerSize = 'medium';

    /**
     * The display mode of the spinner.
     * - `inline`: Renders inline within the document flow.
     * - `overlay`: Renders as a full-screen fixed overlay with a dimmed background.
     */
    @Input() mode: SpinnerMode = 'inline';

    /** Computed diameter value based on the size input. */
    private _diameter: number = 40;

    /**
     * Getter for the computed diameter value.
     * Exposed as a getter so templates can bind to `diameter` directly.
     */
    get diameter(): number {
        return this._diameter;
    }

    /**
     * Lifecycle hook called when one or more input properties change.
     * Recomputes the spinner diameter based on the current size.
     *
     * @param changes - The current input changes triggering this lifecycle hook.
     */
    ngOnChanges(changes: SimpleChanges): void {
        if (changes['size'] || !this._diameter) {
            this._computeDiameter();
        }
    }

    /**
     * Computes the spinner diameter based on the current size value.
     */
    private _computeDiameter(): void {
        switch (this.size) {
            case 'small':
                this._diameter = 28;
                break;
            case 'medium':
                this._diameter = 40;
                break;
            case 'large':
                this._diameter = 64;
                break;
            default:
                this._diameter = 40;
        }
    }
}