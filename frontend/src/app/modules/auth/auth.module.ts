import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { SharedModule } from '../../shared/shared.module';
import { LoginComponent } from './login/login.component';
import { LogoutComponent } from './logout/logout.component';
import { RoleDirective } from './directives/role.directive';

@NgModule({
    declarations: [
        LoginComponent,
        LogoutComponent,
        RoleDirective,
    ],
    imports: [
        CommonModule,
        SharedModule,
        ReactiveFormsModule,
        FormsModule,
        RouterModule,
    ],
    exports: [
        LoginComponent,
        LogoutComponent,
        RoleDirective,
    ],
})
export class AuthModule { }