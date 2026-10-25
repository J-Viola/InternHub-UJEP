import { createContext, useState, useContext, useEffect} from "react";
import User from "@auth/UserObj";

const UserContext = createContext();

function UserProvider({children}) {
    // Initialize user from localStorage if available
    const [user, setUserState] = useState(() => {
        const storedUser = localStorage.getItem("user");
        if (storedUser) {
            try {
                const userData = JSON.parse(storedUser);
                const newUser = new User();
                newUser.setUser(userData);
                return newUser;
            } catch (error) {
                if (process.env.NODE_ENV === "development") console.error("Chyba při parsování dat uživatele z localStorage");
                localStorage.removeItem("user");
            }
        }
        return new User();
    });

    const setUser = (data) => {
        try {
            const newUser = new User();
            newUser.setUser(data);
            setUserState(newUser);
            localStorage.setItem("user", JSON.stringify(data));

            if (process.env.NODE_ENV === "development") console.log("Data uživatele nastavena a uložena do localStorage");
        } catch(err) {
            if (process.env.NODE_ENV === "development") console.error("Chyba při nastavování dat uživatele");
            throw new Error(err.message);
        }
    }

    const cleanUser = () => {
        try {
            setUserState(new User());
            localStorage.removeItem("user");
            if (process.env.NODE_ENV === "development") console.log("Data uživatele vyčištěna z localStorage");
        } catch(err) {
            if (process.env.NODE_ENV === "development") console.error("Chyba při mazání dat uživatele");
        }
    }

    useEffect(() => {
        if (process.env.NODE_ENV === "development") console.log("UserProvider state updated");
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
