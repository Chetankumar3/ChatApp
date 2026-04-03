import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { registerRecruiter } from '../api/auth.js';
import Spinner from '../components/Spinner.jsx';

export default function RecruiterRegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!username.trim() || !password.trim()) {
      setError('All fields are required');
      return;
    }

    setLoading(true);
    try {
      const data = await registerRecruiter(username.trim(), password, name.trim(), email.trim());
      await login(data.token, data.isNewUser);
      navigate('/chat');
    } catch (e) {
      setError(e.message || 'Registration failed. Please try again.');
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
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h1 className="text-tx-1 text-2xl font-bold tracking-tight">Recruiter Register</h1>
            <p className="text-tx-2 text-sm mt-1">Create a guest account valid for 2 hours</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-tx-2 text-sm mb-2">Name (Optional)</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 bg-base border border-border rounded-lg text-tx-1 placeholder-tx-3 focus:outline-none focus:ring-2 focus:ring-accent/50"
                placeholder="Your name"
              />
            </div>
            <div>
              <label className="block text-tx-2 text-sm mb-2">Email (Optional)</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 bg-base border border-border rounded-lg text-tx-1 placeholder-tx-3 focus:outline-none focus:ring-2 focus:ring-accent/50"
                placeholder="Your email"
              />
            </div>
            <div>
              <label className="block text-tx-2 text-sm mb-2">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 bg-base border border-border rounded-lg text-tx-1 placeholder-tx-3 focus:outline-none focus:ring-2 focus:ring-accent/50"
                placeholder="Choose a username"
                required
              />
            </div>
            <div>
              <label className="block text-tx-2 text-sm mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 bg-base border border-border rounded-lg text-tx-1 placeholder-tx-3 focus:outline-none focus:ring-2 focus:ring-accent/50"
                placeholder="Create a password"
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
                Register
              </button>
            )}
            {error && (
              <p className="text-red-400 text-xs text-center bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            <div className="text-center">
              <button
                type="button"
                onClick={() => navigate('/recruiter/login')}
                className="text-accent text-sm hover:underline"
              >
                Back to Recruiter Login
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
