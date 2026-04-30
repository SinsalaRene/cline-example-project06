import { NgModule, Provider } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatDialogModule } from '@angular/material/dialog';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatMenuModule } from '@angular/material/menu';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './components/app.component';
import { LayoutModule } from './modules/layout.module';
import { SharedModule } from './shared/shared.module';
import { AuthModule } from './modules/auth/auth.module';
import { CoreService } from './core/services/api.service';
import { AuthService } from './core/services/auth.service';
import { ErrorHandlerService } from './core/services/error-handler.service';
import { ThemeService } from './core/services/theme.service';
import { HttpRequestInterceptor } from './core/interceptors/http-request.interceptor';
import { HttpErrorInterceptor } from './core/interceptors/http-error.interceptor';

/** HTTP interceptor providers configuration */
const HTTP_INTERCEPTOR_PROVIDERS: Provider[] = [
    { provide: HTTP_INTERCEPTORS, useClass: HttpRequestInterceptor, multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: HttpErrorInterceptor, multi: true },
];

@NgModule({
    declarations: [
        AppComponent,
    ],
    imports: [
        BrowserModule,
        BrowserAnimationsModule,
        HttpClientModule,
        ReactiveFormsModule,
        FormsModule,
        AppRoutingModule,
        LayoutModule,
        SharedModule,
        AuthModule,
        // Material modules
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        MatInputModule,
        MatFormFieldModule,
        MatSelectModule,
        MatButtonModule,
        MatIconModule,
        MatCardModule,
        MatTabsModule,
        MatDialogModule,
        MatListModule,
        MatProgressSpinnerModule,
        MatExpansionModule,
        MatChipsModule,
        MatSidenavModule,
        MatMenuModule,
    ],
    providers: [
        CoreService,
        AuthService,
        ErrorHandlerService,
        ThemeService,
        ...HTTP_INTERCEPTOR_PROVIDERS
    ],
    bootstrap: [AppComponent],
})
export class AppModule { }