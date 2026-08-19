# Feature Specifications - December 12, 2025 - Major Fixes

This document provides clear, unambiguous specifications for implementing critical fixes related to order validation and scale locking. These are major fixes that require high precision and full focus, as they affect the core order validation cycle functionality.

---

## Feature 1: Fix Order Validation Cycle and Baseline Tracking

### Overview
The order validation cycle is not working properly. The system should track baseline values from scales for each product version, monitor deltas (incremental changes), and update the current value in validation progress. Currently, baselines are not showing, deltas are not being tracked when values are added in SQL Server, and the validation progress is not updating correctly.

### Current Issues

1. **Baseline Values Not Showing**:
   - Baseline values for scales are not being displayed in Order Progress Details
   - System is not capturing or storing baseline values when an order starts
   - Baseline values should represent the initial scale readings for each product version

2. **Deltas Not Tracking**:
   - When values are added/updated in SQL Server, the system is not calculating or displaying deltas
   - Deltas represent the incremental change from baseline to current value
   - Without delta tracking, the system cannot determine progress toward target

3. **Current Value Not Updating**:
   - Current value in validation progress is not being updated when scale values change
   - The system should continuously monitor scale values and update the current value
   - This prevents accurate progress calculation

4. **Order Validation Cycle Not Working**:
   - The complete validation cycle is broken, preventing proper order validation
   - The cycle should: capture baseline → track deltas → update current value → compare to target → validate completion

### Required Changes

#### 1. Baseline Capture and Display

**Problem**: Baseline values for scales are not being captured or displayed when an order starts.

**Required Solution**:
- When an order starts validation, capture the current scale readings as baseline values
- Store baseline values for each scale associated with the order
- Display baseline values clearly in Order Progress Details
- Baseline should be captured once when order validation begins
- Baseline values should be associated with the specific product version

**Implementation Requirements**:
- Capture baseline from scale readings at the moment order validation starts
- Store baseline values in the database (linked to order and product version)
- Display baseline in Order Progress Details with clear labeling
- Baseline should show the initial scale reading for each scale used by the order
- If multiple scales are used (scale1, scale2, scale3), capture baseline for each

**Expected Result**:
- Baseline values are captured when order validation starts
- Baseline values are stored in database
- Baseline values are clearly displayed in Order Progress Details
- Each scale used by the order has its baseline value shown

#### 2. Delta Calculation and Tracking

**Problem**: Deltas (incremental changes from baseline) are not being calculated or displayed when values change in SQL Server.

**Required Solution**:
- Continuously monitor scale values from SQL Server
- Calculate delta as: `delta = current_scale_value - baseline_value`
- Display deltas in real-time in Order Progress Details
- Update deltas whenever scale values change
- Track deltas for each scale individually

**Implementation Requirements**:
- Poll or monitor SQL Server for scale value changes
- Calculate delta for each scale: `delta = current_value - baseline`
- Update delta values in real-time or near real-time
- Display deltas in Order Progress Details
- Show positive deltas (increases) and handle negative deltas appropriately
- Delta should reflect the total change since baseline was captured

**Expected Result**:
- Deltas are calculated correctly: `delta = current - baseline`
- Deltas update automatically when scale values change in SQL Server
- Deltas are displayed in Order Progress Details
- Each scale shows its individual delta value
- Delta tracking works continuously throughout order validation

#### 3. Current Value Updates

**Problem**: Current value in validation progress is not updating when scale values change.

**Required Solution**:
- Continuously monitor scale values from SQL Server
- Update current value in validation progress whenever scale values change
- Current value should reflect the latest reading from scales
- Update should happen automatically without manual refresh

**Implementation Requirements**:
- Poll SQL Server for latest scale values at regular intervals (e.g., every few seconds)
- Update current value in the database when new scale values are detected
- Update current value display in Order Progress Details UI
- Ensure updates happen in real-time or near real-time
- Current value should be the sum of all relevant scale values for the order

**Expected Result**:
- Current value updates automatically when scale values change in SQL Server
- Current value is displayed correctly in validation progress
- Updates happen without requiring manual page refresh
- Current value accurately reflects the latest scale readings

#### 4. Complete Order Validation Cycle

**Problem**: The order validation cycle is not working properly, preventing accurate validation.

**Required Solution**:
- Implement complete validation cycle: Baseline → Delta Tracking → Current Value → Progress Calculation → Target Comparison → Validation
- Ensure all components work together correctly
- Validation should complete when current value reaches or exceeds target

**Validation Cycle Steps**:
1. **Capture Baseline**: When order starts, capture initial scale readings as baseline
2. **Track Deltas**: Continuously calculate and display deltas as scale values change
3. **Update Current Value**: Continuously update current value from scale readings
4. **Calculate Progress**: Progress = (current_value / target_value) * 100
5. **Compare to Target**: Check if current_value >= target_value
6. **Validate Completion**: When target is reached, mark order as validated

**Implementation Requirements**:
- Ensure baseline capture happens at the right time (when order validation starts)
- Ensure delta calculation happens continuously
- Ensure current value updates happen continuously
- Ensure progress calculation uses current value and target
- Ensure validation completion triggers when target is reached
- All steps must work together seamlessly

**Expected Result**:
- Complete validation cycle works end-to-end
- Baseline is captured correctly
- Deltas track correctly
- Current value updates correctly
- Progress calculates correctly
- Validation completes when target is reached
- All components work together as a cohesive system

### Implementation Approach

1. **Baseline Capture**:
   - Identify when order validation starts
   - Query current scale values from SQL Server at that moment
   - Store baseline values in database
   - Display baseline in Order Progress Details

2. **Delta Tracking**:
   - Set up polling or real-time monitoring of scale values from SQL Server
   - Calculate delta: `current_value - baseline_value`
   - Store delta values
   - Display deltas in Order Progress Details

3. **Current Value Updates**:
   - Set up continuous monitoring of scale values
   - Update current value in database when values change
   - Update current value display in UI
   - Ensure updates happen frequently enough for real-time feel

4. **Validation Cycle Integration**:
   - Ensure all components are connected
   - Test complete cycle from start to completion
   - Verify baseline → delta → current → progress → validation flow
   - Ensure error handling for each step

### Expected Result

After implementation:
- **Baseline Values**: Captured when order starts and displayed in Order Progress Details
- **Delta Tracking**: Deltas calculated and displayed in real-time as scale values change
- **Current Value**: Updates automatically when scale values change in SQL Server
- **Validation Cycle**: Complete cycle works correctly from baseline capture to validation completion
- **Progress Calculation**: Accurate progress based on current value vs target
- **Real-time Updates**: All values update automatically without manual refresh

### Testing Checklist
- [ ] Baseline values are captured when order validation starts
- [ ] Baseline values are stored in database correctly
- [ ] Baseline values are displayed in Order Progress Details
- [ ] Deltas are calculated correctly: `delta = current - baseline`
- [ ] Deltas update automatically when scale values change in SQL Server
- [ ] Deltas are displayed in Order Progress Details
- [ ] Current value updates automatically when scale values change
- [ ] Current value is displayed correctly in validation progress
- [ ] Progress calculation uses current value: `(current / target) * 100`
- [ ] Validation completes when current value >= target value
- [ ] Complete validation cycle works end-to-end
- [ ] All updates happen in real-time or near real-time
- [ ] No manual refresh required for updates
- [ ] Multiple scales are handled correctly (scale1, scale2, scale3)
- [ ] Baseline, delta, and current values work for each scale individually

---

## Feature 2: Scale Locking for Duplicated Product Versions and Scales

### Overview
When multiple orders have the same product version or use the same scales, the system must lock those scales and follow priority logic. Scales should be locked when duplicated product versions are in the queue, and the same priority logic should apply when the same scales are used by different orders. This prevents conflicts and ensures orders are processed in the correct sequence.

### Current Issues

1. **Scale Locking Not Working for Duplicated Product Versions**:
   - When multiple orders have the same product version, scales are not being locked
   - Orders with same product version can conflict when trying to use the same scales
   - Priority logic is not being applied correctly

2. **Scale Locking Not Working for Duplicated Scales**:
   - When different orders use the same scales, those scales are not being locked
   - Multiple orders can try to use the same scales simultaneously
   - This causes conflicts and incorrect validation

3. **Priority Logic Not Applied**:
   - When scales are locked, priority should determine which order gets access
   - Priority should follow order ID or drag-and-drop order
   - Currently, priority logic is not being enforced for scale locking

### Required Changes

#### 1. Scale Locking for Duplicated Product Versions

**Problem**: When multiple orders have the same product version, scales are not locked, causing conflicts.

**Required Solution**:
- When an order with a product version starts, check if other orders have the same product version
- If duplicate product versions exist, lock the scales used by the highest priority order
- Lower priority orders with the same product version must wait
- Scales remain locked until the highest priority order completes
- When highest priority order completes, next priority order gets access to scales

**Priority Logic**:
- Priority should be determined by order ID (lower ID = higher priority)
- OR priority should follow drag-and-drop order (if drag-and-drop is implemented)
- The order with highest priority (lowest ID or first in drag order) gets scale access first
- Other orders with same product version wait in queue

**Implementation Requirements**:
- Detect when multiple orders have the same product version
- Identify which scales are used by orders with that product version
- Lock those scales for the highest priority order
- Block lower priority orders from accessing locked scales
- Release scales when highest priority order completes
- Assign scales to next priority order when scales are released
- Display lock status in UI (which order has scales locked)

**Expected Result**:
- When orders have duplicate product versions, scales are locked
- Highest priority order gets access to scales first
- Lower priority orders wait until scales are released
- Scales are released when highest priority order completes
- Next priority order gets access automatically
- Lock status is visible in UI

#### 2. Scale Locking for Duplicated Scales

**Problem**: When different orders use the same scales, those scales are not locked, causing conflicts.

**Required Solution**:
- When an order starts and uses specific scales, check if other orders are using the same scales
- If duplicate scales are detected, lock those scales for the highest priority order
- Lower priority orders using the same scales must wait
- Scales remain locked until the highest priority order completes
- Same priority logic applies as for duplicated product versions

**Priority Logic**:
- Same priority logic as duplicated product versions
- Priority determined by order ID (lower ID = higher priority)
- OR priority follows drag-and-drop order
- Highest priority order gets scale access first
- Other orders wait in queue

**Implementation Requirements**:
- Detect when multiple orders use the same scales (scale1, scale2, scale3)
- Identify which orders are using the same scales
- Lock those scales for the highest priority order
- Block lower priority orders from accessing locked scales
- Release scales when highest priority order completes
- Assign scales to next priority order when scales are released
- Display lock status in UI

**Expected Result**:
- When orders use duplicate scales, scales are locked
- Highest priority order gets access to scales first
- Lower priority orders wait until scales are released
- Scales are released when highest priority order completes
- Next priority order gets access automatically
- Lock status is visible in UI
- Same priority logic applies as for duplicated product versions

#### 3. Unified Priority Logic

**Problem**: Priority logic needs to be consistent for both duplicated product versions and duplicated scales.

**Required Solution**:
- Use the same priority logic for both scenarios
- Priority should be based on order ID (lower ID = higher priority)
- OR priority should follow drag-and-drop order if implemented
- Priority should be clearly visible in UI
- Priority should determine scale access order

**Implementation Requirements**:
- Implement consistent priority calculation
- Use order ID for priority (lower ID = higher priority = 1, 2, 3, etc.)
- OR use drag-and-drop order for priority if drag-and-drop is implemented
- Display priority clearly in orders table
- Use priority to determine which order gets scale access
- Update priority when orders are reordered (if drag-and-drop is used)

**Expected Result**:
- Priority is calculated consistently
- Priority is clearly displayed in UI
- Priority determines scale access order
- Same priority logic works for both duplicated product versions and duplicated scales
- Priority updates correctly when orders are reordered

#### 4. Scale Lock Status and Queue Management

**Problem**: Users need to see which scales are locked and which orders are waiting.

**Required Solution**:
- Display scale lock status in UI
- Show which order currently has scales locked
- Show which orders are waiting for scales
- Display priority order clearly
- Provide visual indicators for locked scales

**Implementation Requirements**:
- Display lock status for each scale
- Show which order ID has the lock
- Show queue of waiting orders with their priorities
- Use visual indicators (colors, icons) to show lock status
- Update lock status in real-time as orders complete

**Expected Result**:
- Lock status is visible in UI
- Users can see which order has scales locked
- Users can see which orders are waiting
- Priority order is clearly displayed
- Visual indicators make lock status clear

### Implementation Approach

1. **Detect Duplicates**:
   - Check for duplicate product versions when order starts
   - Check for duplicate scales when order starts
   - Identify all orders affected by duplicates

2. **Calculate Priority**:
   - Determine priority for each order (by ID or drag order)
   - Sort orders by priority
   - Highest priority order gets access first

3. **Lock Scales**:
   - Lock scales for highest priority order
   - Block lower priority orders from accessing locked scales
   - Store lock information in database

4. **Manage Queue**:
   - Maintain queue of orders waiting for scales
   - Release scales when highest priority order completes
   - Assign scales to next priority order
   - Update queue status

5. **Display Status**:
   - Show lock status in UI
   - Show which order has lock
   - Show waiting orders
   - Update status in real-time

### Expected Result

After implementation:
- **Scale Locking for Duplicated Product Versions**: Scales are locked when multiple orders have the same product version
- **Scale Locking for Duplicated Scales**: Scales are locked when multiple orders use the same scales
- **Priority Logic**: Consistent priority logic applied to both scenarios
- **Queue Management**: Orders wait in queue based on priority
- **Lock Status Display**: Lock status is clearly visible in UI
- **Automatic Release**: Scales are automatically released and assigned to next priority order
- **Conflict Prevention**: No conflicts occur when multiple orders need the same scales

### Testing Checklist
- [ ] Scales are locked when multiple orders have the same product version
- [ ] Highest priority order gets access to scales first
- [ ] Lower priority orders wait until scales are released
- [ ] Scales are locked when multiple orders use the same scales
- [ ] Same priority logic applies to both duplicated product versions and duplicated scales
- [ ] Priority is calculated correctly (by order ID or drag order)
- [ ] Priority is clearly displayed in UI
- [ ] Scales are released when highest priority order completes
- [ ] Next priority order gets access automatically when scales are released
- [ ] Lock status is visible in UI
- [ ] Queue of waiting orders is displayed
- [ ] Visual indicators show lock status clearly
- [ ] No conflicts occur when multiple orders need same scales
- [ ] System handles multiple scales correctly (scale1, scale2, scale3)
- [ ] System handles orders with different combinations of scales
- [ ] Priority updates correctly when orders are reordered (if drag-and-drop is used)

---

## Notes for Implementation

- **Critical Priority**: These are major fixes that affect core functionality - order validation cycle and scale locking are critical for system operation
- **High Precision Required**: Both features require high precision implementation - test thoroughly at each step
- **Real-time Updates**: Ensure all updates happen in real-time or near real-time for proper functionality
- **Database Consistency**: Ensure database state is consistent - baseline, deltas, current values, and locks must be accurate
- **Error Handling**: Implement robust error handling for each component
- **Testing**: Test complete cycles end-to-end, not just individual components
- **Visual Feedback**: Provide clear visual feedback for all states (baseline, deltas, current value, locks, queue)
- **Performance**: Ensure polling/monitoring doesn't impact system performance
- **Scalability**: Solution should work with multiple orders and multiple scales simultaneously

