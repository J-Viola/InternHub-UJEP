export const DUMMY_MODE = false

class User {
    constructor() {
        this.role = DUMMY_MODE ? "ST" :"";
        this.id = DUMMY_MODE ? "1" : "";
    }

    setUser(data) {
        this.role = data.role; // pro FE - DODĚLAT
        this.id = data.id
    }

    // dodělat checks na role, check T/F: má data?
}

export default User;