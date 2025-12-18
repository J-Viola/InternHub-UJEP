import React from 'react';
import Container from '@core/Container/Container';
import Nav from '@components/core/Nav';
import { Outlet } from 'react-router-dom';

export default function MainLayout() {
    return (
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Outlet />
            </Container>
        </Container>
    );
}
