/**
 * Design tokens for SIMA Swiss design system.
 *
 * CSS custom properties in global.css are the source of truth for all CSS styling.
 * These TypeScript exports exist for Plotly chart configs and other JS contexts
 * that cannot read CSS custom properties directly.
 */

export const colors = {
  black: '#000000',
  gray700: '#424242',
  gray500: '#9E9E9E',
  gray200: '#E0E0E0',
  gray100: '#F5F5F5',
  white: '#FFFFFF',
  accent: '#C41E3A',
  accentLight: '#F5E6E8',
} as const;

export const fonts = {
  body: '"Inter", "Helvetica Neue", Helvetica, Arial, sans-serif',
  mono: '"JetBrains Mono", monospace',
} as const;

export const typeScale = {
  h1: '2.441rem',
  h2: '1.953rem',
  h3: '1.563rem',
  body: '1rem',
  small: '0.8rem',
} as const;

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  xxl: '48px',
} as const;

export const grid = {
  columns: 12,
  gutter: '24px',
  maxWidth: '1200px',
  margin: '48px',
} as const;
