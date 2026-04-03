import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Spinner from '../components/Spinner.jsx';

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Email is required');
      return;
    }
    setLoading(true);
    setError('');
    setMessage('');
    try {
      // TODO: Implement forgot password API
      // await forgotPassword(email.trim());
      setMessage('Password reset link sent to your email (feature not implemented yet)');
    } catch (e) {
      setError(e.message || 'Failed to send reset email');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex items-center justify-center bg-base relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-accent/5 blur-3xl" />
        <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-indigo-800/10 blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-sm px-4">
        <div className="bg-surface border border-border rounded-3xl p-8 shadow-2xl animate-slide-up">
          <div className="flex flex-col items-center mb-8">
            <div className="w-14 h-14 rounded-2xl bg-accent/10 border border-accent/30 flex items-center justify-center mb-4">
              <svg className="w-7 h-7 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
            </div>
            <h1 className="text-tx-1 text-2xl font-bold tracking-tight">Forgot Password</h1>
            <p className="text-tx-2 text-sm mt-1">Enter your email to reset password</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-tx-2 text-sm mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 bg-base border border-border rounded-lg text-tx-1 placeholder-tx-3 focus:outline-none focus:ring-2 focus:ring-accent/50"
                placeholder="Enter your email"
                required
              />
            </div>

            {loading ? (
              <div className="flex justify-center py-4">
                <Spinner />
              </div>
            ) : (
              <button
                type="submit"
                className="w-full bg-accent hover:bg-accent/90 text-white font-medium py-2 px-4 rounded-lg transition-colors"
              >
                Send Reset Link
              </button>
            )}

            <div className="text-center">
              <button
                onClick={() => navigate('/recruiter/login')}
                className="text-accent text-sm hover:underline"
              >
                Back to Login
              </button>
            </div>

            {message && (
              <p className="text-green-400 text-xs text-center bg-green-400/10 border border-green-400/20 rounded-lg px-3 py-2">
                {message}
              </p>
            )}

            {error && (
              <p className="text-red-400 text-xs text-center bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}