export default function EmptyState() {
  return (
    <div className="flex-1 h-full flex flex-col items-center justify-center gap-4 text-center px-8">
      {/* Decorative icon */}
      <div className="relative">
        <div className="w-20 h-20 rounded-3xl bg-hover border border-border flex items-center justify-center">
          <svg className="w-9 h-9 text-tx-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-accent flex items-center justify-center">
          <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
        </div>
      </div>

      <div>
        <p className="text-tx-1 font-semibold text-base">No chat open</p>
        <p className="text-tx-3 text-sm mt-1 max-w-xs">
          Pick a conversation on the left, or add a new friend to start chatting.
        </p>
      </div>
    </div>
  );
}
