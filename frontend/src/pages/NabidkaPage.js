import React, { useEffect, useState } from "react";
import Container from "@core/Container/Container";
import Nav from "@components/core/Nav";
import NabidkaEntity from "@components/Nabidka/NabidkaEntity";
import { useSearchParams } from "react-router-dom";
import FilterNabidka from "@components/Nabidka/FilterNabidka";
import { makeQuery, useCurrentUrl, useSetParams, useFullUrl, useClearParams, useStripParams } from "@hooks/SearchParams"
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI"

export default function NabidkaPage() {
    const currentUrl = useCurrentUrl();
    const setParams = useSetParams();
    const fullUrl = useFullUrl();
    const clearParams = useClearParams();
    const stripUrlParams = useStripParams();
    const [searchParams] = useSearchParams();
    const [filterValue, setFilterValue] = useState({ title: "" })

    const [data, setData] = useState(null);
    const nabidkaAPI = useNabidkaAPI();

    const initParamLoad = () => {
        console.log("full url", fullUrl);
        const urlParams = stripUrlParams(fullUrl);
        console.log("URL params", urlParams);
        
        if (urlParams && Object.keys(urlParams).length > 0) {
            console.log("Mám params data");
            setFilterValue(urlParams);
            console.log("FILTER DATA Z PARAMS", urlParams);
            fetchDataWithParams(urlParams);
        } else {
            setFilterValue({});
            fetchData();
        }
    }

    //fetch s parametry
    const fetchDataWithParams = async (params) => {
        try {
            console.log("Fetching with URL params:", params);
            const result = await nabidkaAPI.getNabidky(params);
            setData(result);
        } catch (error) {
            console.error("Chyba při načítání nabídek:", error);
        }
    };

    //fetch s aktuálními filtry
    const fetchData = async () => {
        try {
            console.log("Fetching with current filters:", filterValue);
            const result = await nabidkaAPI.getNabidky(filterValue);
            setData(result);
        } catch (error) {
            console.error("Chyba při načítání nabídek:", error);
        }
    };

    useEffect(() => {
        initParamLoad();
    }, []); 

    useEffect(() => {
        console.log("filter values", filterValue);
    }, [filterValue]);

    //DEBUG
    useEffect(() => {
        console.log(data);
    },[data])
        
    const handleFilterChange = (e) => {
        setFilterValue(prev => ({
            ...prev,
            [e.target.id]: e.target.value
        }));
    };

    const handleSearchClear = () => {
        setFilterValue(prev => ({
            ...prev,
            title: ""
        }));
    };

    const handleSearchSubmit = () => {
        const queryString = makeQuery(filterValue);
        console.log("QueryString", queryString);
        setParams(currentUrl, queryString);
        fetchData(); // api call
    };

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <FilterNabidka 
                    filterValue={filterValue}
                    handleFilterChange={handleFilterChange}
                    onSearchClear={handleSearchClear}
                    onSearchSubmit={handleSearchSubmit}
                />
                
                <Container property="grid grid-cols-1 gap-4 mt-2">
                    {data && data.map((entity, index) => (
                        <NabidkaEntity key={entity.practice_id || index} entity={entity}/>
                    ))}
                </Container>
            </Container>
        </Container>
    )
}