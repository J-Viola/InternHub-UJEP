import { useAuth } from "@auth/Auth";
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";

const LogoutUser = () => {
    const { refreshToken, logout } = useAuth();
    const { addMessage } = useMessage();
    const navigate = useNavigate();
    const hasLoggedOut = useRef(false);

    useEffect(() => {
        const performLogout = async () => {
            if (hasLoggedOut.current) return; // Zabrání více spuštěním
            
            try {
                hasLoggedOut.current = true;
                await logout();
                addMessage("Úspěšně jste byli odhlášeni", "S");
            } catch (error) {
                console.error("Chyba při odhlášení:", error);
                //addMessage("Chyba při odhlášení: " + error.message, "E");
            } finally {
                navigate('/');
            }
        };

        performLogout();
    }, []); 

    return (
        <div className="flex justify-center items-center min-h-screen">
            <div className="text-lg">Odhlášení...</div>
        </div>
    );
};

export default LogoutUser;