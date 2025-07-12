import { createContext, useState, useContext, useEffect} from "react";
import User from "@auth/UserObj";

const UserContext = createContext();

function UserProvider({children}) {
    // Initialize user from localStorage if available
    const [user, setUserState] = useState(() => {
        const storedUser = localStorage.getItem("user");
        if (storedUser) {
            console.log("Načítám uživatele z localStorage:", storedUser);
            try {
                const userData = JSON.parse(storedUser);
                const newUser = new User();
                newUser.setUser(userData);
                console.log("Uživatel úspěšně načten:", newUser);
                return newUser;
            } catch (error) {
                console.error("Chyba při parsování dat uživatele z localStorage:", error);
                localStorage.removeItem("user"); // Odstraníme poškozená data
                return new User();
            }
        }
        console.log("Žádný uživatel v localStorage");
        return new User();
    });

    const setUser = (data) => {
        try {
            const newUser = new User();
            newUser.setUser(data);
            setUserState(newUser);
            localStorage.setItem("user", JSON.stringify(data));
            
            console.log("Data uživatele nastavena a uložena do localStorage:", newUser);
        } catch(err) {
            console.error("Chyba při nastavování dat uživatele:", err);
            throw new Error(err.message);
        }
    }

    const cleanUser = () => {
        try {
            setUserState(new User());
            localStorage.removeItem("user");
            console.log("Data uživatele vyčištěna z localStorage");
        } catch(err) {
            console.error("Chyba při mazání dat uživatele:", err);
        }
    }

    useEffect(() => {
        console.log("UserProvider state:", user);
    }, [user]);

    return (
        <UserContext.Provider value={{user, setUser, cleanUser}}>
            {children}
        </UserContext.Provider>
    )
}

export function useUser() {
    const context = useContext(UserContext);
    return context;
}

export default UserProvider;