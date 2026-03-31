/**
 * Utility functions for frontend validation.
 */

export const validateEmail = (email) => {
    if (!email) return false;
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
};

export const validateICO = (ico) => {
    if (!ico) return false;
    // Czech ICO is 8 digits
    const re = /^\d{8}$/;
    return re.test(String(ico));
};

export const validatePhone = (phone) => {
    if (!phone) return true; // Optional field
    // Basic phone validation (allowing +, spaces, and digits)
    const re = /^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$/;
    return re.test(String(phone));
};

export const validateRequired = (value) => {
    if (value === null || value === undefined) return false;
    if (typeof value === 'string') return value.trim().length > 0;
    if (Array.isArray(value)) return value.length > 0;
    return true;
};

export const validatePassword = (password) => {
    if (!password) return false;
    // At least 8 characters
    return password.length >= 8;
};
