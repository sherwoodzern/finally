import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { ChatDrawer } from './ChatDrawer';

describe('<ChatDrawer />', () => {
  it('is open by default with w-[380px]', () => {
    render(<ChatDrawer><div data-testid="child-body" /></ChatDrawer>);
    const aside = screen.getByTestId('chat-drawer');
    expect(aside.className).toContain('w-[380px]');
    expect(screen.getByTestId('child-body')).toBeInTheDocument();
  });

  it('toggles to collapsed (w-12) when toggle button is clicked (D-07)', () => {
    render(<ChatDrawer><div data-testid="child-body" /></ChatDrawer>);
    fireEvent.click(screen.getByRole('button', { name: 'Collapse chat' }));
    const aside = screen.getByTestId('chat-drawer');
    expect(aside.className).toContain('w-12');
    // children body hidden when collapsed
    expect(screen.queryByTestId('child-body')).toBeNull();
  });
});
