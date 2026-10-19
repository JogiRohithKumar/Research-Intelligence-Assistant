import { useState } from 'react';
import { loginUser, registerUser } from '../../services/api';

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let res;
      if (isRegister) {
        if (!email.trim()) {
          throw new Error("Email is required for registration");
        }
        res = await registerUser(username, email, password);
      } else {
        res = await loginUser(username, password);
      }
      if (onAuthSuccess) {
        onAuthSuccess(res.user);
      }
      onClose();
    } catch (err) {
      const msg = err.response?.data?.error?.message || err.response?.data?.detail || err.message || "Authentication failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-[#0f172a] border border-slate-700 rounded-xl shadow-2xl p-6 sm:p-8 space-y-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h2 id="auth-modal-title" className="text-xl font-semibold text-slate-100 tracking-tight">
              {isRegister ? "Create Research Account" : "Researcher Sign In"}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {isRegister
                ? "Register for persistent research sessions and multi-tenant isolation"
                : "Sign in with your verified scholarly credentials"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            aria-label="Close dialog"
          >
            ✕
          </button>
        </div>

        {error && (
          <div role="alert" className="p-3 bg-red-950/50 border border-red-800/80 rounded-lg text-xs text-red-200">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1" htmlFor="auth-username">
              Username {isRegister ? "" : "or Email"}
            </label>
            <input
              id="auth-username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder={isRegister ? "dr_feynman" : "username or email"}
            />
          </div>

          {isRegister && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1" htmlFor="auth-email">
                Institutional / Professional Email
              </label>
              <input
                id="auth-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="researcher@institute.edu"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1" htmlFor="auth-password">
              Password
            </label>
            <input
              id="auth-password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900/60 text-white font-medium text-sm rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            {loading ? "Authenticating..." : (isRegister ? "Register Account" : "Sign In")}
          </button>
        </form>

        <div className="text-center pt-2 border-t border-slate-800">
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError(null);
            }}
            className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors focus:outline-none focus:underline"
          >
            {isRegister
              ? "Already have an account? Sign in here"
              : "Don't have an account? Register here"}
          </button>
        </div>
      </div>
    </div>
  );
}
