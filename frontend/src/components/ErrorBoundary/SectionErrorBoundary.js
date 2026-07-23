import React from 'react';
import Container from '@core/Container/Container';
import Paragraph from '@core/Text/Paragraph';
import Button from '@core/Button/Button';
import { useTranslation } from 'react-i18next';

/**
 * SectionErrorBoundary — lightweight wrapper for individual sections/cards.
 * If one dashboard KPI card fails, only that card shows an inline error.
 *
 * Props:
 *   - children: ReactNode
 *   - onError?: (error, errorInfo) => void
 *   - sectionName?: string — shown in the error card (defaults to t('common.error_label'))
 */
class SectionErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        if (process.env.NODE_ENV !== 'production') {
            console.error('SectionErrorBoundary caught:', error, errorInfo);
        }
        if (typeof this.props.onError === 'function') {
            this.props.onError(error, errorInfo);
        }
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            return (
                <SectionErrorFallback
                    sectionName={this.props.sectionName}
                    onRetry={this.handleRetry}
                />
            );
        }

        return this.props.children;
    }
}

function SectionErrorFallback({ sectionName, onRetry }) {
    const { t } = useTranslation();

    return (
        <Container property="bg-red-50 border border-red-200 rounded-lg p-4 flex flex-col gap-3">
            <Container property="flex items-center gap-2">
                <svg
                    className="w-5 h-5 text-red-400 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                </svg>
                <Paragraph variant="baseBold" property="text-red-700">
                    {sectionName || t('common.error_label')}
                </Paragraph>
            </Container>

            <Paragraph variant="small" property="text-gray-500">
                {'Tato sekce není dostupná'}
            </Paragraph>

            <Button
                variant="redSmall"
                onClick={onRetry}
                property="self-start"
            >
                {t('common.retry')}
            </Button>
        </Container>
    );
}

export default SectionErrorBoundary;
