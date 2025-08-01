import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import './index.css';
//import Test from './pages/TestPage';
import LoginPage from "@pages/LoginPage";
import NabidkaPage from '@pages/NabidkaPage';
import NabidkaDetailPage from '@pages/NabidkaDetailPage';
import ProfilPage from '@pages/ProfilPage';
import PraxePage from '@pages/PraxePage';
import StudentPage from '@pages/StudentsPage';
import VytvorenePraxe from '@pages/VytvorenePraxePage';
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
import AuthProvider from '@services/auth/Auth';
import { MessageProvider}  from '@hooks/MessageContext';
import InvitationPage from '@pages/InvitationPage';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <MessageProvider>
      <UserProvider> {/* USE INFO PRO ŘÍZENÍ FE */}
        <BrowserRouter>
          <AuthProvider> {/* TOKEN WORK */}
            <MessageToast/> {/* PRO ZOBRAZENÍ MESSAGE BOXU */}
            <Routes>
              <Route path="/" element={<LoginPage />} />
              <Route path="/nabidka" element={<NabidkaPage />} />
              <Route path="/nabidka/:id" element={<NabidkaDetailPage />} />
              <Route path="/subjects" element={<SubjectPage />} />
              <Route path="/profil/:id?" element={<ProfilPage />} />
              <Route path="/registrace" element={<RegistracePage />} />
              <Route path="/praxe" element={<PraxePage />} />
              <Route path="/karta-praxe/:id" element={<PraxeDetailPage />} />
              <Route path="/students/:id?" element={<StudentPage />} />
              <Route path="/SprInPrihlaseni" element={<VytvorenePraxe />} />
              <Route path="/vytvorit-nabidku" element={<VytvoritNabidku />} />
              <Route path="/upravit-nabidku/:id" element={<UpravitNabidku />} />
              <Route path="/logout" element={<LogoutUser />} />
              <Route path="/users/:type" element={<UserCRUDPage/>} />
              <Route path="/prihlasky" element={<PrihlaskyPage/>} />
              <Route path="/sprava-stazi" element={<SpravaStaziPage/>} />
              <Route path="/formular" element={<FormPage/>} />
              <Route path="/pozvanka" element={<InvitationPage/>} />

            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </UserProvider>
    </MessageProvider>
  </React.StrictMode>
);


reportWebVitals();
