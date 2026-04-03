import { useState, useRef } from 'react';

export default function MessageInput({ onSend, disabled }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
    textareaRef.current?.focus();
    // Reset textarea height
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e) => {
    setText(e.target.value);
    // Auto-grow
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  return (
    <div className="px-4 py-3 border-t border-border shrink-0 bg-surface">
      <div className="flex items-end gap-2 bg-hover border border-border rounded-2xl px-3 py-2 focus-within:border-accent transition-colors">
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder="Type a message…"
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className="flex-1 bg-transparent resize-none text-sm text-tx-1 placeholder:text-tx-3 outline-none leading-relaxed min-h-[22px] disabled:opacity-50"
          style={{ height: 'auto' }}
        />
        <button
          onClick={handleSend}
          disabled={!text.trim() || disabled}
          className="w-8 h-8 flex items-center justify-center rounded-xl bg-accent hover:bg-accent-h disabled:opacity-30 disabled:cursor-not-allowed transition-all shrink-0 self-end"
        >
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5M5 12l7-7 7 7" />
          </svg>
        </button>
      </div>
      <p className="text-tx-3 text-[10px] mt-1 text-right">Enter to send · Shift+Enter for newline</p>
    </div>
  );
}
