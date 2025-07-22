import { useApi } from "@hooks/useApi";

export const useDocumentsAPI = () => {
    const api = useApi();

    const downloadDocument = async (documentId) => {
        try {
            const res = await api.get(`/api/student-practices/download-document/${documentId}`, { responseType: "blob" });
            return res.data;
        } catch (error) {
            throw error;
        }
    };

    const uploadDocument = async (documentId, formData) => {
        try {
            const res = await api.post(`/api/student-practices/upload-document/${documentId}`, formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });
            return res.data;
        } catch (error) {
            throw error;
        }
    };

    return {
        downloadDocument,
        uploadDocument,
    };
};