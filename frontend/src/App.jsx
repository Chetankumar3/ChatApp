import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext.jsx';
import { ChatProvider } from './context/ChatContext.jsx';
import LoginPage from './pages/LoginPage.jsx';
import ChatPage from './pages/ChatPage.jsx';
import ProfilePage from './pages/ProfilePage.jsx';
import SetUsernamePage from './pages/SetUsernamePage.jsx';
import RecruiterLoginPage from './pages/RecruiterLoginPage.jsx';
import RecruiterRegisterPage from './pages/RecruiterRegisterPage.jsx';
import ForgotPasswordPage from './pages/ForgotPasswordPage.jsx';

function ProtectedRoute({ children }) {
  const { userId, loading } = useAuth();
  if (loading) return (
    <div className="h-full flex items-center justify-center bg-base">
      <div className="w-6 h-6 rounded-full border-2 border-accent border-t-transparent animate-spin" />
    </div>
  );
  return userId ? children : <Navigate to="/" replace />;
}

function PublicRoute({ children }) {
  const { userId, loading } = useAuth();
  if (loading) return null;
  return userId ? <Navigate to="/chat" replace /> : children;
}

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<PublicRoute><LoginPage /></PublicRoute>} />
          <Route path="/recruiter/login" element={<PublicRoute><RecruiterLoginPage /></PublicRoute>} />
          <Route path="/recruiter/register" element={<PublicRoute><RecruiterRegisterPage /></PublicRoute>} />
          <Route path="/forgot-password" element={<PublicRoute><ForgotPasswordPage /></PublicRoute>} />
          <Route path="/set-username" element={
            <ProtectedRoute>
              <SetUsernamePage />
            </ProtectedRoute>
          } />
          <Route path="/chat" element={
            <ProtectedRoute>
              <ChatProvider>
                <ChatPage />
              </ChatProvider>
            </ProtectedRoute>
          } />
          <Route path="/profile" element={
            <ProtectedRoute>
              <ChatProvider>
                <ProfilePage />
              </ChatProvider>
            </ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
