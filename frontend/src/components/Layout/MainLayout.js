import React from 'react';
import Container from '@core/Container/Container';
import Nav from '@components/core/Nav';
import Footer from './Footer';
import { Outlet } from 'react-router-dom';

export default function MainLayout() {
    return (
        <Container property="min-h-screen flex flex-col bg-gray-100">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-grow w-full">
                <Outlet />
            </Container>
            <Footer />
        </Container>
    );
}
