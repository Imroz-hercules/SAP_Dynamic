# Feature Specifications - December 10, 2025

This document provides clear, unambiguous specifications for implementing features requested on December 10, 2025. Each feature is documented with precise requirements and implementation details to ensure error-free execution.

---

## Feature 1: SAP Data Sync Interval Configuration from Settings

### Overview
The interval for receiving/pulling data from SAP should be configurable from the Settings page. This is the sync interval that controls how often the system fetches new orders and data from SAP. The interval should not be hardcoded and must be manageable through the Settings interface.

### Current Issues
- The SAP data sync interval (for receiving data from SAP) may be hardcoded in the codebase
- The interval might not be configurable from the Settings interface
- Users cannot adjust how frequently the system pulls data from SAP without code changes

### Required Changes

#### 1. Verify Current SAP Data Sync Interval Configuration
- **Action**: Check where the SAP data sync interval (for receiving/pulling data from SAP) is currently configured
- **What to Check**:
  - Any hardcoded interval values for SAP data pull operations
  - Environment variables that define the sync interval
  - Scheduler configurations that control SAP data fetching
  - Any configuration files that contain the interval definition

#### 2. Ensure SAP Data Sync Interval Uses Settings Database
- **Action**: Make sure the SAP data sync interval (for receiving data) is read from the Settings database table
- **Requirements**:
  - The scheduler that pulls data from SAP should query the Settings database table for the interval value
  - No hardcoded interval should exist for SAP data sync
  - Environment variables should only be used as fallback defaults when Settings are not available
  - The Settings database should be the single source of truth for this interval

#### 3. Settings UI Requirements
- **Action**: Ensure the Settings page provides an interface for managing the SAP data sync interval
- **Required Features**:
  - Display the current SAP data sync interval value
  - Allow editing of the interval value (in minutes or hours)
  - Show clear label: "SAP Data Sync Interval" or "SAP Order Pull Interval"
  - Include description explaining this controls how often data is received from SAP
  - Display last sync time
  - Display next scheduled sync time (optional but helpful)
  - Include validation to prevent invalid interval values (e.g., minimum 1 minute, maximum reasonable limit)
  - Provide a save/update button

#### 4. Backend API Requirements
- **Action**: Ensure the SAP data sync interval can be retrieved and updated via API
- **Required Endpoints**:
  - Get the current SAP data sync interval setting
  - Update the SAP data sync interval setting


### Implementation Approach

1. **Audit Phase**:
   - Search the codebase for any hardcoded SAP data sync interval values
   - Identify the scheduler or service that performs SAP data pulls
   - Document where the interval is currently defined

2. **Refactoring Phase**:
   - Update the SAP data pull scheduler to read the interval value from the Settings database
   - Remove any hardcoded interval values
   - Implement fallback logic to use environment variables only when Settings are unavailable
   - Ensure the Settings database table has a field for this interval

3. **Database Verification**:
   - Verify that the Settings database table has a field for the SAP data sync interval
   - Ensure the field supports interval values (in minutes or hours)
   - Check that a default value is set appropriately
   - Verify database indexes if needed for performance

4. **UI Enhancement**:
   - Add or update the Settings page to display the SAP data sync interval setting
   - Create a form field for editing the interval value
   - Add proper validation (minimum/maximum values)
   - Include helpful description text
   - Show current value clearly

5. **Testing Phase**:
   - Test updating the interval from the Settings interface
   - Verify that the scheduler picks up the new value
   - Test with different interval values
   - Verify fallback behavior when Settings are not available
   - Test authorization and access control

### Expected Result

After implementation:
- **Configurable Interval**: The SAP data sync interval (for receiving data from SAP) is configurable from the Settings page
- **No Hardcoded Values**: No hardcoded interval exists for SAP data sync
- **Single Source of Truth**: The Settings database is the authoritative source for the sync interval
- **Dynamic Updates**: The scheduler reads from Settings and uses the updated value
- **Clear UI**: Settings page displays and allows editing of the SAP data sync interval
- **Proper API**: The interval can be managed via API endpoints with proper authorization

### Testing Checklist
- [ ] SAP data sync interval is visible in Settings page
- [ ] Interval can be updated from Settings interface
- [ ] Scheduler uses value from Settings (not hardcoded value)
- [ ] Changes to Settings are reflected in scheduler behavior
- [ ] Fallback to environment variables works correctly when Settings unavailable
- [ ] No hardcoded interval remains in the codebase
- [ ] API endpoints work correctly for retrieving and updating the setting
- [ ] Settings UI displays current value correctly
- [ ] Validation prevents invalid interval values
- [ ] Last sync time is displayed correctly (if implemented)
- [ ] Authorization is properly enforced on API endpoints

---

## Feature 2: Order Validation Page UI Layout Improvements

### Overview
The Order Validation page needs UI layout improvements to make it more space-efficient and better organized. The focus should be on making the orders table visible without scrolling, as the primary user goal is to view and validate orders.

### Current Issues
1. **KPI Cards Layout**: The summary cards (Total Orders, In Progress, Validated, Error Log, Offline Orders) are currently unorganized and take up two rows, wasting vertical space
2. **Auto Validation Control Section**: The Auto Validation Control panel with status and buttons is taking too much vertical space, requiring users to scroll to see the orders table
3. **Table Column Alignment**: There is misalignment between table column headers and the data cells underneath them, making the table look unprofessional

### Required Changes

#### 2.1. Fix KPI Cards Layout - Single Row Dynamic Alignment

**Problem Description**:
- The KPI summary cards are currently displayed in a grid layout that wraps to multiple rows on different screen sizes
- This takes up excessive vertical space, pushing the orders table down
- Cards are not evenly distributed and look unorganized

**Required Solution**:
- Display all KPI cards (Total Orders, In Progress, Validated, Error Log, Offline Orders) in a single horizontal row
- Cards should be evenly distributed across the available width
- Cards should dynamically adjust their size to fit in one row on all screen sizes
- No wrapping to a second row should occur on any screen size
- Cards should shrink proportionally on smaller screens while maintaining readability

**Implementation Guidelines**:
- Use a flexbox layout instead of grid to ensure all cards stay in one row
- Apply equal flex distribution to all cards so they share the width evenly
- Reduce gaps and padding between cards to maximize space efficiency
- Ensure cards have minimum width constraints to prevent content overflow
- Consider reducing internal padding or font sizes within cards if needed to fit all cards
- Maintain responsive behavior so cards remain usable on smaller screens

**Expected Result**:
- All 5 KPI cards display in a single horizontal row
- Cards are evenly distributed and take equal width
- No cards wrap to a second row on any screen size
- Significantly less vertical space is used, allowing the orders table to be visible higher on the page
- Cards remain readable and functional on all screen sizes

#### 2.2. Compact Auto Validation Control Section

**Problem Description**:
- The Auto Validation Control section (showing status, description, and action buttons) is taking too much vertical space
- The section has large padding, large fonts, and verbose descriptions
- Users must scroll down to see the orders table, which is the main focus of the page

**Required Solution**:
- Make the Auto Validation Control section significantly more compact
- Reduce vertical space usage while maintaining all functionality
- Organize the layout more efficiently using horizontal space
- Keep status and buttons clearly visible but in a more condensed format

**Implementation Guidelines**:
- Reduce overall padding of the control panel container
- Reduce font sizes for headings and descriptions
- Use a more horizontal layout instead of stacked vertical elements
- Combine status indicator and text in a single line where possible
- Shorten status messages and use abbreviations where appropriate (e.g., "60s" instead of "every 60 seconds")
- Reduce button sizes and padding while keeping them clickable
- Hide detailed progress information by default (show on hover or in tooltips if needed)
- Use a single-row layout with status on the left and buttons on the right
- Remove unnecessary spacing and margins

**Expected Result**:
- Auto Validation Control section takes minimal vertical space (approximately 50-60% less than current)
- Status and buttons remain clearly visible and accessible
- All functionality is preserved
- Users can see the orders table without scrolling on standard screen sizes
- The section looks organized and tidy

#### 2.3. Fix Orders Table Column Alignment

**Problem Description**:
- Table column headers are not properly aligned with the data cells in the rows below
- This creates a visual misalignment that makes the table look unprofessional
- The misalignment can make it difficult to read data correctly

**Required Solution**:
- Ensure perfect alignment between all table column headers (`<th>` elements) and their corresponding data cells (`<td>` elements)
- All columns should have consistent alignment
- The table should look professional and organized

**Implementation Guidelines**:
- Ensure consistent padding values between headers and data cells
- Use fixed table layout to ensure consistent column widths
- Verify that all header cells and data cells use the same padding classes
- Ensure consistent text alignment within each column (left, center, or right as appropriate)
- Check that width constraints are consistent between headers and cells
- Verify that all rows have the same number of cells as there are headers
- Remove any inline styles or conflicting CSS that might cause misalignment
- Consider using explicit column width definitions if needed
- Ensure that any drag handles or special elements in cells don't affect alignment

**Common Causes to Check**:
- Different padding values between `<th>` and `<td>` elements
- Different width constraints or classes
- Text alignment differences
- Missing fixed table layout
- Inconsistent column structure (missing or extra cells in rows)
- Special elements (icons, buttons) affecting cell width

**Expected Result**:
- All table column headers align perfectly with data cells below them
- No visual misalignment is visible
- The table looks professional and well-organized
- Columns maintain consistent widths
- Text alignment is consistent within each column
- The table is easy to read and navigate

### Implementation Approach

1. **KPI Cards Layout Fix**:
   - Locate the KPI cards container in the Order Validation page
   - Change from grid layout to flexbox layout
   - Apply equal flex distribution to all cards
   - Adjust spacing and padding to fit all cards in one row
   - Test on various screen sizes to ensure no wrapping occurs

2. **Auto Validation Control Compaction**:
   - Locate the Auto Validation Control section
   - Reduce container padding and margins
   - Reduce font sizes for headings and text
   - Reorganize layout to be more horizontal
   - Reduce button sizes and spacing
   - Test that all functionality still works

3. **Table Alignment Fix**:
   - Locate the orders table structure
   - Verify padding consistency between headers and cells
   - Add fixed table layout if not present
   - Check text alignment consistency
   - Verify column structure matches between headers and rows
   - Test alignment visually in browser

4. **Overall Testing**:
   - Verify that the orders table is visible without scrolling on standard screens
   - Test responsive behavior on different screen sizes
   - Verify all functionality still works after layout changes
   - Check that the UI looks organized and professional
   - Ensure no console errors are introduced

### Expected Result

After implementation:
- **KPI Cards**: All 5 cards display in a single row, evenly distributed, taking minimal vertical space
- **Auto Validation Control**: Compact section that takes minimal vertical space while remaining functional
- **Orders Table**: Perfect alignment between headers and data cells, professional appearance
- **Overall UX**: Users can see the orders table immediately without scrolling, with the page focused on the primary task of order validation

### Testing Checklist
- [ ] All 5 KPI cards display in a single row on all screen sizes
- [ ] Cards are evenly distributed and don't wrap to a second row
- [ ] Cards remain readable and functional on small screens
- [ ] Auto Validation Control section is significantly more compact
- [ ] Status and buttons are clearly visible but take less space
- [ ] All Auto Validation Control functionality still works
- [ ] Orders table headers align perfectly with data cells
- [ ] No visual misalignment is visible in the table
- [ ] Orders table is visible without scrolling on standard screens (1920x1080, 1366x768)
- [ ] All existing functionality still works after layout changes
- [ ] Responsive behavior is correct on mobile, tablet, and desktop
- [ ] No console errors are introduced
- [ ] UI looks organized, tidy, and professional
- [ ] Theme support (light/dark mode) is maintained

---

## Notes for Implementation

- **Focus on UX**: The primary goal is to make the orders table visible without scrolling, as order validation is the main user task
- **Preserve Functionality**: All layout changes should maintain existing functionality - only modify visual presentation
- **Maintain Themes**: Ensure all changes work correctly in both light and dark themes
- **Test Responsively**: Verify that improvements work well on different screen sizes
- **Incremental Changes**: Make changes incrementally and test after each modification
- **Visual Verification**: Use browser developer tools to verify alignment and spacing
- **User-Centric**: Keep the focus on making the orders table easily accessible to users
