import { useCallback, useMemo } from "react";
import { useApi } from "@hooks/useApi";
import { buildFormData } from "@utils/formDataUtils";

export const useNabidkaAPI = () => {
    const api = useApi();

    const getNabidky = useCallback(async (params = {}) => {
        try {
            const response = await api.get('/practices/student/', { params });

            if (response && response.data) {
                // Backend returns paginated shape: { count, next, previous, results }
                if (response.data.results !== undefined) {
                    return {
                        results: response.data.results,
                        count: response.data.count ?? 0,
                        next: response.data.next,
                        previous: response.data.previous,
                    };
                }
                // Fallback: plain array (no pagination)
                return { results: response.data, count: response.data.length, next: null, previous: null };
            }

            return { results: [], count: 0, next: null, previous: null };
        } catch (error) {
            throw error;
        }
    }, [api]);

    const getAdminPractices = useCallback(async () => {
        try {
            const response = await api.get('/practices/admin-practices/');
            if (response && response.data) {
                return response.data.results !== undefined ? response.data.results : response.data;
            }
            return [];
        } catch (error) {
            console.error("Chyba při získávání praxí admina:", error);
            throw error;
        }
    }, [api]);

    // Detail vlastní nabídky pro editaci — katalogový endpoint skrývá nezveřejněné nabídky (404).
    const getEmployerNabidkaById = useCallback(async (id) => {
        try {
            const response = await api.get(`/practices/employer/${id}/`)
            return response && response.data ? response.data : null
        } catch (error) {
            console.error("Chyba při získávání nabídky organizace podle ID:", error);
            throw error;
        }
    }, [api]);

    const getNabidkaById = useCallback(async (id) => {
        try {
            const response = await api.get(`/practices/student/${id}/`)

            if (response && response.data) {
                return response.data
            }

            return null

        } catch (error) {
            console.error("Chyba při získávání nabídky podle ID:", error);
            throw error;
        }
    }, [api]);

    const createNabidka = useCallback(async (data) => {
        try {
            const formData = buildFormData(data);

            const response = await api.post('/practices/employer/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            if (response && response.data) {
                sessionStorage.setItem("pendingMessage", JSON.stringify({
                    text: "Nabídka byla úspěšně vytvořena",
                    type: "S"
                }));
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při vytváření nabídky:", error);
            throw error;
        }
    }, [api]);

    const applyNabidka = useCallback(async (data) => {
        try {
            const formData = buildFormData(data);

            const response = await api.post('/practices/student/apply/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            if (response && response.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při vytváření nabídky:", error);
            throw error;
        }
    }, [api]);

    const getPracticeUserRelations = useCallback(async () => {
        try {
            const response = await api.get('/practices/student/get_practice_user_relations/');

            if (response && response.data) {
                return response.data;
            }
            return null

        } catch (error) {
            console.error('Chyba při získávání uživatelů organizace:', error);
            throw error;
        }
    }, [api]);

    const getOrganizationPractices = useCallback(async () => {
        try {
            const response = await api.get('/practices/employer/');

            if (response && response.data) {
                if (response.data.results !== undefined) {
                    return {
                        results: response.data.results,
                        count: response.data.count ?? 0,
                    };
                }
                return response.data;
            }
            return { results: [], count: 0 };

        } catch (error) {
            console.error('Chyba při získávání praxí organizace:', error);
            throw error;
        }
    }, [api]);

    const getNabidkyByUserDepartment = useCallback(async () => {
        try {
            const response = await api.get('/practices/staff/department_overview/');
            if (response && response.data) {
                return response.data;
            }
            return { approved_practices: [], to_approve_practices: [], active_offers: [] };
        } catch (error) {
            console.error('Chyba při získávání nabídek podle katedry uživatele:', error);
            throw error;
        }
    }, [api]);

    const changeStatus = useCallback(async (id, status) => {
        try {
            const response = await api.post(`/practices/staff/${id}/approve/`, status);
            if (response && response.data) {
                return response.data;
            }
        } catch (error) {
            console.error('Chyba při změně stavu nabídky:', error);
            throw error;
        }
    }, [api]);

    // BL-07/PBUG-BL07-07: stornování aktivní nabídky — reálná UI akce.
    // Backend: POST /api/practices/{id}/cancel/ (CanCancelPractice: admin /
    // vedoucí katedry / garant); důvod je povinný.
    const cancelPractice = useCallback(async (practiceId, reason) => {
        try {
            const response = await api.post(`/practices/${practiceId}/cancel/`, { reason });
            if (response && response.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error('Chyba při stornování nabídky:', error);
            throw error;
        }
    }, [api]);

    const calculateEndDate = useCallback(async (startDate, employmentLoad) => {
        try {
            const response = await api.post('/practices/get-end-date/', {
                start_date: startDate,
                coefficient: employmentLoad
            });

            if (response && response.data) {
                return response.data.end_date;
            }
            return null;
        } catch (error) {
            console.error('Chyba při výpočtu koncového data:', error);
            throw error;
        }
    }, [api]);

    const updateNabidka = useCallback(async (id, data, isPartial = false) => {
        try {
            const formData = buildFormData(data);

            const method = isPartial ? 'patch' : 'put';
            const response = await api[method](`/practices/employer/${id}/`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            if (response && response.data) {
                sessionStorage.setItem("pendingMessage", JSON.stringify({
                    text: "Nabídka byla úspěšně aktualizována",
                    type: "S"
                }));
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při aktualizaci nabídky:", error);
            throw error;
        }
    }, [api]);

    const createExternalPractice = useCallback(async (data) => {
        try {
            // externí praxe nese povinnou přílohu external_details_file
            // (PDF/DOCX ≤ 10 MB) → payload se posílá jako multipart/FormData.
            // Detekujeme File (i uvnitř polí) a payload převedeme přes buildFormData;
            // bez přílohy posíláme JSON (zpětná kompatibilita).
            const hasFile = data instanceof FormData ||
                (data && Object.values(data).some(v =>
                    v instanceof File || (Array.isArray(v) && v.some(item => item instanceof File))
                ));

            const payload = hasFile && !(data instanceof FormData) ? buildFormData(data) : data;

            const response = await api.post('/practices/external/', payload, {
                headers: {
                    'Content-Type': hasFile ? 'multipart/form-data' : 'application/json',
                },
            });

            if (response && response.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při vytváření mimosystémové praxe:", error);
            throw error;
        }
    }, [api]);

    const toggleFavorite = useCallback(async (id) => {
        try {
            const response = await api.post(`/practices/student/${id}/toggle_favorite/`);
            return response.data;
        } catch (error) {
            console.error('Chyba při změně oblíbených:', error);
            throw error;
        }
    }, [api]);

    return useMemo(() => ({
        getNabidky,
        getNabidkaById,
        getEmployerNabidkaById,
        createNabidka,
        applyNabidka,
        getPracticeUserRelations,
        getOrganizationPractices,
        getNabidkyByUserDepartment,
        changeStatus,
        cancelPractice,
        calculateEndDate,
        updateNabidka,
        getAdminPractices,
        toggleFavorite,
        createExternalPractice
    }), [getNabidky, getNabidkaById, getEmployerNabidkaById, createNabidka, applyNabidka,
        getPracticeUserRelations, getOrganizationPractices, getNabidkyByUserDepartment,
        changeStatus, cancelPractice, calculateEndDate, updateNabidka,
        getAdminPractices, toggleFavorite, createExternalPractice]);
};
