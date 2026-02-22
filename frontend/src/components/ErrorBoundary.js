import React from 'react';

/**
 * Catches unhandled render errors in the component tree and shows a
 * user-friendly fallback instead of a blank screen.
 */
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError() {
        return { hasError: true };
    }

    componentDidCatch(error, info) {
        // In production you would forward this to an error-tracking service.
        if (process.env.NODE_ENV !== 'production') {
            console.error('ErrorBoundary caught:', error, info);
        }
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-gray-100">
                    <div className="text-center p-8 bg-white rounded-lg shadow-md max-w-md">
                        <h2 className="text-xl font-bold text-red-600 mb-2">
                            Něco se pokazilo
                        </h2>
                        <p className="text-gray-600 mb-4">
                            Došlo k neočekávané chybě. Zkuste obnovit stránku.
                        </p>
                        <button
                            onClick={() => window.location.reload()}
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                        >
                            Obnovit stránku
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
