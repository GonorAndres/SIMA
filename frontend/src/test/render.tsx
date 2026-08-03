import type { ReactElement, ReactNode } from 'react';
import { act, render } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import i18n from '../i18n';

/**
 * Render helper wiring the two providers every page needs: i18n (all copy goes
 * through `t()`) and a router (nav links and `useLocation`).
 */

export async function setLanguage(lng: 'es' | 'en') {
  // Wrapped in act(): changeLanguage re-renders every mounted component that
  // uses useTranslation, and React warns about state updates outside act.
  await act(async () => {
    await i18n.changeLanguage(lng);
  });
}

interface RenderOptions {
  /**
   * Starting path. Passed to MemoryRouter as `initialEntries` -- MemoryRouter
   * keeps its own in-memory history and ignores window.history entirely, so
   * pushState here would silently do nothing and every test would start at '/'.
   */
  route?: string;
}

export function renderWithProviders(ui: ReactElement, options?: RenderOptions) {
  const initialEntries = [options?.route ?? '/'];

  function Providers({ children }: { children: ReactNode }) {
    return (
      <I18nextProvider i18n={i18n}>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </I18nextProvider>
    );
  }

  return render(ui, { wrapper: Providers });
}

export { i18n };
