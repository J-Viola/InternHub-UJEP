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
import ProfileForm from '@pages/ProfilFormPage';
import StudentPage from '@pages/StudentsPage';
import VytvorenePraxe from '@pages/VytvorenePraxePage';
import VytvoritNabidku from '@pages/VytvoritNabidku';

import reportWebVitals from './reportWebVitals';
import UserProvider from '@hooks/UserProvider';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <UserProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/nabidka" element={<NabidkaPage />} />
          <Route path="/nabidka/:id" element={<NabidkaDetailPage />} />
          <Route path="/profil" element={<ProfilPage />} />
          <Route path="/praxe" element={<PraxePage />} />
          <Route path="/TEST" element={<TextEditor />} />
          <Route path="/ProfileForm" element={<ProfileForm />} /> {/* DODĚLAT PARAMS NA USERA ZE SESSION*/}
          <Route path="/Students" element={<StudentPage />} />
          <Route path="/SprInPrihlaseni" element={<VytvorenePraxe />} />
          <Route path="/VytNabidku" element={<VytvoritNabidku />} />
        </Routes>
      </BrowserRouter>
    </UserProvider>
  </React.StrictMode>
);


reportWebVitals();
