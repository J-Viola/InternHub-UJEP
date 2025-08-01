export const DUMMY_MODE = false

class User {
    constructor() {
        this.role = DUMMY_MODE ? "ST" : "";
        this.id = DUMMY_MODE ? "1" : "";
        this.username = DUMMY_MODE ? "test_user" : "";
        this.email = DUMMY_MODE ? "test@example.com" : "";
        this.isAuthenticated = false;
    }

    setUser(data) {
        if (!data) {
            console.warn("setUser: No data provided");
            return;
        }
        
        this.role = data.role || "";
        this.id = data.id || data.user_id || "";
        this.username = data.username || "";
        this.email = data.email || "";
        this.isAuthenticated = true;
        
        // Store additional user data if provided
        if (data.first_name) this.firstName = data.first_name;
        if (data.last_name) this.lastName = data.last_name;
        if (data.department) this.department = data.department;
    }

    // Role checks
    hasRole(role) {
        return this.role === role;
    }

    isStudent() {
        return this.hasRole("ST");
    }

    isProfessor() {
        return this.hasRole("VY");
    }

    isDepartmentMg() {
        return this.hasRole("VK");
    }

    isEmployer() {
        return this.hasRole("EM");
    }

    isAdmin() {
        return this.hasRole("AD");
    }

    isOrganizationUser() {
        return this.hasRole("OWNER") || this.hasRole("INSERTER") 
    }

    isDepartmentUser() {
        return this.hasRole("VY") || this.hasRole("VK")
    }

    isOwner() {
        return this.hasRole("OWNER")
    }

    isInserter() {
        return this.hasRole("INSERTER")
    }

    // Check if user has any data
    hasData() {
        return this.isAuthenticated && this.id && this.role;
    }

    // Clear user data
    clear() {
        this.role = "";
        this.id = "";
        this.username = "";
        this.email = "";
        this.isAuthenticated = false;
        this.firstName = undefined;
        this.lastName = undefined;
        this.department = undefined;
    }

    // Get user display name
    getDisplayName() {
        if (this.firstName && this.lastName) {
            return `${this.firstName} ${this.lastName}`;
        }
        return this.username || "Unknown User";
    }
}

export default User;