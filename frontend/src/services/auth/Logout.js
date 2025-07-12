import { useAuth } from "@auth/Auth";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

const LogoutUser = () => {
    const { refreshToken, logout } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        const performLogout = async () => {
            try {
                await logout();
            } catch (error) {
                console.error("Chyba při odhlášení:", error);
                // I při chybě přesměrujeme na login
                navigate('/');
            }
        };

        performLogout();
    }, [logout, navigate]);

    return (
        <div className="flex justify-center items-center min-h-screen">
            <div className="text-lg">Odhlášení...</div>
        </div>
    );
};

export default LogoutUser;