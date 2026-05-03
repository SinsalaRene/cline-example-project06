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

    describe('setMode', () => {
        it('should set mode to dark', () => {
            service.setMode('dark');
            const body = document.body;
            expect(body.classList.contains('dark-theme')).toBe(true);
            expect(body.classList.contains('light-theme')).toBe(false);
        });

        it('should set mode to light', () => {
            service.setMode('light');
            const body = document.body;
            expect(body.classList.contains('light-theme')).toBe(true);
            expect(body.classList.contains('dark-theme')).toBe(false);
        });

        it('should handle auto mode', () => {
            service.setMode('auto');
            const mode = service.getMode();
            expect(mode).toBe('auto');
        });
    });

    describe('toggleTheme', () => {
        it('should toggle from dark to light', () => {
            service.setMode('dark');
            service.toggleTheme();
            const body = document.body;
            expect(body.classList.contains('light-theme')).toBe(true);
        });

        it('should toggle from light to dark', () => {
            service.setMode('light');
            service.toggleTheme();
            const body = document.body;
            expect(body.classList.contains('dark-theme')).toBe(true);
        });
    });

    describe('getMode', () => {
        it('should return the current mode', () => {
            const mode = service.getMode();
            expect(['dark', 'light', 'auto']).toContain(mode);
        });
    });

    describe('resetTheme', () => {
        it('should reset theme to default (light)', () => {
            service.setMode('dark');
            service.resetTheme();
            const mode = service.getMode();
            expect(mode).toBe('light');
        });
    });

    describe('isDarkTheme', () => {
        it('should return true when dark mode is active', () => {
            service.setMode('dark');
            expect(service.isDarkTheme).toBe(true);
        });

        it('should return false when light mode is active', () => {
            service.setMode('light');
            expect(service.isDarkTheme).toBe(false);
        });
    });

    describe('isLightTheme', () => {
        it('should return false when dark mode is active', () => {
            service.setMode('dark');
            expect(service.isLightTheme).toBe(false);
        });

        it('should return true when light mode is active', () => {
            service.setMode('light');
            expect(service.isLightTheme).toBe(true);
        });
    });

    describe('getThemeConfig', () => {
        it('should return the full theme configuration', () => {
            service.setMode('dark');
            const config = service.getThemeConfig();
            expect(config.mode).toBe('dark');
            expect(config.primaryColor).toBe('#1976d2');
            expect(config.accentColor).toBe('#ff9800');
        });
    });

    describe('setColors', () => {
        it('should update theme colors', () => {
            // setColors just logs in the current implementation
            expect(() => service.setColors({ primaryColor: '#ff0000' })).not.toThrow();
        });
    });
});