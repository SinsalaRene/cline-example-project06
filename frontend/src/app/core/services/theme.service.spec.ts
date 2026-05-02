import { TestBed } from '@angular/core/testing';
import { ThemeService } from './theme.service';

describe('ThemeService', () => {
    let service: ThemeService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [ThemeService]
        });

        service = TestBed.inject(ThemeService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('setTheme', () => {
        it('should set theme to dark', () => {
            service.setTheme('dark');
            const htmlElement = document.documentElement;
            expect(htmlElement.classList.contains('dark')).toBe(true);
        });

        it('should set theme to light', () => {
            service.setTheme('light');
            const htmlElement = document.documentElement;
            expect(htmlElement.classList.contains('dark')).toBe(false);
        });

        it('should handle invalid theme by defaulting to dark', () => {
            service.setTheme('invalid');
            const htmlElement = document.documentElement;
            expect(htmlElement.classList.contains('dark')).toBe(true);
        });
    });

    describe('toggleTheme', () => {
        it('should toggle from dark to light', () => {
            service.setTheme('dark');
            service.toggleTheme();
            const htmlElement = document.documentElement;
            expect(htmlElement.classList.contains('dark')).toBe(false);
        });

        it('should toggle from light to dark', () => {
            service.setTheme('light');
            service.toggleTheme();
            const htmlElement = document.documentElement;
            expect(htmlElement.classList.contains('dark')).toBe(true);
        });
    });

    describe('getPreferredTheme', () => {
        it('should return the preferred theme', () => {
            const theme = service.getPreferredTheme();
            expect(['dark', 'light']).toContain(theme);
        });
    });

    describe('getTheme', () => {
        it('should return current theme', () => {
            service.setTheme('dark');
            const theme = service.getTheme();
            expect(theme).toBe('dark');
        });
    });
});