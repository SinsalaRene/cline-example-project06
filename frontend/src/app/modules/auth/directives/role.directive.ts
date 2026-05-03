import {
    Directive,
    TemplateRef,
    ViewContainerRef,
    OnInit,
    Input,
} from '@angular/core';
import { AuthService } from '../../../core/services/auth.service';

/**
 * Directive to conditionally render content based on user roles.
 *
 * Usage:
 * ```html
 * <div *appRole="'admin'">Only admins see this</div>
 * <div *appRole="['admin', 'editor']">Admins or editors see this</div>
 * ```
 */
@Directive({
    selector: '[appRole]',
    standalone: true,
})
export class RoleDirective implements OnInit {
    @Input() appRole: string | string[] = '';

    private hasAccess = false;

    constructor(
        private templateRef: TemplateRef<unknown>,
        private viewContainer: ViewContainerRef,
        private authService: AuthService
    ) { }

    ngOnInit(): void {
        this.checkAccess();
    }

    /**
     * Check if the user has any of the required roles.
     */
    private checkAccess(): void {
        const requiredRoles = this.getRequiredRoles();
        this.hasAccess = requiredRoles.some((role: string) =>
            this.authService.hasRole(role)
        );

        if (this.hasAccess) {
            this.viewContainer.createEmbeddedView(this.templateRef);
        } else {
            this.viewContainer.clear();
        }
    }

    /**
     * Get the required roles from the directive input.
     */
    private getRequiredRoles(): string[] {
        if (Array.isArray(this.appRole)) {
            return this.appRole;
        }

        if (typeof this.appRole === 'string') {
            return [this.appRole];
        }

        return [];
    }
}
