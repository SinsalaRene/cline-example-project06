import { Component, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { BreakpointObserver } from '@angular/cdk/layout';
import { AuthService } from './core/services/auth.service';

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
    isHandset!: Observable<boolean>;
    readonly displayedColumns: string[] = ['name', 'priority', 'action', 'protocol', 'source', 'destination', 'status', 'actions'];

    constructor(
        private breakpointObserver: BreakpointObserver,
        private authService: AuthService
    ) { }

    ngOnInit(): void {
        this.isHandset = this.breakpointObserver.observe('(max-width: 599px)');
    }

    logout(): void {
        this.authService.logout();
    }
}