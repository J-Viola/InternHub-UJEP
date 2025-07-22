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
import TextEditor from '@pages/TEST_TextEditor';
import StudentPage from '@pages/StudentsPage';
import VytvorenePraxe from '@pages/VytvorenePraxePage';
import VytvoritNabidku from '@pages/VytvoritNabidku';
import RegistracePage from '@pages/RegistracePage';
import LogoutUser from '@services/auth/Logout';
import MessageToast from '@components/MessageBox/MessageToast';
import UserCRUDPage from '@pages/UserCRUDPage';
import PrihlaskyPage from '@pages/PrihlaskyPage';
import SpravaStaziPage from '@pages/SpravaStaziPage';


import reportWebVitals from './reportWebVitals';
import UserProvider from '@hooks/UserProvider';
import AuthProvider from '@services/auth/Auth';
import { MessageProvider}  from '@hooks/MessageContext';

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
              <Route path="/profil" element={<ProfilPage />} />
              <Route path="/registrace" element={<RegistracePage />} />
              <Route path="/praxe" element={<PraxePage />} />
              <Route path="/TEST" element={<TextEditor />} />
              <Route path="/students" element={<StudentPage />} />
              <Route path="/SprInPrihlaseni" element={<VytvorenePraxe />} />
              <Route path="/vytvorit-nabidku" element={<VytvoritNabidku />} />
              <Route path="/logout" element={<LogoutUser />} />
              <Route path="/users/:type" element={<UserCRUDPage/>} />
              <Route path="/prihlasky" element={<PrihlaskyPage/>} />
              <Route path="/sprava-stazi" element={<SpravaStaziPage/>} />
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </UserProvider>
    </MessageProvider>
  </React.StrictMode>
);


reportWebVitals();
