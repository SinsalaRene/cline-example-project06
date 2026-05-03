import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { RulesListComponent } from './components/rules-list.component';
import { RulesService } from './services/rules.service';

const routes: Routes = [
    { path: '', component: RulesListComponent }
];

@NgModule({
    imports: [
        RouterModule.forChild(routes),
        RulesListComponent
    ],
    providers: [RulesService]
})
export class RulesModule { }
