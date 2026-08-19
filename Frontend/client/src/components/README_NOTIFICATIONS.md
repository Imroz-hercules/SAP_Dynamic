# Professional Notification System

This document describes the new professional notification system implemented for the Hercules SFMS application.

## Overview

The notification system provides a modern, professional way to display messages to users with:
- **Professional Design**: Modern popup notifications with gradients and animations
- **Multiple Types**: Success, Error, Warning, and Info notifications
- **Actionable Content**: Buttons for user actions within notifications
- **Auto-dismiss**: Configurable auto-dismiss timers
- **Accessibility**: Proper ARIA labels and keyboard navigation
- **Responsive**: Works on all screen sizes

## Components

### NotificationProvider
Wraps the entire application to provide notification context.

```tsx
import { NotificationProvider } from './components/NotificationSystem';

function App() {
  return (
    <NotificationProvider>
      {/* Your app content */}
    </NotificationProvider>
  );
}
```

### useNotification Hook
Hook to show notifications from any component.

```tsx
import { useNotificationHelpers } from './components/NotificationSystem';

function MyComponent() {
  const { showSuccess, showError, showWarning, showInfo } = useNotificationHelpers();

  const handleClick = () => {
    showSuccess('Success!', 'Operation completed successfully.');
  };
}
```

## Notification Types

### Success Notifications
Green gradient with checkmark icon. Auto-dismisses after 4 seconds.

```tsx
showSuccess(
  'Operation Successful',
  'The SAP synchronization completed successfully.',
  4000 // Optional duration
);
```

### Error Notifications
Red gradient with X icon. Does not auto-dismiss by default.

```tsx
showError(
  'SAP Connection Failed',
  'Unable to connect to SAP server.',
  0, // No auto-dismiss
  [ // Optional actions
    {
      label: 'Retry',
      action: () => retryConnection(),
      variant: 'primary'
    }
  ]
);
```

### Warning Notifications
Yellow gradient with warning icon. Auto-dismisses after 5 seconds.

```tsx
showWarning(
  'Data Sync Warning',
  'Some orders could not be synchronized.',
  5000
);
```

### Info Notifications
Blue gradient with info icon. Auto-dismisses after 4 seconds.

```tsx
showInfo(
  'SAP Maintenance',
  'Scheduled maintenance from 2-4 AM.',
  6000
);
```

## SAP Error Handling

The system includes specialized SAP error handling with actionable suggestions:

### Connection Errors
- **DNS Resolution**: VPN connection issues
- **Timeouts**: Network connectivity problems
- **Connection Refused**: Server unavailable

### Authentication Errors
- **401 Unauthorized**: Invalid credentials
- **403 Forbidden**: Insufficient permissions

### Data Errors
- **JSON Parse Errors**: API response format issues
- **Validation Errors**: Data format mismatches

## Features

### Professional Design
- Gradient backgrounds with proper contrast
- Smooth animations and transitions
- Hover effects and scaling
- Modern typography and spacing

### User Experience
- Non-blocking notifications
- Stack multiple notifications
- Click to dismiss
- Action buttons for quick responses

### Accessibility
- ARIA labels for screen readers
- Keyboard navigation support
- High contrast colors
- Focus management

### Responsive Design
- Mobile-friendly sizing
- Touch-friendly buttons
- Adaptive layouts
- Proper spacing on all devices

## Usage Examples

### Basic Success
```tsx
showSuccess('Success!', 'Data saved successfully.');
```

### Error with Actions
```tsx
showError(
  'Upload Failed',
  'File could not be uploaded.',
  0,
  [
    {
      label: 'Retry',
      action: () => retryUpload(),
      variant: 'primary'
    },
    {
      label: 'Cancel',
      action: () => cancelUpload(),
      variant: 'secondary'
    }
  ]
);
```

### SAP Integration
```tsx
try {
  await syncWithSAP();
  showSuccess('SAP Sync Complete', '15 orders imported successfully.');
} catch (error) {
  const sapError = parseSAPError(error);
  showError(sapError.title, sapError.message, 0, sapError.actions);
}
```

## Customization

### Styling
The notification system uses Tailwind CSS classes and can be customized by modifying the component styles.

### Timing
- Success: 4 seconds (default)
- Error: No auto-dismiss (default)
- Warning: 5 seconds (default)
- Info: 4 seconds (default)

### Actions
Actions support three variants:
- `primary`: Main action (blue)
- `secondary`: Secondary action (gray)
- `danger`: Destructive action (red)

## Best Practices

1. **Use appropriate types**: Success for positive outcomes, Error for failures, etc.
2. **Provide actionable content**: Include buttons for user actions when possible
3. **Keep messages concise**: Clear, brief descriptions
4. **Don't spam**: Avoid showing too many notifications at once
5. **Handle errors gracefully**: Use the SAP error handler for consistent error messages

## Integration

The notification system is fully integrated with:
- SAP error handling
- Loading states
- User feedback
- Error recovery
- Action buttons

This provides a professional, user-friendly experience for all SAP operations and system interactions.
