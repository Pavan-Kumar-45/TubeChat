import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Bot, Copy, Check, Code } from 'lucide-react';
import { useState, useCallback } from 'react';

/* ── Code block with copy + language label ── */
/**
 * Renders fenced code blocks with a language label and copy-to-clipboard button.
 * Falls back to inline code styling for single-line snippets without a language class.
 */
function CodeBlock({ className, children, ...props }) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const lang  = match?.[1] || '';
  const code  = String(children).replace(/\n$/, '');

  const copy = useCallback(() => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  // inline code — no wrapper
  if (!className && !String(children).includes('\n')) {
    return <code className="inline-code" {...props}>{children}</code>;
  }

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-lang"><Code size={12} /> {lang || 'code'}</span>
        <button onClick={copy} className="code-copy-btn" title="Copy code">
          {copied ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
        </button>
      </div>
      <pre className={className}><code className={className} {...props}>{children}</code></pre>
    </div>
  );
}

/* ── Inline copy button for whole message ── */
/**
 * Copy-to-clipboard button for an entire AI message.
 * Appears on hover via the parent group class.
 * @param {{ text: string }} props
 */
function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs
                 text-[var(--color-text-secondary)] hover:text-[var(--color-text)]
                 hover:bg-[var(--color-hover)] transition-all
                 opacity-0 group-hover:opacity-100"
      title="Copy message"
    >
      {copied
        ? <><Check size={12} className="text-green-500" /> Copied</>
        : <><Copy size={12} /> Copy</>
      }
    </button>
  );
}

/* ── Thinking indicator ── */
/**
 * Animated thinking indicator shown while the AI is processing.
 * @param {{ status: string }} props - Current pipeline status message.
 */
export function ThinkingBubble({ status }) {
  return (
    <div className="flex gap-3 animate-fade-up">
      <div className="w-7 h-7 rounded-full bg-[var(--color-accent)] flex items-center justify-center shrink-0">
        <Bot size={14} className="text-white" />
      </div>
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
          <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-[var(--color-accent)]" />
          <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-[var(--color-accent)]" />
          <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-[var(--color-accent)]" />
          <span className="ml-1 text-xs font-medium">{status}</span>
        </div>
      </div>
    </div>
  );
}

/* ── markdown renderer config (stable refs) ── */
const mdPlugins   = [remarkGfm];
const rehyPlugins = [rehypeHighlight];
const mdComponents = { code: CodeBlock };

/* ── Message bubble ── */
/**
 * Renders a single chat message — user bubbles on the right, AI bubbles
 * on the left with markdown rendering, copy button, and follow-up chips.
 * @param {{ role: string, content: string, followUp?: string[], onFollowUp?: (q: string) => void }} props
 */
export default function MessageBubble({ role, content, followUp, onFollowUp }) {
  const isUser = role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end animate-fade-up">
        <div className="max-w-[75%] bg-[var(--color-user-bubble)] text-white
                        px-4 py-2.5 rounded-2xl rounded-br-sm
                        text-sm leading-relaxed whitespace-pre-wrap shadow-sm">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 animate-fade-up group">
      {/* avatar */}
      <div className="w-7 h-7 rounded-full bg-[var(--color-accent)] flex items-center justify-center shrink-0 mt-0.5">
        <Bot size={14} className="text-white" />
      </div>

      {/* body */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* markdown content */}
        <div className="ai-message-content prose prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={mdPlugins}
            rehypePlugins={rehyPlugins}
            components={mdComponents}
          >
            {content}
          </ReactMarkdown>
        </div>

        {/* actions */}
        <div className="flex items-center gap-1 -ml-1">
          <CopyBtn text={content} />
        </div>

        {/* follow-up chips */}
        {followUp?.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {followUp.map((q, i) => (
              <button
                key={i}
                onClick={() => onFollowUp?.(q)}
                disabled={!onFollowUp}
                className="text-xs px-3 py-1.5 rounded-full border border-[var(--color-border)]
                           text-[var(--color-text-secondary)] transition-all duration-200
                           enabled:hover:border-[var(--color-accent)] enabled:hover:bg-[var(--color-accent)]/5
                           enabled:hover:text-[var(--color-accent)]
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
