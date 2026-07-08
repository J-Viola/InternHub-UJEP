import React, { useState, useRef, useEffect } from 'react';
import { useNotifications } from '@hooks/useNotifications';
import Paragraph from '@core/Text/Paragraph';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

const NotificationBell = () => {
    const { t, i18n } = useTranslation();
    const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();
    const [isOpen, setIsOpen] = useState(false);
    const navigate = useNavigate();
    const dropdownRef = useRef(null);

    const toggleDropdown = () => setIsOpen(!isOpen);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen]);

    const handleNotificationClick = (notification) => {
        if (!notification.is_read) {
            markAsRead(notification.id);
        }
        setIsOpen(false);
    };

    const getMessage = (n) => i18n.language === 'en' ? (n.message_en || n.message_cz) : n.message_cz;

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={toggleDropdown}
                className="relative p-2 text-gray-600 hover:text-blue-600 focus:outline-none transition-colors"
                aria-label={t('notifications.label')}
            >
                <i className="fa-solid fa-bell text-xl"></i>
                {unreadCount > 0 && (
                    <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-red-100 transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full border-2 border-white">
                        {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                )}
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-100 z-50 overflow-hidden">
                    <div className="p-3 border-b border-gray-100 flex justify-between items-center bg-gray-50">
                        <span className="font-bold text-gray-800">{t('nav.notifications')}</span>
                        {unreadCount > 0 && (
                            <button
                                onClick={markAllAsRead}
                                className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
                            >
                                {t('notifications.mark_all_read')}
                            </button>
                        )}
                    </div>

                    <div className="max-h-96 overflow-y-auto">
                        {notifications.length === 0 ? (
                            <div className="p-4 text-center text-gray-500 italic">
                                {t('notifications.no_notifications')}
                            </div>
                        ) : (
                            notifications.map((notification) => (
                                <div
                                    key={notification.id}
                                    onClick={() => handleNotificationClick(notification)}
                                    className={`p-3 border-b border-gray-50 cursor-pointer hover:bg-blue-50 transition-colors ${!notification.is_read ? 'bg-blue-50/30' : ''}`}
                                >
                                    <div className="flex justify-between items-start mb-1">
                                        <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                            notification.notification_type === 1 ? 'bg-green-100 text-green-700' :
                                            notification.notification_type === 2 ? 'bg-yellow-100 text-yellow-700' :
                                            notification.notification_type === 3 ? 'bg-red-100 text-red-700' :
                                            'bg-blue-100 text-blue-700'
                                        }`}>
                                            {notification.verb.replace(/_/g, ' ')}
                                        </span>
                                        <span className="text-[10px] text-gray-400">
                                            {new Date(notification.created_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                    {notification.actor_name && (
                                        <div className="text-[10px] text-gray-500 font-medium mb-1">
                                            Od: {notification.actor_name}
                                        </div>
                                    )}
                                    <Paragraph property="text-sm leading-snug">
                                        {getMessage(notification)}
                                    </Paragraph>
                                </div>
                            ))
                        )}
                    </div>

                    <button
                        onClick={() => { navigate('/notifikace'); setIsOpen(false); }}
                        className="w-full p-2 text-sm text-center text-gray-600 hover:bg-gray-50 hover:text-blue-600 transition-all font-medium border-t border-gray-100"
                    >
                        {t('notifications.view_all')}
                    </button>
                </div>
            )}
        </div>
    );
};

export default NotificationBell;
