import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import './i18n';
import './index.css';
import LoginPage from "@pages/LoginPage";
import NabidkaPage from '@pages/NabidkaPage';
import NabidkaDetailPage from '@pages/NabidkaDetailPage';
import ProfilPage from '@pages/ProfilPage';
import PraxePage from '@pages/PraxePage';
import StudentPage from '@pages/StudentsPage';
import VytvoritNabidku from '@pages/VytvoritNabidku';
import UpravitNabidku from '@pages/UpravitNabidku';
import RegistracePage from '@pages/RegistracePage';
import LogoutUser from '@services/auth/Logout';
import MessageToast from '@components/MessageBox/MessageToast';
import UserCRUDPage from '@pages/UserCRUDPage';
import PrihlaskyPage from '@pages/PrihlaskyPage';
import SpravaStaziPage from '@pages/SpravaStaziPage';
import PraxeDetailPage from '@pages/PraxeDetailPage';
import SubjectPage from '@pages/SubjectPage';
import FormPage from '@pages/FormPage';
import reportWebVitals from './reportWebVitals';
import UserProvider from '@hooks/UserProvider';
import AuthProvider, { useAuth } from '@services/auth/Auth';
import { MessageProvider } from '@hooks/MessageContext';
import InvitationPage from '@pages/PozvankyPage';
import PozvankyListPage from '@pages/PozvankyListPage';
import DepartmentsPage from '@pages/DepartmentsPage';
import CompaniesPage from '@pages/CompaniesPage';
import ChangePasswordPage from '@pages/ChangePasswordPage';
import PasswordResetRequestPage from '@pages/PasswordResetRequestPage';
import PasswordResetConfirmPage from '@pages/PasswordResetConfirmPage';
import MainLayout from '@components/Layout/MainLayout';
import StudentApplicationsPage from '@pages/StudentApplicationsPage';
import ProtectedRoute from '@components/ProtectedRoute';
import ErrorBoundary from '@components/ErrorBoundary';
import { useTranslation } from 'react-i18next';

const AppRoutes = () => {
  const { isInitializing } = useAuth();
  const { t } = useTranslation();

  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-xl text-gray-600">{t('common.loading_app')}</div>
      </div>
    );
  }

  return (
    <Routes>
      <Route element={<MainLayout />}>
        {/* Public routes — accessible without authentication */}
        <Route path="/" element={<LoginPage />} />
        <Route path="/registrace" element={<RegistracePage />} />
        <Route path="/reset-password" element={<PasswordResetRequestPage />} />
        <Route path="/reset-password/:uid/:token" element={<PasswordResetConfirmPage />} />

        {/* Protected routes — require a valid access token */}
        <Route path="/nabidka" element={<ProtectedRoute><NabidkaPage /></ProtectedRoute>} />
        <Route path="/nabidka/:id" element={<ProtectedRoute><NabidkaDetailPage /></ProtectedRoute>} />
        <Route path="/subjects" element={<ProtectedRoute allowedRoles={['VY', 'VK', 'admin']}><SubjectPage /></ProtectedRoute>} />
        <Route path="/profil/:id?" element={<ProtectedRoute><ProfilPage /></ProtectedRoute>} />
        <Route path="/change-password" element={<ProtectedRoute><ChangePasswordPage /></ProtectedRoute>} />
        <Route path="/praxe" element={<ProtectedRoute allowedRoles={['ST', 'OWNER', 'INSERTER', 'admin']}><PraxePage /></ProtectedRoute>} />
        <Route path="/karta-praxe/:id" element={<ProtectedRoute allowedRoles={['ST', 'VY', 'VK', 'OWNER', 'INSERTER', 'admin']}><PraxeDetailPage /></ProtectedRoute>} />
        <Route path="/students/:id?" element={<ProtectedRoute allowedRoles={['VY', 'VK', 'OWNER', 'INSERTER', 'admin']}><StudentPage /></ProtectedRoute>} />
        <Route path="/vytvorit-nabidku" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'admin']}><VytvoritNabidku /></ProtectedRoute>} />
        <Route path="/upravit-nabidku/:id" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'admin']}><UpravitNabidku /></ProtectedRoute>} />
        <Route path="/logout" element={<ProtectedRoute><LogoutUser /></ProtectedRoute>} />
        <Route path="/users/:type" element={<ProtectedRoute allowedRoles={['VK', 'OWNER', 'INSERTER', 'admin']}><UserCRUDPage /></ProtectedRoute>} />
        <Route path="/prihlasky" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'admin']}><PrihlaskyPage /></ProtectedRoute>} />
        <Route path="/sprava-stazi" element={<ProtectedRoute allowedRoles={['VY', 'VK', 'admin']}><SpravaStaziPage /></ProtectedRoute>} />
        <Route path="/formular" element={<ProtectedRoute><FormPage /></ProtectedRoute>} />
        <Route path="/pozvanka" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'admin']}><InvitationPage /></ProtectedRoute>} />
        <Route path="/pozvanky-list" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'admin']}><PozvankyListPage /></ProtectedRoute>} />
        <Route path="/departments" element={<ProtectedRoute allowedRoles={['admin']}><DepartmentsPage /></ProtectedRoute>} />
        <Route path="/companies" element={<ProtectedRoute allowedRoles={['admin']}><CompaniesPage /></ProtectedRoute>} />
        <Route path="/moje-prihlasky" element={<ProtectedRoute allowedRoles={['ST']}><StudentApplicationsPage /></ProtectedRoute>} />
      </Route>
    </Routes>
  );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <MessageProvider>
        <UserProvider>
          <BrowserRouter>
            <AuthProvider>
              <ErrorBoundary>
                <MessageToast />
                <AppRoutes />
              </ErrorBoundary>
            </AuthProvider>
          </BrowserRouter>
        </UserProvider>
      </MessageProvider>
    </ErrorBoundary>
  </React.StrictMode>
);


reportWebVitals();
