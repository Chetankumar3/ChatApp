export default function Spinner({ size = 'md', className = '' }) {
  const sz = { sm: 'w-4 h-4 border', md: 'w-6 h-6 border-2', lg: 'w-10 h-10 border-2' }[size];
  return (
    <div className={`${sz} rounded-full border-accent border-t-transparent animate-spin ${className}`} />
  );
}
