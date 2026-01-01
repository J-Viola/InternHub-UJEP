import React, { useEffect, useState } from "react";
import Container from "@core/Container/Container";
import Nav from "@components/core/Nav";
import NabidkaEntity from "@components/Nabidka/NabidkaEntity";
import { useSearchParams } from "react-router-dom";
import FilterNabidka from "@components/Nabidka/FilterNabidka";
import { makeQuery, useCurrentUrl, useSetParams, useFullUrl, useClearParams, useStripParams } from "@hooks/SearchParams"
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI"
import { useCodeListAPI } from "@api/code_list/code_listAPI";
import { useMessage } from "@hooks/MessageContext";



export default function NabidkaPage() {
    const currentUrl = useCurrentUrl();
    const setParams = useSetParams();
    const fullUrl = useFullUrl();
    const clearParams = useClearParams();
    const stripUrlParams = useStripParams();
    const [ searchParams ] = useSearchParams();
    const [ filterValue, setFilterValue ] = useState({ title: "" });
    const [ filterOptions, setFilterOptions ] = useState({});
    const [data, setData] = useState(null);
    const nabidkaAPI = useNabidkaAPI();
    const codelist = useCodeListAPI();
    const { addMessage } = useMessage();

    const [ uniqueLocations, setLocations ] = useState([])
    const [ uniqueSubjects, setSubjects ] = useState([])

    const initParamLoad = () => {
        const urlParams = stripUrlParams(fullUrl);
        
        if (urlParams && Object.keys(urlParams).length > 0) {
            setFilterValue(urlParams);
            fetchDataWithParams(urlParams);
        } else {
            setFilterValue({});
            fetchData();
        }
    }

    const initFilterOptions = async() =>{
        try {
            const locations = await codelist.getUniqueLocations();
            setLocations(locations);

            const subjects = await codelist.getUniqueSubjects();
            setSubjects(subjects);
        } catch (error) {
            console.error("Error initializing filter options:", error);
        }
    }

    //fetch s parametry
    const fetchDataWithParams = async (params) => {
        try {
            const result = await nabidkaAPI.getNabidky(params);
            setData(result);
        } catch (error) {
            console.error("Chyba při načítání nabídek:", error);
        }
    };

    //fetch s aktuálními filtry
    const fetchData = async () => {
        try {
            const result = await nabidkaAPI.getNabidky(filterValue);
            setData(result);
        } catch (error) {
            console.error("Chyba při načítání nabídek:", error);
        }
    };

    useEffect(() => {
        initParamLoad();
        initFilterOptions();

        const pending = sessionStorage.getItem("pendingMessage");
        if (pending) {
            const { text, type } = JSON.parse(pending);
            addMessage(text, type);
            sessionStorage.removeItem("pendingMessage");
        }
    }, []);

    const handleFilterChange = (e, id, value, directValue = false) => {
        setFilterValue(prev => {
            const newValue = directValue ? value : e.target.value;
            const key = directValue ? id : e.target.id;
            const updatedFilter = { ...prev };
            
            if (newValue === "" || newValue === null || newValue === undefined) {
                delete updatedFilter[key];
            } else {
                updatedFilter[key] = newValue;
            }
            return updatedFilter;
        });
    };

    const handleSearchClear = (id) => {
        setFilterValue(prev => {
            const updated = { ...prev };
            delete updated[id];
            return updated;
        });
    };

    const handleSearchSubmit = () => {
        const queryString = makeQuery(filterValue);
        setParams(currentUrl, queryString);
        fetchData(); // api call
    };

    return(
        <>
            <FilterNabidka 
                filterValue={filterValue}
                handleFilterChange={handleFilterChange}
                onSearchClear={handleSearchClear}
                onSearchSubmit={handleSearchSubmit}
                locations={uniqueLocations}
                subjects={uniqueSubjects}
            />
            
            <Container property="grid grid-cols-1 gap-4 mt-2">
                {data && data.map((entity, index) => (
                    <NabidkaEntity key={entity.practice_id || index} entity={entity}/>
                ))}
            </Container>
        </>
    )
}