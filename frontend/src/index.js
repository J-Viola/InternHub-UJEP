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
import VytvoritExterniPraxi from '@pages/VytvoritExterniPraxi';
import EvaluationForm from '@pages/EvaluationForm';
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
import { NotificationProvider } from '@hooks/NotificationProvider';
import InvitationPage from '@pages/PozvankyPage';
import PozvankyListPage from '@pages/PozvankyListPage';
import StudentApplicationsPage from '@pages/StudentApplicationsPage';
import NotificationsPage from '@pages/NotificationsPage';
import DepartmentsPage from '@pages/DepartmentsPage';
import CompaniesPage from '@pages/CompaniesPage';
import ChangePasswordPage from '@pages/ChangePasswordPage';
import PasswordResetRequestPage from '@pages/PasswordResetRequestPage';
import PasswordResetConfirmPage from '@pages/PasswordResetConfirmPage';
import NotFoundPage from '@pages/NotFoundPage';
import ForbiddenPage from '@pages/ForbiddenPage';
import MainLayout from '@components/Layout/MainLayout';
import ProtectedRoute from '@components/ProtectedRoute';
import { withErrorBoundary } from '@components/ErrorBoundary';
import { useTranslation } from 'react-i18next';
import * as Sentry from "@sentry/react";

// Sentry error monitoring — only initializes when REACT_APP_SENTRY_DSN is set
if (process.env.REACT_APP_SENTRY_DSN) {
    Sentry.init({
        dsn: process.env.REACT_APP_SENTRY_DSN,
        environment: process.env.NODE_ENV || "development",
    });
}

// Global error handlers — catches errors outside React tree
window.addEventListener('error', (event) => {
  console.error('Nezachycená chyba:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Nezachycené odmítnutí promise:', event.reason);
});

// Wrap every page component with its own ErrorBoundary so a crash
// on one route does not take down the entire SPA.
const w = withErrorBoundary;
const LoginPageW          = w(LoginPage);
const NabidkaPageW        = w(NabidkaPage);
const NabidkaDetailPageW  = w(NabidkaDetailPage);
const ProfilPageW         = w(ProfilPage);
const PraxePageW          = w(PraxePage);
const StudentPageW        = w(StudentPage);
const VytvoritNabidkuW    = w(VytvoritNabidku);
const VytvoritExterniPraxiW = w(VytvoritExterniPraxi);
const EvaluationFormW     = w(EvaluationForm);
const UpravitNabidkuW     = w(UpravitNabidku);
const RegistracePageW     = w(RegistracePage);
const UserCRUDPageW       = w(UserCRUDPage);
const PrihlaskyPageW      = w(PrihlaskyPage);
const SpravaStaziPageW    = w(SpravaStaziPage);
const PraxeDetailPageW    = w(PraxeDetailPage);
const SubjectPageW        = w(SubjectPage);
const FormPageW           = w(FormPage);
const InvitationPageW     = w(InvitationPage);
const PozvankyListPageW   = w(PozvankyListPage);
const StudentApplicationsPageW = w(StudentApplicationsPage);
const NotificationsPageW       = w(NotificationsPage);
const DepartmentsPageW    = w(DepartmentsPage);
const CompaniesPageW      = w(CompaniesPage);
const ChangePasswordPageW = w(ChangePasswordPage);
const PasswordResetRequestPageW = w(PasswordResetRequestPage);
const PasswordResetConfirmPageW = w(PasswordResetConfirmPage);
const NotFoundPageW       = w(NotFoundPage);
const ForbiddenPageW      = w(ForbiddenPage);

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
        <Route path="/" element={<LoginPageW />} />
        <Route path="/registrace" element={<RegistracePageW />} />
        <Route path="/reset-password" element={<PasswordResetRequestPageW />} />
        <Route path="/reset-password/:uid/:token" element={<PasswordResetConfirmPageW />} />

        {/* Protected routes — require a valid access token */}
        <Route path="/nabidka" element={<ProtectedRoute><NabidkaPageW /></ProtectedRoute>} />
        <Route path="/nabidka/:id" element={<ProtectedRoute><NabidkaDetailPageW /></ProtectedRoute>} />
        <Route path="/subjects" element={<ProtectedRoute allowedRoles={['VY', 'VK', 'admin']}><SubjectPageW /></ProtectedRoute>} />
        <Route path="/profil/:id?" element={<ProtectedRoute><ProfilPageW /></ProtectedRoute>} />
        <Route path="/change-password" element={<ProtectedRoute><ChangePasswordPageW /></ProtectedRoute>} />
        <Route path="/praxe" element={<ProtectedRoute allowedRoles={['ST', 'OWNER', 'INSERTER', 'admin']}><PraxePageW /></ProtectedRoute>} />
        <Route path="/karta-praxe/:id" element={<ProtectedRoute allowedRoles={['ST', 'VY', 'VK', 'OWNER', 'INSERTER', 'admin']}><PraxeDetailPageW /></ProtectedRoute>} />
        <Route path="/students/:id?" element={<ProtectedRoute allowedRoles={['VY', 'VK', 'OWNER', 'INSERTER', 'admin']}><StudentPageW /></ProtectedRoute>} />
        <Route path="/vytvorit-nabidku" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'admin']}><VytvoritNabidkuW /></ProtectedRoute>} />
        <Route path="/vytvorit-externi-praxi" element={<ProtectedRoute allowedRoles={['ST', 'VY', 'VK', 'admin']}><VytvoritExterniPraxiW /></ProtectedRoute>} />
        <Route path="/upravit-nabidku/:id" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'admin']}><UpravitNabidkuW /></ProtectedRoute>} />
        <Route path="/logout" element={<ProtectedRoute><LogoutUser /></ProtectedRoute>} />
        <Route path="/users/:type" element={<ProtectedRoute allowedRoles={['VK', 'OWNER', 'INSERTER', 'admin']}><UserCRUDPageW /></ProtectedRoute>} />
        <Route path="/prihlasky" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'admin']}><PrihlaskyPageW /></ProtectedRoute>} />
        <Route path="/sprava-stazi" element={<ProtectedRoute allowedRoles={['VY', 'VK', 'admin']}><SpravaStaziPageW /></ProtectedRoute>} />
        <Route path="/evaluace/:id" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'VY', 'VK', 'admin']}><EvaluationFormW /></ProtectedRoute>} />
        <Route path="/formular" element={<ProtectedRoute><FormPageW /></ProtectedRoute>} />
        <Route path="/pozvanka" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'admin']}><InvitationPageW /></ProtectedRoute>} />
        <Route path="/pozvanky-list" element={<ProtectedRoute allowedRoles={['OWNER', 'INSERTER', 'admin']}><PozvankyListPageW /></ProtectedRoute>} />
        <Route path="/moje-prihlasky" element={<ProtectedRoute allowedRoles={['ST']}><StudentApplicationsPageW /></ProtectedRoute>} />
        <Route path="/notifikace" element={<ProtectedRoute><NotificationsPageW /></ProtectedRoute>} />
        <Route path="/departments" element={<ProtectedRoute allowedRoles={['admin']}><DepartmentsPageW /></ProtectedRoute>} />
        <Route path="/companies" element={<ProtectedRoute allowedRoles={['admin']}><CompaniesPageW /></ProtectedRoute>} />
        <Route path="/forbidden" element={<ForbiddenPageW />} />
        <Route path="*" element={<NotFoundPageW />} />
      </Route>
    </Routes>
  );
};

function ErrorFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="text-center p-8">
        <h1 className="text-2xl font-bold text-red-600 mb-4">Nastala chyba</h1>
        <p className="text-gray-600 mb-4">Došlo k neočekávané chybě. Zkuste prosím obnovit stránku.</p>
        <button
          className="px-4 py-2 bg-blue-500 text-white rounded-lg"
          onClick={() => window.location.reload()}
        >
          Obnovit stránku
        </button>
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <MessageProvider>
      <UserProvider>
        <BrowserRouter>
          <AuthProvider>
            <NotificationProvider>
              <MessageToast />
              <Sentry.ErrorBoundary fallback={<ErrorFallback />} showDialog>
                <AppRoutes />
              </Sentry.ErrorBoundary>
            </NotificationProvider>
          </AuthProvider>
        </BrowserRouter>
      </UserProvider>
    </MessageProvider>
  </React.StrictMode>
);


reportWebVitals();
