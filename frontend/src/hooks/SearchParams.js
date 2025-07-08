import { useSearchParams } from "react-router-dom"


{/* HOOKY PRO QUERY, CURRENT URL A NÁSLEDNÉ PŘESMĚROVÁNÍ S PARAMS*/}
export function makeQuery(params) {
    const searchParams = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
            searchParams.set(key, value);
        }
    });
    
    return searchParams.toString() ? `?${searchParams.toString()}` : "";
}

export function useCurrentUrl() {
    return window.location.pathname;
}

export function useFullUrl() {
    return window.location.href;
}

export function useSetParams() {
    const [searchParams, setSearchParams] = useSearchParams();
    
    return (baseUrl, paramsQuery) => {
        const newParams = new URLSearchParams(paramsQuery);
        setSearchParams(newParams);
    };
}

export function useClearParams() {
    const [searchParams, setSearchParams] = useSearchParams();
    
    return (baseUrl) => {
        setSearchParams(new URLSearchParams());
    };
}

export function useStripParams() {
    return (url) => {
        const parts = url.split('?');
        if (parts.length > 1) {
            const queryString = decodeURIComponent(parts[1]);
            const params = {};
            
            const paramPairs = queryString.split('&');
            
            paramPairs.forEach(pair => {
                const [key, value] = pair.split('=');
                if (key && value !== undefined) {
                    const decodedValue = value.replace(/\+/g, ' ');
                    params[key] = decodedValue;
                }
            });
            
            return params;
        }
        return {};
    };
}