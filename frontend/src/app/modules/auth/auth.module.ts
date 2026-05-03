import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { SharedModule } from '../../shared/shared.module';
import { LoginComponent } from './login/login.component';
import { RoleDirective } from './directives/role.directive';
import { LogoutComponent } from './logout/logout.component';

@NgModule({
    declarations: [],
    imports: [
        CommonModule,
        SharedModule,
        ReactiveFormsModule,
        FormsModule,
        RouterModule,
        LoginComponent,
        LogoutComponent,
        RoleDirective,
    ],
    exports: [
        LoginComponent,
        LogoutComponent,
        RoleDirective,
    ],
})
export class AuthModule { }
