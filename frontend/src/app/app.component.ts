import { Component, OnInit } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { Observable, filter, map, startWith } from 'rxjs';
import { BreakpointObserver, BreakpointState } from '@angular/cdk/layout';
import { AuthService } from './core/services/auth.service';

type DrawerMode = 'over' | 'push';

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
    drawerMode: Observable<DrawerMode>;
    sidenavOpened: Observable<boolean>;
    isLoginRoute = false;
    readonly displayedColumns: string[] = ['name', 'priority', 'action', 'protocol', 'source', 'destination', 'status', 'actions'];

    constructor(
        private router: Router,
        private breakpointObserver: BreakpointObserver,
        private authService: AuthService
    ) {
        this.drawerMode = new Observable<DrawerMode>(observer => {
            observer.next('push');
        });
        this.sidenavOpened = new Observable<boolean>(observer => {
            observer.next(true);
        });
    }

    ngOnInit(): void {
        // Check if current route is the login page
        this.router.events
            .pipe(filter(event => event instanceof NavigationEnd))
            .subscribe((event: any) => {
                this.isLoginRoute = event.url === '/login';
            });

        // Check on init as well
        this.isLoginRoute = this.router.url === '/login';

        this.drawerMode = this.breakpointObserver.observe('(max-width: 599px)').pipe(
            map((r: BreakpointState) => {
                const m = r.matches;
                if (m === true) return 'over';
                return 'push';
            }),
            startWith<DrawerMode>('push')
        );
        this.sidenavOpened = this.breakpointObserver.observe('(max-width: 599px)').pipe(
            map((r: BreakpointState) => {
                const m = r.matches;
                return m !== true;
            }),
            startWith(true)
        );
    }

    logout(): void {
        this.authService.logout();
    }
}