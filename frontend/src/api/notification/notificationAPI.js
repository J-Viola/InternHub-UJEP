import { useCallback, useMemo } from "react";
import { useApi } from "@hooks/useApi";

export const useNotificationAPI = () => {
    const api = useApi();

    const getNotifications = useCallback(async (params = {}) => {
        const response = await api.get("/notifications/", { params });
        return response.data;
    }, [api]);

    const getUnreadCount = useCallback(async () => {
        const response = await api.get("/notifications/unread_count/");
        return response.data?.unread_count ?? 0;
    }, [api]);

    const markAsRead = useCallback(async (id) => {
        const response = await api.patch(`/notifications/${id}/read/`);
        return response.data;
    }, [api]);

    const markAllAsRead = useCallback(async () => {
        const response = await api.post("/notifications/read_all/");
        return response.data;
    }, [api]);

    return useMemo(() => ({
        getNotifications,
        getUnreadCount,
        markAsRead,
        markAllAsRead,
    }), [getNotifications, getUnreadCount, markAsRead, markAllAsRead]);
};
