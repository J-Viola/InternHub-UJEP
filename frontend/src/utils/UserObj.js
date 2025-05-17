class User {
    constructor() {
        this.ticker = null;
        this.name = null;
        this.role = null;
        //........
    }

    setUser(user) {
        this.ticker = user.ticker;
        this.name = user.name;
        this.role = user.role;
        //........
    }

    // Dodělat constructor,getters a setters podle BE (je student, je na katedře....)

}

export default User;