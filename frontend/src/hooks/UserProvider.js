import { createContext, useState, useContext, useEffect} from "react";
import User from "@auth/UserObj";

const UserContext = createContext();

function UserProvider({children}) {
    const [user, setUserState] = useState(new User());

    const setUser = (data) => {
        try {
            const newUser = new User();
            newUser.setUser(data);
            setUserState(newUser);
            console.log("Data uživatele nastavena:", newUser);
        } catch(err) {
            console.error("Chyba při nastavování dat uživatele:", err);
            throw new Error(err.message);
        }
    }

    const cleanUser = () => {
        try {
            setUserState(new User());
        } catch(err) {
            console.error("Chyba při mazání dat uživatele")
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