import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
//import Headings from "@core/Text/Headings";
//import Button from "@core/Button/Button";
import Nav from "@components/core/Nav";
import LoginForm from "@login/LoginForm";
import { STAGLogin, getParams } from "@utils/STAGLogin";

export default function LoginPage() {
    const [params, setParams] = useState({});

    // handle loginu - z komponenty LoginForm - hadnle API a vytvoření session
    const handleParams = () => {
        const params = getParams();
        console.log("Params:", params);
        params && setParams(params);
    }

    
    const handleSTAGLogin = () => {
        STAGLogin();
        handleParams();
    }

    useEffect(() => {
        handleParams();
    }, []);


    return (
        <>
        <Nav/>              
        <Container property="min-h-screen flex items-center justify-center bg-gray-100">
            <LoginForm handleSTAGLogin={handleSTAGLogin}/>
        </Container>
        </>
    );
}

