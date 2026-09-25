import { Navigate, Route, Routes } from 'react-router-dom';
import { AnalyzePage } from './components/app/AnalyzePage';
import { AppShell, RequireAuth } from './components/app/AppShell';
import { HistoryPage } from './components/app/HistoryPage';
import { ReportPage } from './components/app/ReportPage';
import { RepositoriesPage } from './components/app/RepositoriesPage';
import { SettingsPage } from './components/app/SettingsPage';
import { AuthPage } from './components/auth/AuthPage';
import { LandingPage } from './components/landing/LandingPage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/signin" element={<AuthPage mode="signin" />} />
      <Route path="/signup" element={<AuthPage mode="signup" />} />
      <Route path="/app" element={<RequireAuth><AppShell /></RequireAuth>}>
        <Route index element={<Navigate to="repositories" replace />} />
        <Route path="repositories" element={<RepositoriesPage />} />
        <Route path="analyze" element={<AnalyzePage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="reports/:id" element={<ReportPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
