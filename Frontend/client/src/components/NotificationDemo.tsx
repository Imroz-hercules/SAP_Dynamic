import React from 'react';
import { useNotificationHelpers } from './NotificationSystem';

export const NotificationDemo: React.FC = () => {
  const { showSuccess, showError, showWarning, showInfo } = useNotificationHelpers();

  const handleSuccessDemo = () => {
    showSuccess(
      'Operation Successful',
      'The SAP synchronization completed successfully. 15 new orders were imported.',
      4000
    );
  };

  const handleErrorDemo = () => {
    showError(
      'SAP Connection Failed',
      'Unable to resolve the SAP server address. This usually means the VPN is not connected or the server is unreachable.',
      0,
      [
        {
          label: 'Retry Connection',
          action: () => console.log('Retrying connection...'),
          variant: 'primary'
        },
        {
          label: 'Check VPN Status',
          action: () => console.log('Checking VPN...'),
          variant: 'secondary'
        }
      ]
    );
  };

  const handleWarningDemo = () => {
    showWarning(
      'Data Sync Warning',
      'Some orders could not be synchronized due to data format issues. Please review the logs.',
      5000
    );
  };

  const handleInfoDemo = () => {
    showInfo(
      'SAP Maintenance Scheduled',
      'SAP system will be under maintenance from 2:00 AM to 4:00 AM tomorrow. Please plan accordingly.',
      6000
    );
  };

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">
        Notification System Demo
      </h2>
      
      <div className="grid grid-cols-2 gap-4">
        <button
          onClick={handleSuccessDemo}
          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
        >
          Show Success Notification
        </button>
        
        <button
          onClick={handleErrorDemo}
          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
        >
          Show Error Notification
        </button>
        
        <button
          onClick={handleWarningDemo}
          className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
        >
          Show Warning Notification
        </button>
        
        <button
          onClick={handleInfoDemo}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          Show Info Notification
        </button>
      </div>
    </div>
  );
};
