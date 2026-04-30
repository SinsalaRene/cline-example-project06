import { Component, OnInit, OnDestroy, ChangeDetectorRef, Inject } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { NavigationEnd, Router } from '@angular/router';
import { filter, takeUntil, startWith, map } from 'rxjs/operators';
import { Observable, Subject } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { ThemeService } from '../../core/services/theme.service';
import { ErrorHandlerService } from '../../core/services/error-handler.service';

@Component({
    selector: 'app-layout',
    templateUrl: './layout.component.html',
    styleUrls: ['./layout.component.css']
})
export class LayoutComponent implements OnInit, OnDestroy {
    private destroy$ = new Subject<void>();

    // Responsive layout state
    isMobile = false;
    isSidenavCollapsed = false;

    // Page title observable
    title$: Observable<string>;

    constructor(
        private breakpointObserver: BreakpointObserver,
        private router: Router,
        public authService: AuthService,
        public themeService: ThemeService,
        private errorHandler: ErrorHandlerService,
        private cdr: ChangeDetectorRef
    ) {
        // Initialize page title observable
        this.title$ = this.router.events.pipe(
            startWith(null),
            filter((event) => event instanceof NavigationEnd),
            map(() => this.getTitleFromRoute(this.router.routerState.root)),
        );
    }

    ngOnInit(): void {
        // Initialize theme
        this.themeService.loadTheme();

        // Listen for responsive breakpoint changes
        this.breakpointObserver.observe([
            '(max-width: 768px)',
        ]).subscribe((result) => {
            this.isMobile = result.matches;
            if (this.isMobile) {
                this.isSidenavCollapsed = true;
            }
            this.cdr.markForCheck();
        });

        // Listen for auth errors
        this.authService.authError$.subscribe(() => {
            // Auth error was handled in the service
        });
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    /**
     * Toggle sidenav collapsed state.
     */
    toggleSidenav(): void {
        this.isSidenavCollapsed = !this.isSidenavCollapsed;
    }

    /**
     * Toggle theme between light and dark.
     */
    toggleTheme(): void {
        this.themeService.toggleTheme();
    }

    /**
     * Navigate to profile page.
     */
    navigateToProfile(): void {
        this.router.navigate(['/profile']);
    }

    /**
     * Navigate to settings page.
     */
    navigateToSettings(): void {
        this.router.navigate(['/settings']);
    }

    /**
     * Navigate to login page.
     */
    navigateToLogin(): void {
        this.router.navigate(['/login']);
    }

    /**
     * Logout the current user.
     */
    logout(): void {
        this.authService.logout();
        this.router.navigate(['/login']);
    }

    /**
     * Get the title from the current route configuration.
     */
    private getTitleFromRoute(route: any): string {
        let child = route;
        while (child.firstChild) {
            child = child.firstChild;
        }

        if (child?.routeConfig?.data?.['title']) {
            return child.routeConfig.data['title'];
        }

        if (child?.routeConfig?.path) {
            // Use the path segment as title
            return child.routeConfig.path
                .split('/')
                .filter(Boolean)
                .map(part => part.charAt(0).toUpperCase() + part.slice(1))
                .join(' ');
        }

        return 'Firewall Manager';
    }
}