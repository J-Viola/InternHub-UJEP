import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
//import Headings from "@core/Text/Headings";
//import Button from "@core/Button/Button";
import Nav from "@components/core/Nav";
import LoginForm from "@login/LoginForm";
import { STAGLogin, getParams } from "@auth/STAGLogin";
import { useAuth } from "@auth/Auth";
import { useMessage } from "@hooks/MessageContext";



export default function LoginPage() {
    const [ticket, setTicket] = useState(null);
    const { login } = useAuth();
    const { addMessage } = useMessage();
    // hook pro user data

    // Zpracování parametrů z URL při načtení stránky
    useEffect(() => {
        const params = getParams();
        console.log("Načtené URL parametry:", params);
        
        if (params?.service_ticket) {
            setTicket(params.service_ticket);
        }
    }, []); // Spustí se pouze při načtení stránky

    // Zpracování STAG loginu při změně ticketu
    useEffect(() => {
        const handleSTAGLogin = async () => {
            if (!ticket) {
                console.log("Žádný ticket k dispozici");
                return;
            }

            try {
                const response = await login({ service_ticket: ticket });
                
            } catch (error) {
                console.error("Chyba při STAG loginu:", error);
                if (error.response) {
                    console.error("API error response:", error.response.data);
                    addMessage("Chyba při STAG přihlášení: " + (error.response.data?.detail || error.message), "E");
                } else {
                    addMessage("Chyba při STAG přihlášení: " + error.message, "E");
                }
            }
        };

        handleSTAGLogin();
    }, [ticket, login, addMessage]);

    const handleOrganizationLogin = async (loginData) => {
        try{
            console.log("Organization login")
            const response = await login({email: loginData.email, password: loginData.password});
            
            // Po úspěšném loginu se přesměruje na /nabidka
            if (response?.status === 200) {
                console.log("Organization login successful, redirecting to /nabidka");
                //addMessage("Přihlášení úspěšné", "S");
            }

        } catch (error) {
            console.error("Chyba při loginu organizace:", error);
            if (error.response) {
                addMessage("Chyba při přihlášení: " + (error.response.data?.detail || error.message), "E");
            } else {
                addMessage("Chyba při přihlášení: " + error.message, "E");
            }
        }
    }

    // Hook - STAG komunikace
    const initiateSTAGLogin = async () => {
        try {
            console.log("Iniciuji STAG login...");
            await STAGLogin();
        } catch (error) {
            console.error("Chyba při iniciaci STAG loginu:", error);
            addMessage("Chyba při iniciaci STAG přihlášení: " + error.message, "E");
        }
    }

    return (
        <>
        <Nav/>              
        <Container property="min-h-screen flex items-center justify-center bg-gray-100">
            <LoginForm handleSTAGLogin={initiateSTAGLogin} handleOrganizationLogin={handleOrganizationLogin}/>
        </Container>
        </>
    );
}

