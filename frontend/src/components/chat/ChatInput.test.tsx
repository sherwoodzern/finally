import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { ChatInput } from './ChatInput';

describe('<ChatInput />', () => {
  let onSubmit: ((content: string) => void) & ReturnType<typeof vi.fn>;
  beforeEach(() => {
    onSubmit = vi.fn() as ((content: string) => void) & ReturnType<typeof vi.fn>;
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('Enter (no shift) submits the trimmed content (UI-SPEC §5.8)', () => {
    render(<ChatInput onSubmit={onSubmit} isPending={false} />);
    const ta = screen.getByPlaceholderText('Ask me about your portfolio…');
    fireEvent.change(ta, { target: { value: '  hello  ' } });
    fireEvent.keyDown(ta, { key: 'Enter' });
    expect(onSubmit).toHaveBeenCalledWith('hello');
  });

  it('Shift+Enter does NOT submit (newline default)', () => {
    render(<ChatInput onSubmit={onSubmit} isPending={false} />);
    const ta = screen.getByPlaceholderText('Ask me about your portfolio…');
    fireEvent.change(ta, { target: { value: 'hello' } });
    fireEvent.keyDown(ta, { key: 'Enter', shiftKey: true });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('Send button submits via form click', () => {
    render(<ChatInput onSubmit={onSubmit} isPending={false} />);
    const ta = screen.getByPlaceholderText('Ask me about your portfolio…');
    fireEvent.change(ta, { target: { value: 'hello' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    expect(onSubmit).toHaveBeenCalledWith('hello');
  });

  it('disabled while pending: textarea + Send button blocked', () => {
    render(<ChatInput onSubmit={onSubmit} isPending={true} />);
    const ta = screen.getByPlaceholderText('Ask me about your portfolio…') as HTMLTextAreaElement;
    const send = screen.getByRole('button', { name: 'Send' }) as HTMLButtonElement;
    expect(ta.disabled).toBe(true);
    expect(send.disabled).toBe(true);
  });
});
