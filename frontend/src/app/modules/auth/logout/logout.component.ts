import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-logout',
    standalone: true,
    template: '',
    styles: [],
})
export class LogoutComponent implements OnInit {
    constructor(
        private authService: AuthService,
        private router: Router
    ) { }

    ngOnInit(): void {
        // Perform logout action
        this.authService.logout();

        // Redirect to login page
        this.router.navigate(['/login']);
    }
}