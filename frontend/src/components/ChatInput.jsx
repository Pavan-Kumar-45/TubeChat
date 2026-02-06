import { useRef, useState } from 'react';
import { ArrowUp } from 'lucide-react';
import clsx from 'clsx';

/**
 * Chat input bar with auto-growing textarea. Enter sends, Ctrl+Enter adds a newline.
 * @param {{ onSend: (text: string) => void, disabled: boolean }} props
 */
export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('');
  const ref = useRef(null);

  const send = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
    // reset textarea height
    if (ref.current) ref.current.style.height = 'auto';
  };

  const handleKeyDown = (e) => {
    // Ctrl+Enter = newline (default textarea behavior with modifier)
    if (e.key === 'Enter' && !e.ctrlKey && !e.shiftKey) {
      e.preventDefault();
      send();
    }
    // Ctrl+Enter or Shift+Enter inserts newline (default behavior)
  };

  return (
    <div className="border-t border-[var(--color-border)] bg-[var(--color-bg)]">
      <div className="max-w-3xl mx-auto px-4 py-3">
        <div className="flex items-end gap-2 bg-[var(--color-input-bg)] rounded-2xl border border-[var(--color-border)] focus-within:border-[var(--color-accent)] transition-colors px-4 py-2">
          <textarea
            ref={ref}
            rows={1}
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the video... (Ctrl+Enter for new line)"
            disabled={disabled}
            className="flex-1 bg-transparent outline-none resize-none text-sm leading-relaxed max-h-40 text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)]"
          />
          <button
            onClick={send}
            disabled={!value.trim() || disabled}
            className={clsx(
              'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors',
              value.trim() && !disabled
                ? 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]'
                : 'bg-[var(--color-border)] text-[var(--color-text-secondary)] cursor-not-allowed'
            )}
          >
            <ArrowUp size={16} />
          </button>
        </div>
        <p className="text-[10px] text-[var(--color-text-secondary)] text-center mt-1.5">
          Enter to send · Ctrl+Enter for new line
        </p>
      </div>
    </div>
  );
}
