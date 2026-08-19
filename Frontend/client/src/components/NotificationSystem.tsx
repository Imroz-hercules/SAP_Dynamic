import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// Notification types
export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  duration?: number; // Auto-dismiss duration in ms (0 = no auto-dismiss)
  actions?: NotificationAction[];
}

export interface NotificationAction {
  label: string;
  action: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
}

interface NotificationContextType {
  showNotification: (notification: Omit<Notification, 'id'>) => void;
  hideNotification: (id: string) => void;
  clearAllNotifications: () => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const showNotification = useCallback((notification: Omit<Notification, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newNotification: Notification = {
      ...notification,
      id,
      duration: notification.duration ?? 5000, // Default 5 seconds
    };

    setNotifications(prev => [...prev, newNotification]);

    // Auto-dismiss if duration is set
    if (newNotification.duration > 0) {
      setTimeout(() => {
        hideNotification(id);
      }, newNotification.duration);
    }
  }, []);

  const hideNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  return (
    <NotificationContext.Provider value={{ showNotification, hideNotification, clearAllNotifications }}>
      {children}
      <NotificationContainer notifications={notifications} onHide={hideNotification} />
    </NotificationContext.Provider>
  );
};

interface NotificationContainerProps {
  notifications: Notification[];
  onHide: (id: string) => void;
}

const NotificationContainer: React.FC<NotificationContainerProps> = ({ notifications, onHide }) => {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-3 max-w-md">
      {notifications.map(notification => (
        <NotificationItem
          key={notification.id}
          notification={notification}
          onHide={onHide}
        />
      ))}
    </div>
  );
};

interface NotificationItemProps {
  notification: Notification;
  onHide: (id: string) => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({ notification, onHide }) => {
  const { type, title, message, actions } = notification;

  const getNotificationStyles = () => {
    switch (type) {
      case 'success':
        return {
          container: 'bg-gradient-to-r from-green-500 to-emerald-600 border-green-400',
          icon: 'text-green-100',
          title: 'text-green-50',
          message: 'text-green-100',
          closeButton: 'text-green-200 hover:text-green-50 hover:bg-green-600/30'
        };
      case 'error':
        return {
          container: 'bg-gradient-to-r from-red-500 to-rose-600 border-red-400',
          icon: 'text-red-100',
          title: 'text-red-50',
          message: 'text-red-100',
          closeButton: 'text-red-200 hover:text-red-50 hover:bg-red-600/30'
        };
      case 'warning':
        return {
          container: 'bg-gradient-to-r from-yellow-500 to-amber-600 border-yellow-400',
          icon: 'text-yellow-100',
          title: 'text-yellow-50',
          message: 'text-yellow-100',
          closeButton: 'text-yellow-200 hover:text-yellow-50 hover:bg-yellow-600/30'
        };
      case 'info':
        return {
          container: 'bg-gradient-to-r from-blue-500 to-cyan-600 border-blue-400',
          icon: 'text-blue-100',
          title: 'text-blue-50',
          message: 'text-blue-100',
          closeButton: 'text-blue-200 hover:text-blue-50 hover:bg-blue-600/30'
        };
      default:
        return {
          container: 'bg-gradient-to-r from-gray-500 to-slate-600 border-gray-400',
          icon: 'text-gray-100',
          title: 'text-gray-50',
          message: 'text-gray-100',
          closeButton: 'text-gray-200 hover:text-gray-50 hover:bg-gray-600/30'
        };
    }
  };

  const getIcon = () => {
    switch (type) {
      case 'success':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'error':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        );
      case 'info':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return null;
    }
  };

  const styles = getNotificationStyles();

  return (
    <div className={`
      ${styles.container}
      border-2 shadow-2xl rounded-xl p-4 backdrop-blur-sm
      transform transition-all duration-300 ease-in-out
      hover:scale-105 hover:shadow-3xl
      animate-in slide-in-from-right-full
    `}>
      <div className="flex items-start space-x-3">
        {/* Icon */}
        <div className={`flex-shrink-0 ${styles.icon}`}>
          {getIcon()}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h4 className={`text-sm font-semibold ${styles.title} mb-1`}>
            {title}
          </h4>
          <p className={`text-sm ${styles.message} break-words`}>
            {message}
          </p>

          {/* Actions */}
          {actions && actions.length > 0 && (
            <div className="mt-3 flex space-x-2">
              {actions.map((action, index) => (
                <button
                  key={index}
                  onClick={action.action}
                  className={`
                    px-3 py-1 text-xs font-medium rounded-md transition-colors
                    ${action.variant === 'danger' 
                      ? 'bg-red-600/20 text-red-100 hover:bg-red-600/30' 
                      : action.variant === 'primary'
                      ? 'bg-white/20 text-white hover:bg-white/30'
                      : 'bg-black/20 text-white hover:bg-black/30'
                    }
                  `}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Close Button */}
        <button
          onClick={() => onHide(notification.id)}
          className={`
            flex-shrink-0 p-1 rounded-md transition-colors
            ${styles.closeButton}
          `}
          aria-label="Close notification"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
};

// Utility functions for common notifications
export const useNotificationHelpers = () => {
  const { showNotification } = useNotification();

  const showSuccess = useCallback((title: string, message: string, duration?: number) => {
    showNotification({
      type: 'success',
      title,
      message,
      duration: duration ?? 4000,
    });
  }, [showNotification]);

  const showError = useCallback((title: string, message: string, duration?: number, actions?: NotificationAction[]) => {
    showNotification({
      type: 'error',
      title,
      message,
      duration: duration ?? 0, // Don't auto-dismiss errors
      actions,
    });
  }, [showNotification]);

  const showWarning = useCallback((title: string, message: string, duration?: number) => {
    showNotification({
      type: 'warning',
      title,
      message,
      duration: duration ?? 5000,
    });
  }, [showNotification]);

  const showInfo = useCallback((title: string, message: string, duration?: number) => {
    showNotification({
      type: 'info',
      title,
      message,
      duration: duration ?? 4000,
    });
  }, [showNotification]);

  return {
    showSuccess,
    showError,
    showWarning,
    showInfo,
  };
};
