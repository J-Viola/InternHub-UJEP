import React from 'react';

/**
 * Reusable class-based ErrorBoundary that catches rendering errors in its children.
 *
 * Props:
 *   - fallback?: ReactNode — custom fallback UI (overrides the default)
 *   - onError?: (error, errorInfo) => void — callback for logging/reporting
 *   - title?: string — heading shown in the default fallback
 *   - description?: string — body text shown in the default fallback
 */
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        if (process.env.NODE_ENV !== 'production') {
            console.error('ErrorBoundary caught:', error, errorInfo);
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
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <DefaultFallback
                    title={this.props.title}
                    description={this.props.description}
                    onRetry={this.handleRetry}
                />
            );
        }

        return this.props.children;
    }
}

function DefaultFallback({ title, description, onRetry }) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
            <div className="text-center p-8 bg-white rounded-lg shadow-md max-w-md">
                <h2 className="text-xl font-bold text-red-600 mb-2">
                    {title || 'Došlo k chybě'}
                </h2>
                <p className="text-gray-600 mb-4">
                    {description || 'Došlo k nečekané chybě. Zkuste to prosím znovu.'}
                </p>
                <button
                    onClick={onRetry}
                    className="px-4 py-2 bg-facultyCol text-white rounded-lg hover:bg-gray-400 transition-colors duration-200"
                >
                    {'Zkusit znovu'}
                </button>
            </div>
        </div>
    );
}

/**
 * HOC that wraps a component with an individual ErrorBoundary.
 * Each route gets its own boundary so an error on one page
 * does not crash the entire SPA.
 */
export function withErrorBoundary(WrappedComponent, options = {}) {
    return function WithErrorBoundaryWrapper(props) {
        return (
            <ErrorBoundary {...options}>
                <WrappedComponent {...props} />
            </ErrorBoundary>
        );
    };
}

export default ErrorBoundary;
