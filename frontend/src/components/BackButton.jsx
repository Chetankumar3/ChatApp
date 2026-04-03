import { useNavigate } from 'react-router-dom';

export default function BackButton({ onClick, label = 'Back' }) {
  const navigate = useNavigate();
  const handleClick = onClick ?? (() => navigate(-1));

  return (
    <button
      onClick={handleClick}
      className="flex items-center gap-1.5 text-tx-2 hover:text-tx-1 transition-colors text-sm font-medium group"
    >
      <svg
        className="w-4 h-4 transition-transform group-hover:-translate-x-0.5"
        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
      </svg>
      {label}
    </button>
  );
}
