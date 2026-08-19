import React from 'react';

interface LoadingOverlayProps {
  isLoading: boolean;
  message?: string;
  subMessage?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({ 
  isLoading, 
  message = "Loading...", 
  subMessage 
}) => {
  if (!isLoading) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-8 shadow-2xl max-w-md mx-4">
        <div className="flex flex-col items-center space-y-4">
          {/* Spinner */}
          <div className="relative">
            <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 rounded-full animate-spin border-t-blue-600 dark:border-t-blue-400"></div>
            <div className="absolute inset-0 w-12 h-12 border-4 border-transparent rounded-full animate-ping border-t-blue-400/30"></div>
          </div>
          
          {/* Message */}
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {message}
            </h3>
            {subMessage && (
              <p className="text-sm text-gray-600 dark:text-gray-300">
                {subMessage}
              </p>
            )}
          </div>
          
          {/* Progress dots */}
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
        </div>
      </div>
    </div>
  );
};

interface LoadingButtonProps {
  isLoading: boolean;
  loadingText?: string;
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
  onClick?: () => void;
}

export const LoadingButton: React.FC<LoadingButtonProps> = ({
  isLoading,
  loadingText = "Loading...",
  children,
  className = "",
  disabled = false,
  onClick
}) => {
  return (
    <button
      className={`relative ${className} ${(isLoading || disabled) ? 'opacity-50 cursor-not-allowed' : ''}`}
      disabled={isLoading || disabled}
      onClick={onClick}
    >
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-4 h-4 border-2 border-white/30 rounded-full animate-spin border-t-white"></div>
        </div>
      )}
      <span className={isLoading ? 'opacity-0' : 'opacity-100'}>
        {children}
      </span>
      {isLoading && (
        <span className="absolute inset-0 flex items-center justify-center text-sm">
          {loadingText}
        </span>
      )}
    </button>
  );
};
