import { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext.jsx';
import { loginWithGoogle } from '../api/auth.js';
import Spinner from '../components/Spinner.jsx';

export default function LoginPage() {
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const handleSuccess = async (credentialResponse) => {
    setLoading(true);
    setError('');
    try {
      const data = await loginWithGoogle(credentialResponse.credential);
      await login(data.userId);
    } catch (e) {
      setError(e.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex items-center justify-center bg-base relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-accent/5 blur-3xl" />
        <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-indigo-800/10 blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-sm px-4">
        <div className="bg-surface border border-border rounded-3xl p-8 shadow-2xl animate-slide-up">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-14 h-14 rounded-2xl bg-accent/10 border border-accent/30 flex items-center justify-center mb-4">
              <svg className="w-7 h-7 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h1 className="text-tx-1 text-2xl font-bold tracking-tight">Ping</h1>
            <p className="text-tx-2 text-sm mt-1">Fast. Direct. Simple.</p>
          </div>

          <div className="space-y-4">
            <p className="text-tx-3 text-xs text-center uppercase tracking-wider">Sign in to continue</p>

            {loading ? (
              <div className="flex justify-center py-4">
                <Spinner />
              </div>
            ) : (
              <div className="flex justify-center google-btn-wrapper">
                <GoogleLogin
                  onSuccess={handleSuccess}
                  onError={() => setError('Google sign-in failed.')}
                  theme="filled_black"
                  shape="rectangular"
                  size="large"
                  text="signin_with"
                  width="280"
                />
              </div>
            )}

            {error && (
              <p className="text-red-400 text-xs text-center bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
          </div>

          <p className="text-tx-3 text-[10px] text-center mt-6 leading-relaxed">
            By signing in you agree to our terms of service and privacy policy.
          </p>
        </div>
      </div>
    </div>
  );
}
