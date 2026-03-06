import React from 'react';
import { useTranslation } from "react-i18next";

/**
 * Simple previous / next page controls.
 *
 * Props:
 *   currentPage  – 1-based current page number
 *   totalPages   – total number of pages (Math.ceil(count / pageSize))
 *   onPageChange – callback(newPage: number)
 */
export default function Pagination({ currentPage, totalPages, onPageChange }) {
    const { t } = useTranslation();
    if (!totalPages || totalPages <= 1) return null;

    return (
        <div className="flex items-center justify-center gap-4 mt-6 mb-2">
            <button
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage <= 1}
                className="px-4 py-2 rounded border text-sm font-medium
                           disabled:opacity-40 disabled:cursor-not-allowed
                           hover:bg-gray-100 transition-colors"
            >
                ← {t('pagination.previous')}
            </button>

            <span className="text-sm text-gray-600">
                {t('pagination.page')} {currentPage} / {totalPages}
            </span>

            <button
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage >= totalPages}
                className="px-4 py-2 rounded border text-sm font-medium
                           disabled:opacity-40 disabled:cursor-not-allowed
                           hover:bg-gray-100 transition-colors"
            >
                {t('pagination.next')} →
            </button>
        </div>
    );
}
