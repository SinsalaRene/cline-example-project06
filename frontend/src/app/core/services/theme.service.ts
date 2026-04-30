import { Injectable, signal, effect, inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';

/**
 * Theme configuration interface.
 * Defines the structure for theme settings.
 */
export interface ThemeConfig {
    mode: 'light' | 'dark' | 'auto';
    primaryColor: string;
    accentColor: string;
}

/**
 * Default theme configuration.
 */
const DEFAULT_THEME: ThemeConfig = {
    mode: 'light',
    primaryColor: '#1976d2',
    accentColor: '#ff9800',
};

/**
 * Theme Service
 * Provides centralized theme management across the application.
 * Persists theme preferences in localStorage.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
    private document = inject(DOCUMENT);

    /**
     * Current theme mode: light, dark, or auto.
     * Using signal for reactive state.
     */
    private themeMode = signal<'light' | 'dark' | 'auto'>('light');

    /**
     * Observable-like property for theme mode.
     * Components can subscribe to this for reactive updates.
     */
    readonly mode$ = {
        subscribe: (next: (value: 'light' | 'dark' | 'auto') => void) => {
            // For compatibility, expose as observable
            const mode = this.themeMode();
            next(mode);
        },
    };

    /**
     * Whether dark theme is currently active.
     */
    get isDarkTheme(): boolean {
        const mode = this.themeMode();
        return mode === 'dark' || (mode === 'auto' && this.isDarkModeSystem());
    }

    /**
     * Whether light theme is currently active.
     */
    get isLightTheme(): boolean {
        return !this.isDarkTheme;
    }

    /**
     * Get the current theme mode.
     */
    getMode(): 'light' | 'dark' | 'auto' {
        return this.themeMode();
    }

    /**
     * Set the theme mode.
     * @param mode The theme mode to set
     */
    setMode(mode: 'light' | 'dark' | 'auto'): void {
        this.themeMode.set(mode);
        this.applyTheme();
        this.persistTheme(mode);
    }

    /**
     * Toggle between light and dark themes.
     */
    toggleTheme(): void {
        const currentMode = this.themeMode();
        const newMode = currentMode === 'dark' ? 'light' : 'dark';
        this.setMode(newMode);
    }

    /**
     * Set to system preference mode.
     * Automatically switches between light and dark based on OS preference.
     */
    setSystemTheme(): void {
        this.setMode('auto');
    }

    /**
     * Check if the system prefers dark mode.
     * Uses matchMedia to detect system preference.
     */
    private isDarkModeSystem(): boolean {
        if (typeof window !== 'undefined' && window.matchMedia) {
            return window.matchMedia('(prefers-color-scheme: dark)').matches;
        }
        return false;
    }

    /**
     * Apply the current theme to the document.
     * Adds/removes 'dark-theme' class on the body element.
     */
    private applyTheme(): void {
        const shouldApplyDark = this.isDarkTheme;

        if (shouldApplyDark) {
            this.document.body.classList.add('dark-theme');
            this.document.body.classList.remove('light-theme');
        } else {
            this.document.body.classList.add('light-theme');
            this.document.body.classList.remove('dark-theme');
        }

        // Update theme meta tag for mobile browsers
        this.updateThemeMetaTag(shouldApplyDark ? '#121212' : '#ffffff');
    }

    /**
     * Update the theme-color meta tag for mobile browsers.
     * @param color The theme color hex value
     */
    private updateThemeMetaTag(color: string): void {
        let metaTag = this.document.querySelector('meta[name="theme-color"]');
        if (!metaTag) {
            metaTag = this.document.createElement('meta');
            (metaTag as HTMLMetaElement).name = 'theme-color';
            this.document.head.appendChild(metaTag);
        }
        (metaTag as HTMLMetaElement).content = color;
    }

    /**
     * Load persisted theme preference from localStorage.
     */
    loadTheme(): void {
        try {
            const savedTheme = localStorage.getItem('app-theme');
            if (savedTheme && ['light', 'dark', 'auto'].includes(savedTheme)) {
                this.themeMode.set(savedTheme as 'light' | 'dark' | 'auto');
            }
        } catch {
            // Fall back to default theme
            console.warn('Failed to load theme preference from localStorage');
        }
        this.applyTheme();
    }

    /**
     * Persist theme preference to localStorage.
     * @param theme The theme to persist
     */
    private persistTheme(theme: 'light' | 'dark' | 'auto'): void {
        try {
            localStorage.setItem('app-theme', theme);
        } catch {
            // localStorage might be unavailable
            console.warn('Failed to persist theme preference to localStorage');
        }
    }

    /**
     * Get the full theme configuration.
     */
    getThemeConfig(): ThemeConfig {
        return {
            ...DEFAULT_THEME,
            mode: this.themeMode(),
        };
    }

    /**
     * Reset theme to defaults.
     */
    resetTheme(): void {
        this.setMode(DEFAULT_THEME.mode);
    }

    /**
     * Set theme colors.
     * @param colors The color configuration to apply
     */
    setColors(colors: Partial<Pick<ThemeConfig, 'primaryColor' | 'accentColor'>>): void {
        // In a full implementation, this would update CSS custom properties
        console.log('Theme colors updated:', colors);
    }
}