import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
    isExpanded: boolean;
}

class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
            isExpanded: false
        };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, errorInfo: null, isExpanded: false };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('ErrorBoundary caught:', error, errorInfo);
        this.setState({ errorInfo });
    }

    handleReload = () => {
        window.location.reload();
    };

    toggleExpand = () => {
        this.setState(prevState => ({ isExpanded: !prevState.isExpanded }));
    };

    render() {
        if (this.state.hasError) {
            const { error, errorInfo, isExpanded } = this.state;

            return (
                <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 dark:bg-slate-900 p-4 transition-colors duration-300">
                    <div className="max-w-md w-full bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden transition-all duration-300">
                        {/* Header / Icon */}
                        <div className="p-6 flex flex-col items-center text-center">
                            <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
                                <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
                            </div>

                            <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                                Something went wrong
                            </h2>

                            <p className="text-slate-600 dark:text-slate-300 mb-6">
                                The page encountered an unexpected error.
                            </p>

                            <button
                                onClick={this.handleReload}
                                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-slate-800 flex items-center justify-center gap-2"
                            >
                                <RefreshCw className="w-4 h-4" />
                                Reload Page
                            </button>
                        </div>

                        {/* Expandable Details */}
                        <div className="border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                            <button
                                onClick={this.toggleExpand}
                                className="w-full px-6 py-3 flex items-center justify-between text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors focus:outline-none"
                            >
                                <span>Error Details</span>
                                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </button>

                            {isExpanded && (
                                <div className="px-6 pb-6 pt-0 animate-in slide-in-from-top-2 duration-200">
                                    <div className="p-3 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 overflow-x-auto">
                                        <p className="text-xs font-mono text-red-600 dark:text-red-400 mb-2 font-semibold">
                                            {error?.toString()}
                                        </p>
                                        {errorInfo && (
                                            <pre className="text-[10px] font-mono text-slate-500 dark:text-slate-500 whitespace-pre-wrap">
                                                {errorInfo.componentStack}
                                            </pre>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
