import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
//import Headings from "@core/Text/Headings";
//import Button from "@core/Button/Button";
import Nav from "@components/core/Nav";
import LoginForm from "@login/LoginForm";
import { STAGLogin, getParams } from "@auth/STAGLogin";
import { useAuth } from "@auth/Auth";

export default function LoginPage() {
    const [ticket, setTicket] = useState({});
    const {login} = useAuth();
    // hook pro user data

    // handle loginu - z komponenty LoginForm - hadnle API a vytvoření session
    const handleParams = () => {
        const params = getParams();
        console.log("Params:", params);
        ticket && setTicket(params);
    }

    
    const handleSTAGLogin = () => {
        STAGLogin();
        handleParams();
        if (ticket) {
            login({"service_ticket": ticket})
        }
        else {
            console.error("Nemáme stag ticket")
        }
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

