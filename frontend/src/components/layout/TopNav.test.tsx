import { beforeEach, describe, expect, it } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TopNav from './TopNav';
import { renderWithProviders, setLanguage } from '../../test/render';

/**
 * THEORY: the UI standard (.claude/skills/ui-responsive) requires navigation to
 * answer "where am I, where can I go, how do I get back" on every screen: six
 * flat destinations, aria-current on the active link, and a mobile drawer that
 * closes on route change / Escape / backdrop click, exposes aria-expanded on
 * its trigger, and locks body scroll while open. Each rule is tested as
 * observable behaviour.
 *
 * NOTE: renderWithProviders' `route` option pushes onto window.history, which
 * MemoryRouter ignores -- every render starts at "/". Active-link behaviour is
 * therefore exercised by actually navigating (clicking links), which is the
 * stronger test anyway.
 */

/** The hamburger trigger, found by its accessible name in either open/closed state. */
function getHamburger() {
  return screen.getByRole('button', { name: /Abrir menú|Cerrar menú/ });
}

describe('TopNav', () => {
  beforeEach(async () => {
    await setLanguage('es');
    document.body.style.overflow = '';
  });

  it('offers exactly the six destinations, flat, plus a brand link back to home', () => {
    renderWithProviders(<TopNav />);

    const list = screen.getByRole('list');
    const links = within(list).getAllByRole('link');
    expect(links.map((a) => a.getAttribute('href'))).toEqual([
      '/',
      '/mortalidad',
      '/tarificacion',
      '/scr',
      '/sensibilidad',
      '/metodologia',
    ]);

    // The brand mark must always return to "/".
    const brand = screen.getByRole('link', { name: 'SIMA, página principal' });
    expect(brand).toHaveAttribute('href', '/');
  });

  it('marks the current page with aria-current="page" and moves the mark on navigation', async () => {
    const user = userEvent.setup();
    renderWithProviders(<TopNav />);
    const list = screen.getByRole('list');

    // Starts at "/": only INICIO carries the mark.
    expect(within(list).getByRole('link', { name: 'INICIO' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(list).getByRole('link', { name: 'MORTALIDAD' })).not.toHaveAttribute(
      'aria-current',
    );

    await user.click(within(list).getByRole('link', { name: 'MORTALIDAD' }));

    expect(within(list).getByRole('link', { name: 'MORTALIDAD' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(list).getByRole('link', { name: 'INICIO' })).not.toHaveAttribute(
      'aria-current',
    );
  });

  it('reports drawer state to assistive tech via aria-expanded on the trigger', async () => {
    const user = userEvent.setup();
    renderWithProviders(<TopNav />);

    const hamburger = getHamburger();
    expect(hamburger).toHaveAttribute('aria-expanded', 'false');

    await user.click(hamburger);
    expect(hamburger).toHaveAttribute('aria-expanded', 'true');

    await user.click(hamburger);
    expect(hamburger).toHaveAttribute('aria-expanded', 'false');
  });

  it('closes the drawer on route change so a tap lands on the page, not the menu', async () => {
    const user = userEvent.setup();
    renderWithProviders(<TopNav />);

    await user.click(getHamburger());
    expect(getHamburger()).toHaveAttribute('aria-expanded', 'true');

    await user.click(screen.getByRole('link', { name: 'MORTALIDAD' }));
    expect(getHamburger()).toHaveAttribute('aria-expanded', 'false');
  });

  it('closes the drawer on Escape and returns focus to the trigger', async () => {
    const user = userEvent.setup();
    renderWithProviders(<TopNav />);

    await user.click(getHamburger());
    expect(getHamburger()).toHaveAttribute('aria-expanded', 'true');

    await user.keyboard('{Escape}');
    expect(getHamburger()).toHaveAttribute('aria-expanded', 'false');
    expect(getHamburger()).toHaveFocus();
  });

  it('closes the drawer when the backdrop is clicked', async () => {
    const user = userEvent.setup();
    const { container } = renderWithProviders(<TopNav />);

    // No backdrop while closed.
    expect(container.querySelector('div[aria-hidden="true"]')).toBeNull();

    await user.click(getHamburger());
    const backdrop = container.querySelector('div[aria-hidden="true"]');
    expect(backdrop, 'the open drawer must render a click-to-dismiss backdrop').not.toBeNull();

    await user.click(backdrop as Element);
    expect(getHamburger()).toHaveAttribute('aria-expanded', 'false');
  });

  it('locks body scroll while the drawer is open and restores it on close', async () => {
    const user = userEvent.setup();
    renderWithProviders(<TopNav />);

    expect(document.body.style.overflow).not.toBe('hidden');

    await user.click(getHamburger());
    expect(document.body.style.overflow).toBe('hidden');

    await user.keyboard('{Escape}');
    expect(document.body.style.overflow).not.toBe('hidden');
  });

  it('translates the destination labels', async () => {
    renderWithProviders(<TopNav />);
    expect(screen.getByRole('link', { name: 'INICIO' })).toBeInTheDocument();

    await setLanguage('en');
    expect(screen.getByRole('link', { name: 'HOME' })).toBeInTheDocument();
  });
});
