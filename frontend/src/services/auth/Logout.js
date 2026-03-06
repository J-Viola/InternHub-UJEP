import { useAuth } from "@auth/Auth";
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";
import { useTranslation } from "react-i18next";

const LogoutUser = () => {
    const { logout } = useAuth();
    const { addMessage } = useMessage();
    const navigate = useNavigate();
    const { t } = useTranslation();
    const hasLoggedOut = useRef(false);

    useEffect(() => {
        const performLogout = async () => {
            if (hasLoggedOut.current) return; // Zabrání více spuštěním

            try {
                hasLoggedOut.current = true;
                await logout();
                addMessage(t('common.logout_success'), "S");
            } catch (error) {
                console.error("Chyba při odhlášení:", error);
            } finally {
                navigate('/');
            }
        };

        performLogout();
    }, [logout, addMessage, navigate, t]);

    return (
        <div className="flex justify-center items-center min-h-screen">
            <div className="text-lg">{t('common.logging_out')}</div>
        </div>
    );
};

export default LogoutUser;
