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