import React from 'react';
import Container from '@core/Container/Container';
import Headings from '@core/Text/Headings';
import Paragraph from '@core/Text/Paragraph';
import Button from '@core/Button/Button';

/**
 * RouteErrorBoundary — a route-level ErrorBoundary that renders a full-page
 * error state matching the app design system (faculty colors, core components).
 *
 * Props:
 *   - children: ReactNode
 *   - onError?: (error, errorInfo) => void
 *   - pageTitle?: string — shown in the error card (defaults to „Něco se pokazilo“)
 */
class RouteErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        if (process.env.NODE_ENV !== 'production') {
            console.error('RouteErrorBoundary caught:', error, errorInfo);
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
                <RouteErrorFallback
                    pageTitle={this.props.pageTitle}
                    onRetry={this.handleRetry}
                />
            );
        }

        return this.props.children;
    }
}

function RouteErrorFallback({ pageTitle, onRetry }) {

    return (
        <Container property="min-h-screen flex items-center justify-center bg-gray-100 px-4">
            <Container property="bg-white rounded-lg shadow-lg p-8 max-w-lg w-full text-center">
                <Container property="bg-red-50 p-4 rounded-full mb-6 inline-flex items-center justify-center">
                    <svg
                        className="w-12 h-12 text-red-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                        />
                    </svg>
                </Container>

                <Headings sizeTag="h4" property="text-gray-900 font-bold mb-2">
                    {pageTitle || "Něco se pokazilo"}
                </Headings>

                <Paragraph property="text-gray-500 mb-6">
                    {"Došlo k neočekávané chybě"}
                </Paragraph>

                <Button
                    variant="primary"
                    onClick={onRetry}
                    property="px-8"
                >
                    {"Zkusit znovu"}
                </Button>
            </Container>
        </Container>
    );
}

export default RouteErrorBoundary;
