// utils/sapErrorHandler.ts
import { NotificationAction } from '../components/NotificationSystem';

export interface SAPError {
  type: 'connection' | 'authentication' | 'data' | 'network' | 'unknown';
  title: string;
  message: string;
  suggestions: string[];
  actions?: NotificationAction[];
}

export const parseSAPError = (error: any): SAPError => {
  const errorMessage = error?.message || error?.toString() || 'Unknown error occurred';
  
  // Connection/DNS errors
  if (errorMessage.includes('NameResolutionError') || errorMessage.includes('getaddrinfo failed')) {
    return {
      type: 'connection',
      title: 'SAP Connection Failed',
      message: 'Unable to resolve the SAP server address. This usually means the VPN is not connected or the server is unreachable.',
      suggestions: [
        'Check if VPN is connected to the corporate network',
        'Verify the SAP server address is correct',
        'Contact IT support if the issue persists',
        'Try again in a few minutes'
      ],
      actions: [
        {
          label: 'Retry Connection',
          action: () => window.location.reload(),
          variant: 'primary'
        },
        {
          label: 'Check VPN Status',
          action: () => {
            // You could open a VPN status page or show instructions
            alert('Please check your VPN connection:\n1. Ensure VPN client is running\n2. Connect to the corporate network\n3. Verify you can access other internal resources');
          },
          variant: 'secondary'
        }
      ]
    };
  }

  // Network timeout errors
  if (errorMessage.includes('timeout') || errorMessage.includes('ETIMEDOUT')) {
    return {
      type: 'network',
      title: 'SAP Connection Timeout',
      message: 'The connection to SAP server timed out. This could be due to network issues or server overload.',
      suggestions: [
        'Check your internet connection',
        'Try again in a few minutes',
        'Contact IT support if the issue persists',
        'Verify VPN connection is stable'
      ],
      actions: [
        {
          label: 'Retry Now',
          action: () => window.location.reload(),
          variant: 'primary'
        }
      ]
    };
  }

  // Authentication errors
  if (errorMessage.includes('401') || errorMessage.includes('Unauthorized') || errorMessage.includes('authentication')) {
    return {
      type: 'authentication',
      title: 'SAP Authentication Failed',
      message: 'Invalid credentials or authentication error when connecting to SAP.',
      suggestions: [
        'Verify SAP username and password are correct',
        'Check if your SAP account is active',
        'Contact IT support to reset credentials',
        'Ensure you have proper SAP access permissions'
      ],
      actions: [
        {
          label: 'Contact IT Support',
          action: () => {
            // You could open a support ticket or email
            window.open('mailto:it-support@company.com?subject=SAP Authentication Issue', '_blank');
          },
          variant: 'primary'
        }
      ]
    };
  }

  // HTTP errors
  if (errorMessage.includes('HTTP') && errorMessage.includes('5')) {
    return {
      type: 'connection',
      title: 'SAP Server Error',
      message: 'The SAP server is experiencing issues. This is a server-side problem.',
      suggestions: [
        'Try again in a few minutes',
        'Check SAP server status with IT support',
        'Verify the SAP endpoint is correct',
        'Contact system administrator'
      ],
      actions: [
        {
          label: 'Retry Later',
          action: () => {
            setTimeout(() => window.location.reload(), 30000); // Retry in 30 seconds
          },
          variant: 'primary'
        }
      ]
    };
  }

  // Data parsing errors
  if (errorMessage.includes('JSON') || errorMessage.includes('parse') || errorMessage.includes('format')) {
    return {
      type: 'data',
      title: 'SAP Data Format Error',
      message: 'The data received from SAP is not in the expected format.',
      suggestions: [
        'SAP API may have changed its response format',
        'Contact development team to update data mapping',
        'Check SAP API documentation',
        'Try again to see if it was a temporary issue'
      ],
      actions: [
        {
          label: 'Report Issue',
          action: () => {
            // You could open a bug report or contact form
            const bugReport = `SAP Data Format Error\n\nError: ${errorMessage}\n\nTime: ${new Date().toISOString()}\n\nPlease investigate the SAP API response format.`;
            navigator.clipboard.writeText(bugReport);
            alert('Bug report copied to clipboard. Please send it to the development team.');
          },
          variant: 'primary'
        }
      ]
    };
  }

  // Connection refused
  if (errorMessage.includes('Connection refused') || errorMessage.includes('ECONNREFUSED')) {
    return {
      type: 'connection',
      title: 'SAP Server Unreachable',
      message: 'Cannot connect to the SAP server. The server may be down or the port is blocked.',
      suggestions: [
        'Check if SAP server is running',
        'Verify VPN connection',
        'Check firewall settings',
        'Contact IT support'
      ],
      actions: [
        {
          label: 'Check Server Status',
          action: () => {
            // You could ping the server or check status page
            alert('Please contact IT support to check SAP server status.');
          },
          variant: 'primary'
        }
      ]
    };
  }

  // Generic error
  return {
    type: 'unknown',
    title: 'SAP Integration Error',
    message: `An unexpected error occurred while connecting to SAP: ${errorMessage}`,
    suggestions: [
      'Try refreshing the page',
      'Check your network connection',
      'Contact IT support if the issue persists',
      'Verify VPN connection'
    ],
    actions: [
      {
        label: 'Refresh Page',
        action: () => window.location.reload(),
        variant: 'primary'
      },
      {
        label: 'Contact Support',
        action: () => {
          const supportInfo = `SAP Integration Error\n\nError: ${errorMessage}\n\nTime: ${new Date().toISOString()}\n\nPlease help resolve this issue.`;
          navigator.clipboard.writeText(supportInfo);
          alert('Support information copied to clipboard. Please send it to IT support.');
        },
        variant: 'secondary'
      }
    ]
  };
};

export const formatSAPErrorMessage = (error: SAPError): string => {
  const suggestionsText = error.suggestions.map((suggestion, index) => 
    `${index + 1}. ${suggestion}`
  ).join('\n');

  return `${error.message}\n\nSuggestions:\n${suggestionsText}`;
};

export const getSAPErrorIcon = (type: SAPError['type']): string => {
  switch (type) {
    case 'connection':
      return '🔌';
    case 'authentication':
      return '🔐';
    case 'data':
      return '📊';
    case 'network':
      return '🌐';
    case 'unknown':
    default:
      return '⚠️';
  }
};
