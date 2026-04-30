import { Injectable, inject } from '@angular/core';
import { Router, CanActivate, UrlTree, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { Observable } from 'rxjs';

/**
 * Guard for authenticated users.
 * Redirects to login if not authenticated.
 */
@Injectable({
    providedIn: 'root'
})
export class AuthGuard implements CanActivate {
    private authService = inject(AuthService);
    private router = inject(Router);

    canActivate(
        route: ActivatedRouteSnapshot,
        state: RouterStateSnapshot
    ): boolean | UrlTree {
        if (this.authService.isLoggedIn()) {
            return true;
        }
        return this.router.createUrlTree(['/login']);
    }
}

/**
 * Guard for reverse authentication.
 * Redirects to the intended route if already authenticated.
 * Redirects unauthenticated users to the login page.
 */
@Injectable({
    providedIn: 'root'
})
export class ReverseAuthGuard implements CanActivate {
    private authService = inject(AuthService);
    private router = inject(Router);

    canActivate(
        route: ActivatedRouteSnapshot,
        state: RouterStateSnapshot
    ): boolean | UrlTree {
        if (this.authService.isLoggedIn()) {
            return this.router.createUrlTree(['/dashboard']);
        }
        return true;
    }
}

/**
 * Guard for public routes.
 * Allows unauthenticated users to access.
 * Redirects authenticated users away from login page.
 */
@Injectable({
    providedIn: 'root'
})
export class PublicGuard implements CanActivate {
    private authService = inject(AuthService);
    private router = inject(Router);

    canActivate(
        route: ActivatedRouteSnapshot,
        state: RouterStateSnapshot
    ): boolean | UrlTree {
        if (this.authService.isLoggedIn()) {
            return this.router.createUrlTree(['/dashboard']);
        }
        return true;
    }
}

/**
 * Guard for role-based access.
 * Redirects to login if not authenticated or missing required role.
 */
@Injectable({
    providedIn: 'root'
})
export class RoleGuard implements CanActivate {
    private authService = inject(AuthService);
    private router = inject(Router);

    canActivate(
        route: ActivatedRouteSnapshot,
        state: RouterStateSnapshot
    ): boolean | UrlTree {
        const requiredRoles = route.data['roles'] as string[];

        if (!this.authService.isLoggedIn()) {
            return this.router.createUrlTree(['/login']);
        }

        const userRoles = this.authService.userSubject.value?.roles ?? [];
        const hasRole = requiredRoles.some(role => userRoles.includes(role));

        if (!hasRole) {
            return this.router.createUrlTree(['/unauthorized']);
        }

        return true;
    }
}

/**
 * Guard for permission-based access.
 * Redirects to unauthorized page if user lacks required permission.
 */
@Injectable({
    providedIn: 'root'
})
export class PermissionGuard implements CanActivate {
    private authService = inject(AuthService);
    private router = inject(Router);

    canActivate(
        route: ActivatedRouteSnapshot,
        state: RouterStateSnapshot
    ): boolean | UrlTree {
        const requiredPermission = route.data['permission'] as string;

        if (!this.authService.isLoggedIn()) {
            return this.router.createUrlTree(['/login']);
        }

        if (!requiredPermission) {
            return true;
        }

        if (!this.authService.hasPermission(requiredPermission)) {
            return this.router.createUrlTree(['/unauthorized']);
        }

        return true;
    }
}