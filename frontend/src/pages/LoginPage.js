import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
//import Headings from "@core/Text/Headings";
//import Button from "@core/Button/Button";
import LoginForm from "@login/LoginForm";
import { STAGLogin } from "@auth/STAGLogin";
import { useAuth } from "@auth/Auth";
import { useUser } from "@hooks/UserProvider";
import { useMessage } from "@hooks/MessageContext";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";


export default function LoginPage() {
    const { t } = useTranslation();
    const [ticket, setTicket] = useState(null);
    const [stagUserInfo, setStagUserInfo] = useState(null);
    const { login, isInitializing } = useAuth();
    const { user } = useUser();
    const { addMessage } = useMessage();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    // Přesměrování pokud je uživatel již přihlášen
    useEffect(() => {
        if (!isInitializing && user && user.isAuthenticated) {
            navigate("/nabidka");
        }
    }, [user, user.isAuthenticated, isInitializing, navigate]);

    // Zpracování parametrů z URL při načtení stránky
    useEffect(() => {
        const stagUserTicket = searchParams.get("stagUserTicket");
        const  stagUserInfoRaw = searchParams.get("stagUserInfo");

        if (stagUserTicket) {
            if (stagUserInfoRaw) {
                try {
                    const decoded = JSON.parse(atob(stagUserInfoRaw));
                    setStagUserInfo(decoded);
                } catch (e) {
                    console.warn("Error decoding stagUserInfo:", e);
                }
            }
            setTicket(stagUserTicket);
        }
    }, [searchParams]);

    // Zpracování STAG loginu při změně ticketu
    useEffect(() => {
        const handleSTAGLogin = async () => {
            if (!ticket) {
                return;
            }

            try {
                const payload = { service_ticket: ticket };
                if (stagUserInfo) payload.stag_user_info = stagUserInfo;
                await login(payload);

            } catch (error) {
                console.error("Error during STAG login:", error);
                if (error.response) {
                    addMessage(`${t('login.error_stag')}: ${error.response.data?.detail || error.message}`, "E");
                } else {
                    addMessage(`${t('login.error_stag')}: ${error.message}`, "E");
                }
            }
        };

        handleSTAGLogin();
    }, [ticket, login, addMessage, stagUserInfo, t]);

    const handleOrganizationLogin = async (loginData) => {
        try{
            const response = await login({email: loginData.email, password: loginData.password});

            // Po úspěšném loginu se přesměruje na /nabidka (handled in useAuth or useEffect above)
        } catch (error) {
            console.error("Error during organization login:", error);
            if (error.response) {
                addMessage(`${t('login.error_login')}: ${error.response.data?.detail || error.message}`, "E");
            } else {
                addMessage(`${t('login.error_login')}: ${error.message}`, "E");
            }
        }
    }

    // Hook - STAG komunikace
    const initiateSTAGLogin = async () => {
        try {
            await STAGLogin();
        } catch (error) {
            console.error("Error initiating STAG login:", error);
            addMessage(`${t('login.error_init_stag')}: ${error.message}`, "E");
        }
    }

    return (
        <Container property="flex items-center justify-center">
            <LoginForm handleSTAGLogin={initiateSTAGLogin} handleOrganizationLogin={handleOrganizationLogin}/>
        </Container>
    );
}
