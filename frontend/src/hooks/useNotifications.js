import { useNotificationContext } from "./NotificationProvider";

export const useNotifications = () => {
    return useNotificationContext();
};
