import type { ReactElement, ReactNode } from 'react';
import { act, render } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import i18n from '../i18n';

/**
 * Render helper wiring the two providers every page needs: i18n (all copy goes
 * through `t()`) and a router (nav links and `useLocation`).
 *
 * Language is reset to Spanish before each render so a test that switches to
 * English cannot leak into the next one -- i18n is a module-level singleton.
 */
export async function setLanguage(lng: 'es' | 'en') {
  // Wrapped in act(): changeLanguage re-renders every mounted component that
  // uses useTranslation, and React warns about state updates outside act.
  await act(async () => {
    await i18n.changeLanguage(lng);
  });
}

function Providers({ children }: { children: ReactNode }) {
  return (
    <I18nextProvider i18n={i18n}>
      <MemoryRouter>{children}</MemoryRouter>
    </I18nextProvider>
  );
}

export function renderWithProviders(ui: ReactElement, options?: { route?: string }) {
  if (options?.route) {
    window.history.pushState({}, '', options.route);
  }
  return render(ui, { wrapper: Providers });
}

export { i18n };
