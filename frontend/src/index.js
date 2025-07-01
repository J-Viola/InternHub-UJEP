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
import ProfileEditPage from '@pages/ProfileEditPage'
import reportWebVitals from './reportWebVitals';
import UserProvider from '@hooks/UserProvider';
import AuthProvider from '@services/auth/Auth';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <UserProvider> {/* USE INFO PRO ŘÍZENÍ FE */}
      <AuthProvider> {/* TOKEN WORK */}
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LoginPage />} />
            <Route path="/nabidka" element={<NabidkaPage />} />
            <Route path="/nabidka/:id" element={<NabidkaDetailPage />} />
            <Route path="/profil/:id?" element={<ProfilPage />} />
            <Route path="/registrace" element={<RegistracePage />} />
            <Route path="/praxe" element={<PraxePage />} />
            <Route path="/TEST" element={<TextEditor />} />
            <Route path="/Students" element={<StudentPage />} />
            <Route path="/SprInPrihlaseni" element={<VytvorenePraxe />} />
            <Route path="/VytNabidku" element={<VytvoritNabidku />} />
            <Route path="/profil/edit/:id?" element={<ProfileEditPage />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </UserProvider>
  </React.StrictMode>
);


reportWebVitals();
