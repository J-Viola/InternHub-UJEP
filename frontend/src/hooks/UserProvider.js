import { createContext, useState, useContext, useEffect} from "react";
import User from "@utils/UserObj";

const UserContext = createContext();

function UserProvider({children}) {
    const [user, setUser] = useState(new User());

    useEffect(() => {
        console.log("UserProvider", user);
    }, [user]);

    return (
        <UserContext.Provider value={{user, setUser}}>
            {children}
        </UserContext.Provider>
    )
}

export function useUser() {
    // pro přečtení usera z contextu
    return useContext(UserContext);
}

export default UserProvider;