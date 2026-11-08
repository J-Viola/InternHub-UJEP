import React, { useState, useEffect, useRef } from "react";
import Container from "@core/Container/Container";
import LoginForm from "@login/LoginForm";
import { getParams, STAGLogin } from "@auth/STAGLogin";
import { useAuth } from "@auth/Auth";
import { useUser } from "@hooks/UserProvider";
import { useMessage } from "@hooks/MessageContext";
import { useSearchParams, useNavigate } from "react-router-dom";


import getApiErrorMessage from "@utils/apiErrorUtils";
function cleanUrlFromStagParams() {
    const url = new URL(window.location.href);
    let changed = false;
    for (const param of ["stagUserTicket", "stagUserInfo", "state"]) {
        if (url.searchParams.has(param)) {
            url.searchParams.delete(param);
            changed = true;
        }
    }
    if (changed) {
        window.history.replaceState({}, "", url.toString());
    }
}


export default function LoginPage() {
    const [ticket, setTicket] = useState(null);
    const [stagUserInfo, setStagUserInfo] = useState(null);
    const { login, isInitializing } = useAuth();
    const { user } = useUser();
    const { addMessage } = useMessage();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const processedTicketRef = useRef(null);

    // Přesměrování pokud je uživatel již přihlášen
    useEffect(() => {
        if (!isInitializing && user && user.isAuthenticated) {
            navigate("/nabidka");
        }
    }, [user, user.isAuthenticated, isInitializing, navigate]);

    // Zpracování parametrů z URL při načtení stránky
    useEffect(() => {
        const params = getParams();

        if (params) {
            if (params.stag_user_info) {
                setStagUserInfo(params.stag_user_info);
            }
            if (params.service_ticket) {
                setTicket(params.service_ticket);
            }
            // Ticket nesmí zůstat v adrese (historie prohlížeče, logy) — čistíme hned po přečtení.
            cleanUrlFromStagParams();
        } else {
            // Po okamžitém vyčištění URL už router může držet starý searchParams;
            // rozhoduje aktuální adresa, jinak by se chyba „Invalid state“ přidala dvakrát.
            const stagUserTicket = new URLSearchParams(window.location.search).get("stagUserTicket");
            if (stagUserTicket) {
                addMessage("Chyba při STAG přihlášení" + ": Invalid state", "E");
                cleanUrlFromStagParams();
            }
        }
    }, [searchParams]);

    // Zpracování STAG loginu při změně ticketu (pouze jednou na ticket)
    useEffect(() => {
        const handleSTAGLogin = async () => {
            if (!ticket) {
                return;
            }

            // Ochrana proti double-fire v React StrictMode a opakovanému zpracování stejného ticketu
            if (processedTicketRef.current === ticket) {
                return;
            }
            processedTicketRef.current = ticket;

            try {
                const payload = { service_ticket: ticket };
                if (stagUserInfo) payload.stag_user_info = stagUserInfo;
                await login(payload);
            } catch (error) {
                console.error("Error during STAG login:", error?.response?.status || error?.code || "UNKNOWN_ERROR");
                addMessage(`Chyba při STAG přihlášení: ${getApiErrorMessage(error, error.message)}`, "E");
            }
        };

        handleSTAGLogin();
    }, [ticket, login, addMessage, stagUserInfo]);

    const handleOrganizationLogin = async (loginData) => {
        try{
            await login({email: loginData.email, password: loginData.password});

            // Po úspěšném loginu se přesměruje na /nabidka (handled in useAuth or useEffect above)
        } catch (error) {
            console.error("Error during organization login:", error?.response?.status || error?.code || "UNKNOWN_ERROR");
            addMessage(`Chyba při přihlášení: ${getApiErrorMessage(error, error.message)}`, "E");
        }
    }

    // Hook - STAG komunikace
    const initiateSTAGLogin = async () => {
        try {
            await STAGLogin();
        } catch (error) {
            console.error("Error initiating STAG login:", error);
            addMessage(`Chyba při iniciaci STAG přihlášení: ${error.message}`, "E");
        }
    }

    return (
        <Container property="flex items-center justify-center">
            <LoginForm handleSTAGLogin={initiateSTAGLogin} handleOrganizationLogin={handleOrganizationLogin}/>
        </Container>
    );
}
