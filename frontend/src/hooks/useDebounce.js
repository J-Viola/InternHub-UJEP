import { useState, useEffect } from 'react';

/**
 * Delays updating the returned value until `delay` ms have passed
 * without the input value changing.
 *
 * @param {*}      value  – the value to debounce
 * @param {number} delay  – debounce window in milliseconds (default 400)
 * @returns the debounced value
 */
export default function useDebounce(value, delay = 400) {
    const [debouncedValue, setDebouncedValue] = useState(value);

    useEffect(() => {
        const timer = setTimeout(() => setDebouncedValue(value), delay);
        return () => clearTimeout(timer);
    }, [value, delay]);

    return debouncedValue;
}
