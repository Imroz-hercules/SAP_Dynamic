# Role-Based Access Control for Data Sync Interval Settings

This document describes the implementation of role-based access control for managing data frequency sync interval settings in the Hercules SFMS system.

## Overview

The system now includes a comprehensive role-based access control (RBAC) system that controls who can view and modify sync interval settings. This ensures that only authorized personnel can change critical system synchronization parameters.

## Database Schema

### Tables Created

1. **users** - Stores user account information
2. **roles** - Defines different access levels (admin, manager, user, guest)
3. **user_roles** - Many-to-many relationship between users and roles
4. **sync_interval_settings** - Stores sync interval configurations

### Key Fields

#### Users Table
- `id` - Primary key
- `username` - Unique username
- `email` - User email address
- `password_hash` - Bcrypt hashed password
- `full_name` - User's full name
- `is_active` - Account status

#### Roles Table
- `id` - Primary key
- `name` - Role name (admin, manager, user, guest)
- `description` - Role description
- `permissions` - JSON string of permissions

#### Sync Interval Settings Table
- `id` - Primary key
- `sync_type` - Type of sync (raw_data, kpi, process_orders)
- `interval_minutes` - Sync interval in minutes
- `is_enabled` - Whether sync is enabled
- `last_sync` - Timestamp of last sync
- `next_sync` - Timestamp of next scheduled sync
- `created_by` - User who created the setting
- `updated_by` - User who last updated the setting

## Role Permissions Matrix

| Permission | Admin | Manager | User | Guest |
|------------|-------|---------|------|-------|
| view_sync_interval | ✅ | ✅ | ✅ | ❌ |
| change_sync_interval | ✅ | ✅ | ❌ | ❌ |
| view_all_data | ✅ | ✅ | ❌ | ❌ |
| manage_users | ✅ | ❌ | ❌ | ❌ |
| system_admin | ✅ | ❌ | ❌ | ❌ |

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user info
- `GET /api/auth/users` - List users (admin only)
- `GET /api/auth/roles` - List available roles
- `PUT /api/auth/users/{id}/roles` - Update user roles (admin only)

### Sync Interval Management
- `GET /api/sync-interval/settings` - Get all sync settings (requires view permission)
- `GET /api/sync-interval/settings/{type}` - Get specific sync setting
- `PUT /api/sync-interval/settings/{type}` - Update sync setting (requires change permission)
- `POST /api/sync-interval/settings/{type}/test` - Test sync setting
- `POST /api/sync-interval/settings` - Create new sync setting (manager/admin only)

## Frontend Implementation

### Components Created
1. **LoginForm** - User authentication form
2. **AuthContext** - React context for authentication state
3. **AuthDemo** - Demonstration page showing role-based access
4. **Admin.tsx** - Updated with sync interval controls and role checks

### Key Features
- JWT token-based authentication
- Automatic token inclusion in API requests
- Role-based UI visibility
- Permission-based component rendering
- Real-time permission checking

## Setup Instructions

### 1. Database Setup
```bash
cd C3381_Sap/backend
python create_user_roles_tables.py
```

This script will:
- Create all necessary tables
- Seed initial roles (admin, manager, user, guest)
- Create default admin user (username: admin, password: admin123)
- Create default sync interval settings

### 2. Backend Configuration
The backend automatically registers the new blueprints:
- `auth_bp` - Authentication routes
- `sync_interval_bp` - Sync interval management routes

### 3. Frontend Integration
The frontend includes:
- Updated `queryClient.ts` with JWT token support
- `AuthContext` for state management
- Role-based UI components

## Usage Examples

### Login as Admin
```javascript
// Default admin credentials
username: "admin"
password: "admin123"
```

### Check User Permissions
```javascript
const { hasPermission, hasRole } = useAuth()

// Check specific permission
if (hasPermission('change_sync_interval')) {
  // Show sync interval controls
}

// Check role
if (hasRole('admin')) {
  // Show admin-only features
}
```

### Update Sync Interval
```javascript
// Only users with 'change_sync_interval' permission can do this
const response = await apiRequest('PUT', '/api/sync-interval/settings/raw_data', {
  interval_minutes: 120,
  is_enabled: true
})
```

## Security Features

1. **JWT Authentication** - Secure token-based authentication
2. **Bcrypt Password Hashing** - Secure password storage
3. **Role-Based Permissions** - Granular permission system
4. **API Route Protection** - Decorators for route-level security
5. **Frontend Permission Checks** - UI-level access control

## Default Sync Settings

The system comes with three default sync interval settings:

1. **Raw Data Sync** - 60 minutes (1 hour)
   - Syncs data from ASMReporting_5 to SAP
   
2. **KPI Data Sync** - 30 minutes
   - Syncs milling and packing KPIs to SAP
   
3. **Process Orders Sync** - 180 minutes (3 hours)
   - Syncs process orders from SAP

## Testing the Implementation

1. **Start the backend server**
2. **Navigate to the AuthDemo page** to test authentication
3. **Login with admin credentials** (admin/admin123)
4. **Navigate to Admin Panel** to test sync interval controls
5. **Try different user roles** to verify access restrictions

## Future Enhancements

1. **User Management UI** - Admin interface for managing users and roles
2. **Audit Logging** - Track who changed sync settings and when
3. **Scheduled Sync Jobs** - Automatic sync based on interval settings
4. **Email Notifications** - Alerts for sync failures or permission changes
5. **Role Hierarchy** - More granular role system with inheritance

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check if JWT secret is consistent
   - Verify token is being sent in Authorization header

2. **Permission Denied**
   - Verify user has correct role assigned
   - Check permission matrix for role capabilities

3. **Database Connection Issues**
   - Ensure PostgreSQL is running
   - Verify connection string in database.py

4. **Frontend Not Loading**
   - Check if auth token is stored in localStorage
   - Verify API base URL configuration

### Logs and Debugging

The system includes comprehensive logging:
- Authentication events
- Permission checks
- Sync interval changes
- Database operations

Check the backend logs for detailed error information.
