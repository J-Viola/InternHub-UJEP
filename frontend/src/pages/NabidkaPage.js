import React, { useEffect, useState, useCallback } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import NabidkaEntity from "@components/Nabidka/NabidkaEntity";
import FilterNabidka from "@components/Nabidka/FilterNabidka";
import { makeQuery, useCurrentUrl, useSetParams, useFullUrl, useStripParams } from "@hooks/SearchParams";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";
import { useCodeListAPI } from "@api/code_list/code_listAPI";
import { useMessage } from "@hooks/MessageContext";
import Pagination from "@components/core/Pagination";
import useDebounce from "@hooks/useDebounce";
import { useUser } from "@hooks/UserProvider";
import { useTranslation } from "react-i18next";

const PAGE_SIZE = 10;

export default function NabidkaPage() {
    const { t } = useTranslation();
    const currentUrl = useCurrentUrl();
    const setParams = useSetParams();
    const fullUrl = useFullUrl();
    const stripUrlParams = useStripParams();
    const [filterValue, setFilterValue] = useState({});
    const [data, setData] = useState([]);
    const [count, setCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const [uniqueLocations, setLocations] = useState([]);
    const [uniqueSubjects, setSubjects] = useState([]);

    const nabidkaAPI = useNabidkaAPI();
    const codelist = useCodeListAPI();
    const { addMessage } = useMessage();
    const { user } = useUser();

    const totalPages = Math.ceil(count / PAGE_SIZE);

    // Debounce the title text so we auto-search 400 ms after the user stops typing
    const debouncedTitle = useDebounce(filterValue.title, 400);

    const fetchData = useCallback(async (filters = filterValue, page = currentPage) => {
        setLoading(true);
        setError(null);
        try {
            const result = await nabidkaAPI.getNabidky({ ...filters, page, page_size: PAGE_SIZE });
            setData(result.results);
            setCount(result.count);
        } catch {
            setError(t('common.error'));
        } finally {
            setLoading(false);
        }
    }, [t]);

    const initFilterOptions = async () => {
        try {
            const [locations, subjects] = await Promise.all([
                codelist.getUniqueLocations(),
                codelist.getUniqueSubjects(),
            ]);
            setLocations(locations);
            setSubjects(subjects);
        } catch {
            // filter options are non-critical, silently ignore
        }
    };

    useEffect(() => {
        const urlParams = stripUrlParams(fullUrl);
        const initialFilters = (urlParams && Object.keys(urlParams).length > 0) ? urlParams : {};
        setFilterValue(initialFilters);
        setCurrentPage(1);
        fetchData(initialFilters, 1);
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
            const updated = { ...prev };
            if (newValue === "" || newValue == null) {
                delete updated[key];
            } else {
                updated[key] = newValue;
            }
            return updated;
        });
    };

    const handleSearchClear = (id) => {
        setFilterValue(prev => {
            const updated = { ...prev };
            delete updated[id];
            return updated;
        });
    };

    // Auto-fetch when title text changes (debounced)
    useEffect(() => {
        setCurrentPage(1);
        fetchData(filterValue, 1);
    }, [debouncedTitle]);

    const handleSearchSubmit = () => {
        const queryString = makeQuery(filterValue);
        setParams(currentUrl, queryString);
        setCurrentPage(1);
        fetchData(filterValue, 1);
    };

    const handlePageChange = (page) => {
        setCurrentPage(page);
        fetchData(filterValue, page);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const isShowingFavorites = filterValue.favorites === "true";
    const handleFavoritesToggle = () => {
        const newFilters = { ...filterValue };
        if (isShowingFavorites) {
            delete newFilters.favorites;
        } else {
            newFilters.favorites = "true";
        }
        setFilterValue(newFilters);
        setCurrentPage(1);
        fetchData(newFilters, 1);
    };

    return (
        <>
            <Container property={"flex items-center justify-between mb-4 mt-4"}>
                <Headings sizeTag={"h3"}>{t('offers.title')}</Headings>
            </Container>

            <FilterNabidka
                filterValue={filterValue}
                handleFilterChange={handleFilterChange}
                onSearchClear={handleSearchClear}
                onSearchSubmit={handleSearchSubmit}
                locations={uniqueLocations}
                subjects={uniqueSubjects}
            />

            {user?.isStudent() && (
                <Container property="flex justify-end mb-4 -mt-4">
                    <button
                        onClick={handleFavoritesToggle}
                        className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full border transition-colors duration-200 ${
                            isShowingFavorites
                                ? "bg-red-50 border-red-300 text-red-600"
                                : "bg-white border-gray-300 text-gray-500 hover:border-red-300 hover:text-red-500"
                        }`}
                    >
                        <span>{isShowingFavorites ? "♥" : "♡"}</span>
                        {isShowingFavorites ? t('offers.showing_favorites') : t('offers.favorites_only')}
                    </button>
                </Container>
            )}

            {loading && (
                <Container property="flex justify-center py-12">
                    <Paragraph property="text-gray-500">{t('offers.loading')}</Paragraph>
                </Container>
            )}

            {!loading && error && (
                <Container property="flex justify-center py-12">
                    <Paragraph property="text-red-500">{error}</Paragraph>
                </Container>
            )}

            {!loading && !error && data.length === 0 && (
                <Container property="flex justify-center py-12">
                    <Paragraph property="text-gray-500">{t('offers.no_results')}</Paragraph>
                </Container>
            )}

            {!loading && !error && data.length > 0 && (
                <>
                    <Container property="grid grid-cols-1 gap-4 mt-2">
                        {data.map((entity, index) => (
                            <NabidkaEntity key={entity.practice_id || index} entity={entity} />
                        ))}
                    </Container>

                    <Pagination
                        currentPage={currentPage}
                        totalPages={totalPages}
                        onPageChange={handlePageChange}
                    />
                </>
            )}
        </>
    );
}
