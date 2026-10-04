import React, { useState, useEffect } from 'react';
import { useNotificationAPI } from '@api/notification/notificationAPI';
import Container from '@core/Container/Container';
import Headings from '@core/Text/Headings';
import Paragraph from '@core/Text/Paragraph';
import BackButton from '@core/Button/BackButton';
import Button from '@core/Button/Button';
import { useTranslation } from 'react-i18next';
import { useMessage } from '@hooks/MessageContext';
import { useNavigate } from 'react-router-dom';

const NotificationsPage = () => {
    const { t, i18n } = useTranslation();
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const notificationAPI = useNotificationAPI();
    const { addMessage } = useMessage();
    const navigate = useNavigate();

    const fetchAllNotifications = async () => {
        setLoading(true);
        try {
            const data = await notificationAPI.getNotifications();
            setNotifications(data.results || data || []);
        } catch (error) {
            console.error('Failed to fetch all notifications:', error);
            addMessage(t('common.error'), 'E');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAllNotifications();
    }, []);

    const handleMarkAsRead = async (id) => {
        try {
            await notificationAPI.markAsRead(id);
            setNotifications(prev =>
                prev.map(n => n.id === id ? { ...n, is_read: true } : n)
            );
        } catch (error) {
            console.error('Failed to mark notification as read:', error);
            addMessage(t('common.error'), 'E');
        }
    };

    const handleMarkAllAsRead = async () => {
        try {
            await notificationAPI.markAllAsRead();
            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
            addMessage(t('common.save'), 'S');
        } catch (error) {
            console.error('Failed to mark all notifications as read:', error);
            addMessage(t('common.error'), 'E');
        }
    };

    const handleNotificationClick = (notification) => {
        if (!notification.is_read) {
            handleMarkAsRead(notification.id);
        }
        // Navigace na target odkaz notifikace (např. EXPORT_READY).
        const targetUrl = notification.target_url || notification.url || '';
        if (targetUrl) {
            if (/^https?:\/\//i.test(targetUrl)) {
                window.open(targetUrl, '_blank', 'noopener,noreferrer');
            } else {
                navigate(targetUrl);
            }
        }
    };

    const getMessage = (n) => i18n.language === 'en'
        ? (n.message_en || n.message)
        : (n.message_cz || n.message);

    return (
        <Container property="max-w-4xl mx-auto p-4">
            <BackButton />
            <Container property="flex justify-between items-center mb-6 mt-4">
                <Headings sizeTag="h2">{t('nav.notifications')}</Headings>
                {notifications.some(n => !n.is_read) && (
                    <Button variant="blueSmall" onClick={handleMarkAllAsRead}>
                        {t('notifications.mark_all_read')}
                    </Button>
                )}
            </Container>

            {loading ? (
                <Paragraph>{t('common.loading')}</Paragraph>
            ) : notifications.length === 0 ? (
                <Container property="bg-white p-8 rounded-lg shadow-sm text-center border border-gray-100">
                    <Paragraph property="text-gray-500 italic">{t('notifications.no_notifications')}</Paragraph>
                </Container>
            ) : (
                <div className="space-y-3">
                    {notifications.map((notification) => (
                        <div
                            key={notification.id}
                            onClick={() => handleNotificationClick(notification)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') handleNotificationClick(notification);
                            }}
                            className={`p-4 bg-white rounded-lg shadow-sm border-l-4 transition-all ${
                                !notification.is_read ? 'border-l-blue-600' : 'border-l-gray-300 opacity-75'
                            } hover:shadow-md cursor-pointer`}
                        >
                            <div className="flex justify-between items-start mb-2">
                                <span className={`text-xs uppercase font-bold px-2 py-1 rounded ${
                                    notification.notification_type === 1 ? 'bg-green-100 text-green-700' :
                                    notification.notification_type === 2 ? 'bg-yellow-100 text-yellow-700' :
                                    notification.notification_type === 3 ? 'bg-red-100 text-red-700' :
                                    'bg-blue-100 text-blue-700'
                                }`}>
                                    {notification.verb.replace(/_/g, ' ')}
                                </span>
                                <span className="text-xs text-gray-500">
                                    {new Date(notification.created_at).toLocaleString()}
                                </span>
                            </div>
                            <Paragraph property="text-gray-800 text-base">
                                {getMessage(notification)}
                            </Paragraph>
                            {!notification.is_read && (
                                <button className="mt-2 text-xs text-blue-600 hover:underline">
                                    {t('notifications.mark_as_read')}
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </Container>
    );
};

export default NotificationsPage;
