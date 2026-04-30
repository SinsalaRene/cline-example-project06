import {
    Directive,
    TemplateRef,
    ViewContainerRef,
    Inject,
    OnInit,
    OnChanges,
    SimpleChanges,
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
})
export class RoleDirective implements OnInit {
    private hasAccess = false;

    constructor(
        private templateRef: TemplateRef<any>,
        private viewContainer: ViewContainerRef,
        @Inject(AuthService) private authService: AuthService
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
        const roleValue = this.templateRef;
        const roles = this.templateRef['node'];

        // Parse the role value from the directive input
        const input = this.templateRef['_data']?.context?.roles ??
            this.templateRef['_data']?.context?.appRole;

        if (Array.isArray(input)) {
            return input;
        }

        if (typeof input === 'string') {
            return [input];
        }

        return [];
    }
}