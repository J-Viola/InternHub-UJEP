export const DUMMY_MODE = true

class User {
    constructor() {
        this.role = DUMMY_MODE ? "st" :"";
        this.id = DUMMY_MODE ? "1" : "";
    }

    setUser(data) {
        this.role = data.role; // pro FE - DODĚLAT
        this.id = data.id;
    }

    isVyucujici() {
        return this.role === "vy";
    }

    isStudent() {
        return this.role === "st";
    }
}

export default User;