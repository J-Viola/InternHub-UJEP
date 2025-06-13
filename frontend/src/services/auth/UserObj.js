class User {
    constructor() {
        this.role = null;
    }

    setUser(data) {
        this.role = data.role; // pro FE
    }

    // dodělat checks na role, check T/F: má data?
}

export default User;