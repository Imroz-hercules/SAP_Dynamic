# Feature Specifications - December 12, 2024

This document provides clear, unambiguous specifications for implementing features from `Features+Fixes_Dec_12`. Each feature is documented with precise requirements, file locations, and implementation details to ensure error-free execution by AI agents.

---

## Feature 1: KPI Readings Page Layout Simplification

### Current State
- **File**: `Frontend/client/src/pages/hercules-sfms/KpiCalculations.tsx`
- **Current Layout**: 
  - Three tabs: "Milling", "Packing", "SCADA Readings"
  - When "Milling" tab is active: Shows Milling KPIs on left, "Packing KPIs Summary" on right
  - When "Packing" tab is active: Shows Packing KPIs on left, "Packing Summary" on right
  - When "SCADA Readings" tab is active: Shows SCADA readings data
- **Current State Variable**: `const [activeTab, setActiveTab] = useState('Milling');` (line 155)

### Required Changes

#### 1. Remove Tab Navigation
- **Action**: Remove all tab-related UI elements and state
- **Specific Changes**:
  - Remove `activeTab` state variable (line 155)
  - Remove `setActiveTab` function calls
  - Remove `TabButton` component usage (if present in the render)
  - Remove all conditional rendering based on `activeTab === 'Milling'`, `activeTab === 'Packing'`, `activeTab === 'SCADA Readings'`
  - Remove the tab navigation UI (the buttons/links that switch between tabs)

#### 2. Create Side-by-Side Layout
- **Action**: Display Milling KPIs on the left, Packing KPIs on the right, always visible
- **Layout Structure**:
  ```
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
    <!-- Left Column: Milling KPIs -->
    <div>...</div>
    
    <!-- Right Column: Packing KPIs -->
    <div>...</div>
  </div>
  ```
- **Specific Implementation**:
  - Use the existing Milling KPIs card structure (currently shown when `activeTab === 'Milling'`)
  - Use the existing Packing KPIs card structure (currently shown when `activeTab === 'Packing'`)
  - Both cards should be rendered simultaneously, side-by-side
  - Use responsive grid: `grid-cols-1` on mobile, `grid-cols-2` on medium screens and above

#### 3. Remove KPI Summary Sections
- **Action**: Remove all "KPI Summary", "Top Performers", "Areas for Improvement", "Packing Summary", "Production Metrics", and "Time Analysis" sections
- **Specific Sections to Remove**:
  - The card with heading "Packing KPIs Summary" (lines 703-773 in current code)
  - The card with heading "Packing Summary" (lines 809-880 in current code)
  - Any sections showing "Top Performers" or "Areas for Improvement"
  - Any sections showing "Production Metrics" or "Time Analysis"
- **What to Keep**:
  - Keep the Milling KPIs list (all KpiRow components showing individual KPI values)
  - Keep the Packing KPIs list (all KpiRow components showing individual KPI values)
  - Keep the Water Consumption section if it's part of Milling KPIs (lines 674-698)

#### 4. SCADA Readings Handling
- **Action**: SCADA Readings tab content should be removed from this page
- **Note**: SCADA Readings functionality should remain accessible via its own separate route/page (not part of this change)
- **Specific Change**: Remove the conditional block `{activeTab === 'SCADA Readings' && (...)}` entirely

### Implementation Steps

1. **Remove Tab State and Navigation**:
   - Delete line: `const [activeTab, setActiveTab] = useState('Milling');`
   - Remove all `TabButton` components or tab navigation UI
   - Remove all `activeTab === '...'` conditional checks

2. **Create Unified Layout**:
   - Replace all tab-based conditional rendering with a single `grid grid-cols-1 md:grid-cols-2 gap-6` container
   - Place Milling KPIs card in the left column
   - Place Packing KPIs card in the right column

3. **Remove Summary Cards**:
   - Delete the entire card containing "Packing KPIs Summary" (Top Performers/Areas for Improvement)
   - Delete the entire card containing "Packing Summary" (Production Metrics/Time Analysis)
   - Ensure only the KPI value lists remain

4. **Remove SCADA Tab Content**:
   - Delete the entire `{activeTab === 'SCADA Readings' && (...)}` block

5. **Verify Data Flow**:
   - Ensure `kpiData.milling_kpis` and `kpiData.packing_kpis` are still being fetched correctly
   - Ensure all KpiRow components for both Milling and Packing KPIs are displayed
   - Ensure Water Consumption section (if present) remains in Milling KPIs column

### Expected Result

After implementation:
- **No tabs visible** on the KPI Readings page
- **Two columns side-by-side**:
  - **Left column**: "Milling KPIs" heading, followed by list of all Milling KPI rows (Mill Throughput, Mill Time Efficiency, etc.), plus Water Consumption section if applicable
  - **Right column**: "Packing KPIs" heading, followed by list of all Packing KPI rows (Packing Line Capacity, Daily Packing Output, etc.)
- **No summary sections** (no Top Performers, Areas for Improvement, Production Metrics, Time Analysis)
- **Responsive design**: Stacks vertically on mobile, side-by-side on larger screens
- **SCADA Readings**: Not visible on this page (accessible elsewhere if needed)

### File to Modify
- `Frontend/client/src/pages/hercules-sfms/KpiCalculations.tsx`

### Testing Checklist
- [ ] Tabs are completely removed
- [ ] Milling KPIs display in left column
- [ ] Packing KPIs display in right column
- [ ] Both columns visible simultaneously
- [ ] No summary sections visible
- [ ] Layout is responsive (stacks on mobile, side-by-side on desktop)
- [ ] All KPI values still display correctly
- [ ] Water Consumption section (if present) still shows in Milling column
- [ ] No console errors
- [ ] Page loads without errors

---

## Feature 2: Enhanced Reset SCADA Baseline Modal with Current/Total/Custom Values

### Current State
- **File**: `Frontend/client/src/pages/hercules-sfms/LiveMonitor.tsx`
- **Backend API**: `backend/routes/scada_routes.py` - `/api/scada/reset` (POST)
- **Current Behavior**:
  - Button "Reset SCADA Baseline" opens a modal
  - Modal shows checkboxes for each scale with current value
  - User selects scales and clicks Reset
  - System resets selected scales to 0 (sets reset_base = current total from SCADA)
- **Current Modal Structure** (lines 308-558):
  - Shows scale checkboxes
  - Displays "Current: {value}" for each scale
  - Has "Select All" / "Deselect All" buttons
  - Reset button that sends `scale_tags` array to backend

### Required Changes

#### 1. Update Modal to Show Enhanced Information
- **Action**: Replace the current checkbox-based modal with a table-based layout showing detailed information
- **New Modal Structure**:
  ```
  For each scale, display in a table row:
  - Scale Tag (e.g., "WG101") - Column 1
  - Current (read-only label) - Column 2: Shows value after last reset
  - Total (read-only label) - Column 3: Shows original accumulated reading from SCADA/SQL
  - Custom Value (editable textbox) - Column 4: User can enter custom current reading
  ```
- **Specific Implementation**:
  - Remove checkbox selection mechanism
  - Create a table with 4 columns: Scale Tag | Current | Total | Custom Value
  - Each row represents one scale
  - Current and Total are read-only text labels (not inputs)
  - Custom Value is an editable number input (textbox)
  - Custom Value textbox should be empty by default
  - Custom Value textbox should accept decimal numbers
  - Custom Value textbox should have placeholder text like "Enter custom value (optional)"

#### 2. Fetch Scales Status Data
- **Action**: Use the existing backend API to get Current/Total values for all scales
- **Backend API**: `GET /api/scada/scales/status` (already exists, lines 369-420 in `scada_routes.py`)
- **API Response Structure**:
  ```json
  {
    "success": true,
    "scales": [
      {
        "tag": "WG101",
        "total": 1000.50,
        "current": 500.25,
        "reset_base": 500.25,
        "custom_offset": 0.0
      },
      ...
    ]
  }
  ```
- **Frontend Changes**:
  - Replace `fetchAvailableScales()` function to call `/api/scada/scales/status` instead of `/api/scada/available-scales`
  - Update state to store the full scales status data (with total, current, reset_base, custom_offset)
  - Update `AvailableScale` interface or create new interface to include: `tag`, `total`, `current`, `reset_base`, `custom_offset`

#### 3. Update Reset API to Accept Custom Values
- **Action**: Modify backend reset endpoint to accept custom values and calculate offsets automatically
- **Backend File**: `backend/routes/scada_routes.py`
- **Current Endpoint**: `POST /api/scada/reset` (lines 262-341)
- **New Request Body Format**:
  ```json
  {
    "scale_resets": [
      {
        "tag": "WG101",
        "custom_current_value": 300.0  // Optional: if provided, use this; if null/omitted, reset to 0
      },
      {
        "tag": "WG201",
        "custom_current_value": null  // Reset to 0 (default behavior)
      }
    ]
  }
  ```
- **Backend Logic**:
  - For each scale in `scale_resets`:
    - Get current total from SCADA: `total = row[tag]`
    - If `custom_current_value` is provided and is a valid number:
      - Calculate: `new_reset_base = total - custom_current_value`
      - Set: `SCADA_RESET_BASE[tag] = new_reset_base`
    - If `custom_current_value` is null/omitted/empty:
      - Use default behavior: `SCADA_RESET_BASE[tag] = total` (resets current to 0)
  - Return success response with updated baseline values

#### 4. Update Frontend Reset Function
- **Action**: Modify `confirmReset()` function to collect custom values and send to backend
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/LiveMonitor.tsx`
- **Current Function**: `confirmReset()` (lines 141-212)
- **New Logic**:
  - Create state to store custom values: `const [customValues, setCustomValues] = useState<Record<string, number | null>>({});`
  - For each scale in the modal, bind the Custom Value textbox to `customValues[scale.tag]`
  - When Reset button is clicked:
    - Build `scale_resets` array from all scales (not just selected ones)
    - For each scale:
      - If custom value textbox has a value (not empty, not null), include it in the request
      - If custom value textbox is empty, send `null` or omit the field
    - Send POST request to `/api/scada/reset` with new format
    - Handle response and show success/error message

#### 5. Modal UI Layout
- **Action**: Redesign modal to use table layout instead of checkboxes
- **Table Structure**:
  ```
  | Scale Tag | Current (After Last Reset) | Total (Accumulated) | Custom Value (New Current) |
  |-----------|----------------------------|---------------------|----------------------------|
  | WG101     | 500.25                     | 1000.50            | [textbox: empty]          |
  | WG201     | 750.00                     | 1500.00            | [textbox: empty]          |
  | ...       | ...                        | ...                | ...                       |
  ```
- **UI Requirements**:
  - Table should be scrollable if there are many scales
  - Current and Total columns should be right-aligned (numbers)
  - Custom Value textbox should be full-width in its cell
  - Custom Value textbox should have number input type
  - Custom Value textbox should allow decimal values
  - Add column headers with clear labels
  - Remove "Select All" / "Deselect All" buttons (not needed)
  - Remove checkbox column (not needed)
  - Keep "Cancel" and "Reset" buttons at bottom
  - Reset button should work for all scales (no selection needed)

### Implementation Steps

1. **Update State and Interface**:
   - Add state: `const [customValues, setCustomValues] = useState<Record<string, number | null>>({});`
   - Update `AvailableScale` interface or create new interface:
     ```typescript
     interface ScaleStatus {
       tag: string;
       total: number;
       current: number;
       reset_base: number;
       custom_offset: number;
     }
     ```
   - Update `availableScales` state type to use `ScaleStatus[]`

2. **Update fetchAvailableScales Function**:
   - Change API call from `/api/scada/available-scales` to `/api/scada/scales/status`
   - Parse response to extract scales array
   - Store in `availableScales` state

3. **Redesign Modal UI**:
   - Remove checkbox-based selection UI (lines 416-504)
   - Create table with 4 columns: Scale Tag | Current | Total | Custom Value
   - Map over `availableScales` to create table rows
   - Bind Custom Value textboxes to `customValues` state
   - Add onChange handler for textboxes:
     ```typescript
     const handleCustomValueChange = (tag: string, value: string) => {
       const numValue = value === '' ? null : parseFloat(value);
       setCustomValues(prev => ({ ...prev, [tag]: isNaN(numValue) ? null : numValue }));
     };
     ```

4. **Update confirmReset Function**:
   - Remove `selectedScales` dependency
   - Build `scale_resets` array from `availableScales`:
     ```typescript
     const scale_resets = availableScales.map(scale => ({
       tag: scale.tag,
       custom_current_value: customValues[scale.tag] ?? null
     }));
     ```
   - Update API call to send new format:
     ```typescript
     body: JSON.stringify({ scale_resets })
     ```

5. **Update Backend Reset Endpoint**:
   - Modify `POST /api/scada/reset` in `scada_routes.py`
   - Accept new request format: `{ "scale_resets": [...] }`
   - For each scale reset:
     - Get total from SCADA
     - If `custom_current_value` provided: `new_reset_base = total - custom_current_value`
     - If `custom_current_value` is null: `new_reset_base = total` (default: reset to 0)
     - Update `SCADA_RESET_BASE[tag] = new_reset_base`

### Expected Result

After implementation:
- **Modal opens** when "Reset SCADA Baseline" button is clicked
- **Modal shows table** with columns: Scale Tag | Current | Total | Custom Value
- **Current column** displays read-only value (after last reset)
- **Total column** displays read-only value (original accumulated from SCADA)
- **Custom Value column** has editable textbox for each scale (empty by default)
- **User can enter** custom values in textboxes (optional)
- **Reset button** processes all scales (no selection needed)
- **Backend calculates** offsets automatically:
  - If custom value entered: new current = custom value (by adjusting reset_base)
  - If no custom value: new current = 0 (default reset behavior)
- **Success message** shows which scales were reset

### Files to Modify
- **Frontend**: `Frontend/client/src/pages/hercules-sfms/LiveMonitor.tsx`
- **Backend**: `backend/routes/scada_routes.py`

### Testing Checklist
- [ ] Modal opens when Reset button is clicked
- [ ] Table displays all scales with 4 columns
- [ ] Current column shows correct values (after last reset)
- [ ] Total column shows correct values (from SCADA)
- [ ] Custom Value textboxes are editable and accept decimal numbers
- [ ] Custom Value textboxes are empty by default
- [ ] Entering custom value and clicking Reset updates that scale correctly
- [ ] Leaving Custom Value empty and clicking Reset uses default behavior (reset to 0)
- [ ] Multiple scales can have different custom values
- [ ] Backend correctly calculates reset_base based on custom values
- [ ] Success message displays after reset
- [ ] Modal closes after successful reset
- [ ] Data refreshes to show updated current values
- [ ] Error handling works if API call fails

---

## Feature 3: VPN Connection Check and Offline Orders Management

### Current State
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
- **Backend Files**: 
  - `backend/routes/process_orders.py` - `/api/process_orders/push-confirmation` (POST)
  - `backend/services/sap_confirmation.py` - SAPConfirmationService class
- **Current Behavior**:
  - Orders are pushed to SAP via `handlePushConfirmation()` and `handlePushSingleOrderConfirmation()`
  - Backend calls `sap_service.confirm_orders_batch()` which attempts to send to SAP
  - If SAP connection fails, error is returned but order is not stored for later retry
  - No VPN connectivity check before sending
  - No offline mode indicator
  - No offline orders storage or management
- **SAP Endpoint**: `https://vhmioqs4ci.sap.mc3.com.sa:44300` (HTTPS port 44300)
- **Current Metric Cards**: Total Orders, In Progress, Validated, Error Log (each with "View All" button)

### Required Changes

#### 1. Create VPN Connection Check Utility
- **Action**: Create a utility function to check VPN/SAP connectivity before each order push
- **Backend File**: Create new file `backend/utils/vpn_check.py` OR add to existing utility
- **Function Specification**:
  ```python
  def check_vpn_connection() -> Dict[str, Any]:
      """
      Check if VPN connection to SAP is available.
      Attempts to connect to SAP endpoint to verify connectivity.
      
      Returns:
          {
              "connected": bool,
              "message": str,
              "error": Optional[str]
          }
      """
  ```
- **Implementation Details**:
  - Use the same SAP endpoint URL as in `sap_confirmation.py`: `https://vhmioqs4ci.sap.mc3.com.sa:44300`
  - Try to fetch CSRF token from SAP endpoint (similar to `_get_csrf_token()` in `sap_confirmation.py`)
  - Use timeout of 5-10 seconds (shorter than full confirmation timeout)
  - If connection succeeds (200/201 status): return `{"connected": True, "message": "VPN connected"}`
  - If connection fails (ConnectionError, Timeout, 401, 500, etc.): return `{"connected": False, "message": "VPN disconnected", "error": "..."}`
  - Handle exceptions: `requests.exceptions.ConnectionError`, `requests.exceptions.Timeout`, `requests.exceptions.RequestException`
  - In mock mode, always return `{"connected": True}` (for testing)

#### 2. Create Offline Orders Database Model
- **Action**: Create database table to store orders that failed to send due to VPN/network issues
- **Backend File**: `backend/models/offline_confirmation.py` (new file)
- **Model Specification**:
  ```python
  class OfflineConfirmation(PostgresBase):
      __tablename__ = "offline_confirmations"
      
      id = Column(Integer, primary_key=True, autoincrement=True)
      order_id = Column(String(50), nullable=False, index=True)  # PO number
      process_order_id = Column(Integer, nullable=True)  # Internal process order ID
      material = Column(String(200), nullable=True)
      version = Column(String(50), nullable=True)
      confirmed_weight = Column(Float, nullable=False)
      total_qty = Column(Float, nullable=False)
      uom = Column(String(10), nullable=True)
      plant = Column(String(50), nullable=True)
      batch = Column(String(50), nullable=True)
      shift = Column(String(10), nullable=True)
      scrap = Column(Float, default=0.0)  # User-entered scrap value
      confirmed_text = Column(String(500), nullable=True)  # User-entered confirmed text
      sap_payload = Column(JSON, nullable=True)  # Store full SAP payload for retry
      validation_method = Column(String(50), nullable=True)  # 'Manual' or 'Automatic'
      created_at = Column(DateTime(timezone=True), default=func.now())
      updated_at = Column(DateTime(timezone=True), onupdate=func.now())
      sent_at = Column(DateTime(timezone=True), nullable=True)  # When successfully sent to SAP
      retry_count = Column(Integer, default=0)  # Number of retry attempts
      status = Column(String(20), default='pending')  # 'pending', 'sent', 'failed'
  ```
- **Database**: PostgreSQL (use `PostgresBase` from `database.py`)
- **Index**: Add index on `order_id` and `status` for faster queries

#### 3. Update Push Confirmation to Check VPN and Store Offline Orders
- **Action**: Modify order push functions to check VPN before sending, and store orders if VPN is down
- **Backend File**: `backend/routes/process_orders.py`
- **Function to Modify**: `push_confirmation()` (line 3502)
- **Implementation Steps**:
  1. **Before sending to SAP**, call VPN check:
     ```python
     from utils.vpn_check import check_vpn_connection
     vpn_status = check_vpn_connection()
     ```
  2. **If VPN is connected** (`vpn_status["connected"] == True`):
     - Proceed with normal SAP confirmation flow (existing code)
     - If SAP confirmation succeeds: return success
     - If SAP confirmation fails for other reasons (auth, data validation): return error (existing behavior)
  3. **If VPN is disconnected** (`vpn_status["connected"] == False`):
     - **DO NOT** attempt to send to SAP
     - **Store each order** in `offline_confirmations` table:
       - Extract order data from `sap_payloads` array
       - Create `OfflineConfirmation` record for each order
       - Store full `sap_payload` as JSON
       - Set `status = 'pending'`
       - Set `validation_method = 'Manual'` if from manual push, `'Automatic'` if from auto-validator
     - Return response indicating offline mode:
       ```python
       return jsonify({
           "success": False,
           "offline_mode": True,
           "message": "VPN disconnected - orders stored for offline confirmation",
           "stored_count": len(sap_payloads),
           "stored_orders": [p.get("po_number") for p in sap_payloads]
       }), 200  # 200 because it's not an error, just offline mode
       ```
  4. **Also check VPN in automatic validation push**:
     - In `services/auto_validator.py` or wherever automatic confirmation is triggered
     - Apply same VPN check before sending

#### 4. Add Offline Mode Indicator to Top Banner
- **Action**: Display a persistent banner at the top of Order Validation page when VPN is disconnected
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
- **Implementation**:
  - Add state: `const [vpnStatus, setVpnStatus] = useState<{connected: boolean, lastChecked: Date | null}>({connected: true, lastChecked: null});`
  - Create function to check VPN status:
     ```typescript
     const checkVpnStatus = async () => {
       try {
         const response = await fetch('/api/vpn/status');
         const data = await response.json();
         setVpnStatus({connected: data.connected, lastChecked: new Date()});
       } catch (err) {
         setVpnStatus({connected: false, lastChecked: new Date()});
       }
     };
     ```
  - Check VPN status:
     - On component mount
     - Before each order push (manual or automatic)
     - Periodically every 30-60 seconds (optional but recommended)
  - Display banner when `vpnStatus.connected === false`:
     ```tsx
     {!vpnStatus.connected && (
       <div className="w-full mb-4 p-4 rounded-lg bg-red-500/90 text-white flex items-center justify-between">
         <div className="flex items-center gap-3">
           <AlertTriangle className="h-5 w-5" />
           <div>
             <strong>Offline Mode</strong>
             <p className="text-sm">VPN disconnected - Orders are being stored for offline confirmation</p>
           </div>
         </div>
         <button onClick={checkVpnStatus}>Retry Connection</button>
       </div>
     )}
     ```
  - Banner should be visible at the top of the page, below the header but above KPI cards
  - Banner should persist until VPN is reconnected

#### 5. Create Backend VPN Status API
- **Action**: Create API endpoint to check VPN status
- **Backend File**: `backend/routes/process_orders.py` OR create new `backend/routes/vpn_routes.py`
- **Endpoint**: `GET /api/vpn/status`
- **Implementation**:
  ```python
  @process_orders_bp.route("/vpn/status", methods=["GET"])
  def get_vpn_status():
      """Check VPN connection status to SAP."""
      from utils.vpn_check import check_vpn_connection
      status = check_vpn_connection()
      return jsonify(status), 200
  ```
- **Response Format**:
  ```json
  {
    "connected": true/false,
    "message": "VPN connected" or "VPN disconnected",
    "error": null or "error message"
  }
  ```

#### 6. Add Offline Orders Metric Card
- **Action**: Add new KPI card for "Offline Orders" alongside existing cards
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
- **Location**: In the KPI Cards section (around line 4035)
- **Implementation**:
  - Add to `kpiCounts` state: `offlineOrders: 0`
  - Add API call to fetch offline orders count:
     ```typescript
     const loadOfflineOrdersCount = async () => {
       try {
         const response = await fetch('/api/offline-confirmations/count');
         const data = await response.json();
         setKpiCounts(prev => ({ ...prev, offlineOrders: data.count || 0 }));
       } catch (err) {
         console.error('Failed to load offline orders count:', err);
       }
     };
     ```
  - Add new KpiCard component:
     ```tsx
     <KpiCard
       title="Offline Orders"
       value={kpiCounts.offlineOrders}
       unit=""
       Icon={WifiOff}  // or similar offline icon
       color="#f59e0b"  // orange/amber color
       showViewButton={true}
       onViewClick={() => openOrdersModal('offline')}
     />
     ```
  - Update `openOrdersModal` function to handle `'offline'` type
  - Call `loadOfflineOrdersCount()` in `loadKpiCounts()` function

#### 7. Create Offline Orders Backend API
- **Action**: Create API endpoints to manage offline confirmations
- **Backend File**: `backend/routes/process_orders.py` OR create `backend/routes/offline_confirmations.py`
- **Endpoints Needed**:
  1. **GET `/api/offline-confirmations`**: List all pending offline confirmations
     - Query parameters: `?status=pending` (optional filter)
     - Returns: Array of offline confirmation objects
  2. **GET `/api/offline-confirmations/count`**: Get count of pending offline orders
     - Returns: `{"count": number}`
  3. **POST `/api/offline-confirmations/send`**: Send offline confirmations to SAP (bulk or individual)
     - Request body:
       ```json
       {
         "order_ids": [1, 2, 3],  // IDs from offline_confirmations table
         "bulk": true  // If true, send all selected; if false, send only specified IDs
       }
       ```
     - For each order:
       - Check VPN status first
       - If VPN connected: Send to SAP using stored `sap_payload`
       - If send succeeds: Update `status='sent'`, set `sent_at=now()`, increment `retry_count`
       - If send fails: Update `retry_count`, keep `status='pending'`
       - If VPN still disconnected: Return error, keep orders in offline table
  4. **PUT `/api/offline-confirmations/:id`**: Update scrap and confirmed_text for an offline order
     - Request body:
       ```json
       {
         "scrap": 10.5,
         "confirmed_text": "Manual confirmation note"
       }
       ```
     - Updates the offline confirmation record
     - Also updates the `sap_payload` JSON to include new scrap/confirmed_text values

#### 8. Create Offline Orders Modal/Tab
- **Action**: Create UI to view and manage offline orders (similar to existing "View All" modals)
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
- **Implementation**:
  - Extend `modalType` to include `'offline'`: `'validated' | 'rejected' | 'inprogress' | 'errorlog' | 'offline'`
  - Update `openOrdersModal` to handle `'offline'` type:
     ```typescript
     const openOrdersModal = async (type: 'validated' | 'rejected' | 'inprogress' | 'errorlog' | 'offline') => {
       // ... existing code ...
       if (type === 'offline') {
         const response = await fetch('/api/offline-confirmations?status=pending');
         const data = await response.json();
         setModalOrders(data.offline_confirmations || []);
         setModalTitle('Offline Orders');
       }
       // ... rest of existing code ...
     };
     ```
  - **Modal Content for Offline Orders**:
     - **Table Structure**:
       ```
       | [Checkbox] | PO Number | Material | Version | Confirmed Weight | Scrap | Confirmed Text | Actions |
       ```
     - Each row has:
       - Checkbox for selection
       - PO Number (read-only)
       - Material (read-only)
       - Version (read-only)
       - Confirmed Weight (read-only)
       - Scrap (editable textbox, similar to manual confirmation)
       - Confirmed Text (editable textarea, similar to manual confirmation)
       - Actions: "Send" button (individual send)
     - **Bulk Actions** (above table):
       - "Select All" / "Deselect None" buttons
       - "Send Selected" button (bulk send)
       - "Update Selected" button (update scrap/confirmed_text for selected orders)
     - **Individual Actions**:
       - Each row has "Send" button that sends only that order
       - Scrap and Confirmed Text fields are editable inline
     - **Send Logic**:
       - When "Send" clicked (individual or bulk):
         - Collect selected order IDs
         - For each order, get current scrap and confirmed_text values from form
         - Call `PUT /api/offline-confirmations/:id` to update values
         - Call `POST /api/offline-confirmations/send` with order IDs
         - If VPN is connected and send succeeds: Remove from list (or mark as sent)
         - If VPN is disconnected: Show error, keep in list
         - Refresh offline orders list after send

#### 9. Update Automatic Order Push to Check VPN
- **Action**: Ensure automatic order validation push also checks VPN
- **Backend Files**: 
  - `backend/services/auto_validator.py` (if it pushes orders)
  - `backend/services/shift_auto_confirm.py` (shift-end auto confirmation)
- **Implementation**:
  - Before calling `sap_service.push_confirmation()` or `sap_service.confirm_orders_batch()`
  - Check VPN using `check_vpn_connection()`
  - If VPN disconnected: Store orders in `offline_confirmations` table instead of sending
  - Log the offline storage event

### Implementation Steps

1. **Create VPN Check Utility**:
   - Create `backend/utils/vpn_check.py`
   - Implement `check_vpn_connection()` function
   - Test with real SAP endpoint

2. **Create Offline Confirmations Model**:
   - Create `backend/models/offline_confirmation.py`
   - Define `OfflineConfirmation` model
   - Add table creation in database initialization

3. **Create VPN Status API**:
   - Add `GET /api/vpn/status` endpoint
   - Return VPN connection status

4. **Update Push Confirmation Backend**:
   - Modify `push_confirmation()` in `process_orders.py`
   - Add VPN check before SAP call
   - Store orders in offline_confirmations if VPN down
   - Return appropriate response

5. **Create Offline Confirmations APIs**:
   - `GET /api/offline-confirmations` - List offline orders
   - `GET /api/offline-confirmations/count` - Get count
   - `POST /api/offline-confirmations/send` - Send to SAP
   - `PUT /api/offline-confirmations/:id` - Update scrap/confirmed_text

6. **Add Frontend VPN Status Check**:
   - Add VPN status state
   - Create `checkVpnStatus()` function
   - Add periodic check (every 30-60 seconds)
   - Check before each order push

7. **Add Offline Mode Banner**:
   - Create banner component
   - Display when VPN disconnected
   - Add "Retry Connection" button

8. **Add Offline Orders Metric Card**:
   - Add to KPI cards grid
   - Fetch count from API
   - Add "View All" button

9. **Create Offline Orders Modal**:
   - Extend modal to support 'offline' type
   - Create table with checkboxes and editable fields
   - Implement bulk and individual send
   - Handle scrap/confirmed_text updates

10. **Update Automatic Push**:
    - Add VPN check to auto-validator
    - Add VPN check to shift-end confirmation
    - Store in offline_confirmations if VPN down

### Expected Result

After implementation:
- **VPN Check**: Before each order push (manual or automatic), system checks VPN connection
- **Offline Banner**: Red/orange banner appears at top when VPN disconnected, showing "Offline Mode" message
- **Offline Storage**: Orders that fail to send due to VPN are stored in `offline_confirmations` table
- **Offline Orders Card**: New metric card shows count of pending offline orders with "View All" button
- **Offline Orders Modal**: 
  - Table showing all pending offline orders
  - Each row has: Checkbox, PO Number, Material, Version, Confirmed Weight (read-only)
  - Each row has: Scrap (editable), Confirmed Text (editable), Send button
  - Bulk actions: Select All, Send Selected, Update Selected
  - When Send clicked: Checks VPN, sends to SAP if connected, updates status
- **Automatic Handling**: Auto-validator and shift-end confirmation also check VPN and store offline if needed

### Files to Create/Modify

**New Files**:
- `backend/utils/vpn_check.py` - VPN connection check utility
- `backend/models/offline_confirmation.py` - Offline confirmations model
- `backend/routes/offline_confirmations.py` (optional) - Offline confirmations API routes

**Files to Modify**:
- `backend/routes/process_orders.py` - Add VPN check, offline storage, offline APIs
- `backend/services/sap_confirmation.py` - (may need minor updates)
- `backend/services/auto_validator.py` - Add VPN check
- `backend/services/shift_auto_confirm.py` - Add VPN check
- `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx` - Add VPN banner, offline card, offline modal
- `backend/database.py` or `backend/app.py` - Ensure offline_confirmations table is created

### Testing Checklist
- [ ] VPN check utility correctly detects connected/disconnected state
- [ ] VPN check works with real SAP endpoint
- [ ] Offline confirmations table is created in database
- [ ] Orders are stored in offline_confirmations when VPN is down
- [ ] Offline mode banner appears when VPN disconnected
- [ ] Offline mode banner disappears when VPN reconnected
- [ ] Offline Orders metric card shows correct count
- [ ] "View All" button opens offline orders modal
- [ ] Offline orders modal displays all pending orders
- [ ] Scrap and Confirmed Text fields are editable
- [ ] Individual "Send" button works for single order
- [ ] Bulk "Send Selected" button works for multiple orders
- [ ] Orders are removed from offline list after successful send
- [ ] Orders remain in offline list if VPN still disconnected
- [ ] Automatic order push also checks VPN and stores offline
- [ ] Manual order push checks VPN before sending
- [ ] VPN status is checked periodically (every 30-60 seconds)
- [ ] Retry Connection button works
- [ ] No console errors
- [ ] Database queries are efficient (indexed)

---

## Feature 4: Order Validation Page Enhancements (Tabs, Auto-Updates, Priority, Byproducts)

### Current State
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
- **Backend Files**: 
  - `backend/routes/sap_sync.py` - SAP order sync endpoint (line 334-520)
  - `backend/routes/order_validation.py` - Order validation logic
  - `backend/services/scale_lock_service.py` - Scale locking and priority management
- **Current Behavior**:
  - Orders are displayed in a single list, filtered by status (All, InProgress, Validated, etc.)
  - Orders are classified as MILLING or PACKING based on material code (13 = MILLING, 14 = PACKING)
  - SAP updates (version, target qty) are only applied if order status is "Pending" or "Rejected" (line 487 in sap_sync.py)
  - If order is InProgress or Validated, SAP updates are skipped (line 510-516)
  - Priority is stored in database but not displayed in table
  - Byproduct values (scale1_qty, scale2_qty, scale3_qty) are captured at order start but not displayed in table
  - No UI for custom byproduct value entry before sending to SAP

### Required Changes

#### 1. Add Milling and Packing Tabs
- **Action**: Replace single order list with tabbed interface showing Milling and Packing orders separately
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
- **Implementation**:
  - Add tab state: `const [activeOrderTab, setActiveOrderTab] = useState<'milling' | 'packing' | 'all'>('all');`
  - Add tab navigation UI above the orders table:
     ```tsx
     <div className="flex gap-2 mb-4 border-b">
       <button
         onClick={() => setActiveOrderTab('all')}
         className={activeOrderTab === 'all' ? 'active-tab' : 'inactive-tab'}
       >
         All Orders
       </button>
       <button
         onClick={() => setActiveOrderTab('milling')}
         className={activeOrderTab === 'milling' ? 'active-tab' : 'inactive-tab'}
       >
         Milling
       </button>
       <button
         onClick={() => setActiveOrderTab('packing')}
         className={activeOrderTab === 'packing' ? 'active-tab' : 'inactive-tab'}
       >
         Packing
       </button>
     </div>
     ```
  - Filter orders based on active tab:
     ```typescript
     const filteredOrdersByTab = filteredOrders.filter((order: Order) => {
       if (activeOrderTab === 'all') return true;
       if (activeOrderTab === 'milling') return (order as any).order_type === 'MILLING';
       if (activeOrderTab === 'packing') return (order as any).order_type === 'PACKING';
       return true;
     });
     ```
  - Display `filteredOrdersByTab` instead of `filteredOrders` in the table
  - Maintain existing status filter (All, InProgress, Validated, etc.) - it should work within each tab

#### 2. Fix Automatic SAP Updates for InProgress/Validated Orders
- **Action**: Allow SAP updates (version, target qty) to be applied to InProgress/Validated orders without requiring pause/refresh
- **Backend File**: `backend/routes/sap_sync.py`
- **Current Code**: Lines 486-517
- **Current Logic**: 
  ```python
  if existing.status in ["Pending", "Rejected"]:
      # Update order
  else:
      # Skip update (preserve state)
  ```
- **New Logic**:
  ```python
  if existing.status in ["Pending", "Rejected"]:
      # Update order (existing behavior)
  elif existing.status in ["InProgress", "Validated"]:
      # ✅ NEW: Apply updates to InProgress/Validated orders
      # Update only safe fields: version, quantity, expected_weight, material_desc, priority, plant, batch
      # DO NOT update: status, confirmed_qty, current_shift, baseline fields, scale fields
      existing.version = version
      existing.quantity = quantity
      existing.expected_weight = expected
      existing.material_desc = material_desc
      existing.priority = priority
      existing.plant = plant
      existing.batch = batch
      existing.sap_created_on = created_at
      if hasattr(existing, 'updated_at'):
          existing.updated_at = datetime.utcnow()
      
      # ✅ CRITICAL: If target quantity changed, recalculate progress
      # This ensures UI shows updated target without requiring pause
      # The auto-validator will continue using new target
      
      updated.append({
          "order_id": order_id,
          "expected_weight": expected,
          "unit": unit,
          "quantity": quantity,
          "material_desc": material_desc,
          "previous_status": existing.status,
          "auto_updated": True  # Flag to indicate auto-update
      })
      print(f"♻️ Auto-updated InProgress/Validated order {order_id} from SAP sync")
  else:
      # Completed or other statuses - skip update
      skipped.append({...})
  ```
- **Frontend Changes**:
  - No changes needed - orders will automatically reflect updates when `loadOrders()` is called
  - The progress calculation will use the new target quantity automatically
  - Consider adding a visual indicator (e.g., badge or tooltip) when an order was auto-updated from SAP

#### 3. Add Priority Column to Orders Table
- **Action**: Display priority value in orders table, highlighting orders with duplication conflicts
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
- **Backend File**: `backend/services/scale_lock_service.py` (already has priority logic)
- **Implementation**:
  - Add Priority column header in table
  - Display priority value from `order.priority` or `orderPriorities[order.id]`
  - **Priority Calculation Logic** (backend):
     - Orders with duplicate version or scales should have higher priority (lower number = higher priority)
     - Check for duplicates:
       - Same `version` (product version)
       - Same scales (scale1, scale2, scale3 combinations)
     - Priority should be calculated when order is created/updated
     - Priority 1 = highest priority (most urgent)
     - Priority increases (2, 3, 4...) for lower priority orders
  - **Visual Indicators**:
     - Highlight orders with priority 1-3 (high priority) with different background color or badge
     - Show tooltip explaining why order has high priority (duplicate version/scales)
  - **Backend Priority Calculation** (add to `sap_sync.py` or create utility):
     ```python
     def calculate_order_priority(order, all_orders) -> int:
         """
         Calculate priority for an order based on duplication conflicts.
         Lower number = higher priority.
         """
         priority = 100  # Default priority
         
         # Check for duplicate version
         duplicate_version_count = sum(
             1 for o in all_orders 
             if o.version == order.version 
             and o.status in ['Pending', 'InProgress']
             and o.id != order.id
         )
         
         # Check for duplicate scales
         order_scales = set([order.scale1, order.scale2, order.scale3])
         order_scales.discard(None)
         order_scales.discard('')
         
         duplicate_scale_count = 0
         for other_order in all_orders:
             if other_order.id == order.id:
                 continue
             if other_order.status not in ['Pending', 'InProgress']:
                 continue
             other_scales = set([other_order.scale1, other_order.scale2, other_order.scale3])
             other_scales.discard(None)
             other_scales.discard('')
             if order_scales & other_scales:  # Intersection
                 duplicate_scale_count += 1
         
         # Set priority based on conflicts
         if duplicate_version_count > 0 or duplicate_scale_count > 0:
             priority = min(1 + duplicate_version_count + duplicate_scale_count, 10)
         
         return priority
     ```
  - Call `calculate_order_priority()` when order is created/updated in SAP sync
  - Store priority in `order.priority` field

#### 4. Display Byproduct Values for Milling Orders
- **Action**: Show byproduct values (Byproduct 1, Byproduct 2) in orders table for Milling orders
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
- **Backend**: Byproduct values are already stored in `scale1_qty`, `scale2_qty`, `scale3_qty` fields
- **Implementation**:
  - Add "Byproduct 1" and "Byproduct 2" columns to orders table (only visible for MILLING orders)
  - Display values from:
     - `order.scale1_qty` → Byproduct 1
     - `order.scale2_qty` → Byproduct 2
     - `order.scale3_qty` → Byproduct 3 (if applicable, or combine with Byproduct 2)
  - Show scale tag names if available: `order.scale1`, `order.scale2`, `order.scale3`
  - Format: `{scale_tag}: {value} {unit}` (e.g., "WG101: 1250.50 KG")
  - Only show for orders where `order_type === 'MILLING'`
  - For PACKING orders, hide these columns or show "N/A"

#### 5. Custom Byproduct Value Entry Before SAP Send
- **Action**: Allow user to enter custom byproduct values before sending confirmation to SAP, with validation and overflow handling
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
- **Backend File**: `backend/routes/process_orders.py` - `push_confirmation()` endpoint
- **Implementation Details**:
  
  **5.1. Add Custom Byproduct Input Fields**:
  - In the order validation modal or confirmation modal, add input fields for byproduct values
  - Fields: "Custom Byproduct 1", "Custom Byproduct 2", "Custom Byproduct 3" (if applicable)
  - Only show for MILLING orders
  - Each field should:
     - Show current value (read-only label): `Current: {scale1_qty} KG`
     - Have editable textbox for custom value
     - Have validation: Custom value must be ≤ Current value
     - Show error message if custom value > current value
  
  **5.2. Validation Logic**:
  ```typescript
  const validateByproductValue = (customValue: number, currentValue: number): boolean => {
    // Custom value must be less than or equal to current value
    return customValue <= currentValue;
  };
  ```
  
  **5.3. Overflow Calculation**:
  - If custom value < current value: `overflow = current - custom`
  - This overflow should be:
     - Stored in order record (new field: `byproduct1_overflow`, `byproduct2_overflow`, etc.)
     - OR stored in a separate overflow tracking table
     - Applied to the next order that uses the same scale
     - When next order starts, add overflow to its baseline or initial quantity
  
  **5.4. Backend Changes**:
  - Modify `push_confirmation()` to accept custom byproduct values:
     ```python
     # Request body:
     {
         "order_ids": [1, 2, 3],
         "custom_byproducts": {
             "order_id_1": {
                 "scale1_qty": 1000.0,  # Custom value (must be <= current)
                 "scale2_qty": 500.0,
                 "scale3_qty": 0.0
             }
         }
     }
     ```
  - Validate custom values:
     ```python
     for order_id, byproducts in custom_byproducts.items():
         order = get_order(order_id)
         if byproducts.get('scale1_qty', 0) > order.scale1_qty:
             return error("Custom byproduct 1 cannot exceed current value")
         # Calculate overflow
         overflow1 = order.scale1_qty - byproducts.get('scale1_qty', 0)
         # Store overflow for next order
         store_byproduct_overflow(order.scale1, overflow1)
     ```
  - Update SAP payload to use custom byproduct values instead of current values
  - Store overflow values for next order consumption
  
  **5.5. Overflow Application to Next Order**:
  - When next order starts and uses the same scale:
     - Check for overflow from previous order
     - Add overflow to order's initial byproduct quantity or baseline
     - Clear overflow after applying
  - Implementation location: `backend/routes/order_validation.py` - `start_order()` function
     ```python
     # In start_order(), after capturing baselines:
     overflow1 = get_byproduct_overflow(order.scale1)
     if overflow1 > 0:
         # Add overflow to baseline or initial quantity
         current_scale1_qty = get_attr_safe(order, "scale1_qty", 0.0)
         set_attr_safe(order, "scale1_qty", current_scale1_qty + overflow1)
         clear_byproduct_overflow(order.scale1)
     ```

### Implementation Steps

1. **Add Milling/Packing Tabs**:
   - Add `activeOrderTab` state
   - Create tab navigation UI
   - Filter orders by tab
   - Test tab switching

2. **Fix SAP Auto-Updates**:
   - Modify `sap_sync.py` to update InProgress/Validated orders
   - Test with SAP sync while order is validating
   - Verify updates appear without pause/refresh

3. **Add Priority Column**:
   - Create `calculate_order_priority()` function
   - Call it during order creation/update
   - Add Priority column to frontend table
   - Add visual indicators for high-priority orders

4. **Display Byproduct Values**:
   - Add Byproduct 1/2 columns to table
   - Show values for MILLING orders only
   - Format with scale tags and units

5. **Custom Byproduct Entry**:
   - Add input fields in confirmation modal
   - Add validation (custom ≤ current)
   - Modify backend to accept custom values
   - Implement overflow calculation and storage
   - Implement overflow application to next order

### Expected Result

After implementation:
- **Tabs**: Orders page has "All Orders", "Milling", "Packing" tabs
- **Auto-Updates**: SAP updates (version, target qty) apply to InProgress/Validated orders automatically
- **Priority Column**: Table shows priority values, with high-priority orders highlighted
- **Byproduct Display**: Milling orders show Byproduct 1 and Byproduct 2 values in table
- **Custom Byproduct Entry**: 
  - User can enter custom byproduct values before sending to SAP
  - Validation ensures custom ≤ current
  - Overflow is calculated and applied to next order using same scale
  - SAP payload uses custom values

### Files to Modify

**Backend**:
- `backend/routes/sap_sync.py` - Fix auto-updates for InProgress/Validated orders
- `backend/routes/process_orders.py` - Add custom byproduct handling in push_confirmation
- `backend/routes/order_validation.py` - Add overflow application in start_order
- `backend/services/scale_lock_service.py` - (may need priority calculation utility)

**Frontend**:
- `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx` - Add tabs, priority column, byproduct display, custom byproduct inputs

**Database** (if needed):
- Consider adding `byproduct_overflow` table or fields to track overflow values

### Testing Checklist
- [ ] Milling and Packing tabs work correctly
- [ ] Orders are filtered correctly by tab
- [ ] Status filter works within each tab
- [ ] SAP updates apply to InProgress orders without pause
- [ ] SAP updates apply to Validated orders without pause
- [ ] Priority column displays correctly
- [ ] Priority calculation works for duplicate versions
- [ ] Priority calculation works for duplicate scales
- [ ] High-priority orders are visually highlighted
- [ ] Byproduct 1 and Byproduct 2 columns show for Milling orders
- [ ] Byproduct columns are hidden for Packing orders
- [ ] Custom byproduct input fields appear for Milling orders
- [ ] Custom byproduct validation works (custom ≤ current)
- [ ] Error message shows if custom > current
- [ ] Overflow is calculated correctly
- [ ] Overflow is stored for next order
- [ ] Overflow is applied to next order using same scale
- [ ] SAP payload uses custom byproduct values
- [ ] No console errors
- [ ] All existing functionality still works

---

## Feature 5: Admin Settings, SAP Logging, Error Handling, and Error Log Reprocessing

### Current State
- **Admin Page**: `Frontend/client/src/pages/hercules-sfms/Admin.tsx`
- **Sync Interval Settings**: `backend/routes/sync_interval_routes.py` - Currently uses time-based (HH:MM) scheduling, not interval-based (minutes)
- **Error Log**: `backend/models/error_log.py` - Stores errors with payload as JSONB
- **Error Log Display**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx` - Shows error log in modal
- **SAP Logging**: Currently logs to console/print statements, not stored in database
- **Current Behavior**:
  - Sync intervals are configured by time (e.g., 09:00, 09:30) not by interval (e.g., every 15 minutes)
  - SAP requests/responses are logged to console but not stored for viewing
  - Error log shows errors but no reprocessing option
  - Error handling may be inconsistent across screens

### Required Changes

#### 1. Add SAP Sync Interval (Minutes) to Admin Settings
- **Action**: Add option to configure SAP order sync interval in minutes (in addition to or replacing time-based scheduling)
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/Admin.tsx`
- **Backend File**: `backend/routes/sync_interval_routes.py`
- **Database Model**: `backend/models/user_roles.py` - `SyncIntervalSettings` model
- **Implementation Details**:

  **1.1. Update Database Model**:
  - Add `sync_interval_minutes` field to `SyncIntervalSettings`:
     ```python
     sync_interval_minutes = Column(Integer, nullable=True)  # Interval in minutes (e.g., 15, 30, 60)
     ```
  - If `sync_interval_minutes` is set, use interval-based scheduling
  - If `sync_interval_minutes` is NULL, use time-based scheduling (existing behavior)

  **1.2. Update Admin UI**:
  - In Admin page, find "Data Sync Interval Settings" section (around line 1954)
  - Add new input field for "SAP Order Sync Interval (Minutes)":
     ```tsx
     <div className="space-y-4">
       <div>
         <label className="text-sm font-medium text-gray-300">
           SAP Order Sync Interval (Minutes)
         </label>
         <input
           type="number"
           min="1"
           max="1440"
           value={sapSyncInterval}
           onChange={(e) => setSapSyncInterval(parseInt(e.target.value))}
           placeholder="e.g., 15, 30, 60"
           className="mt-1 w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded"
         />
         <p className="text-xs text-gray-400 mt-1">
           How often to check for new orders from SAP (in minutes)
         </p>
       </div>
     </div>
     ```
  - Add "Save" button to update the interval
  - Show current interval value from API

  **1.3. Update Backend API**:
  - Add `PUT /api/sync-interval/settings/process_orders` endpoint:
     ```python
     @sync_interval_bp.route("/settings/process_orders", methods=["PUT"])
     @require_manager_or_admin
     def update_process_orders_interval():
         """Update SAP order sync interval in minutes"""
         data = request.get_json()
         interval_minutes = data.get('sync_interval_minutes')
         
         if interval_minutes is None:
             return jsonify({'error': 'sync_interval_minutes is required'}), 400
         
         if not isinstance(interval_minutes, int) or interval_minutes < 1 or interval_minutes > 1440:
             return jsonify({'error': 'sync_interval_minutes must be between 1 and 1440'}), 400
         
         with PostgresSessionLocal() as db:
             setting = db.query(SyncIntervalSettings).filter(
                 SyncIntervalSettings.sync_type == 'process_orders'
             ).first()
             
             if not setting:
                 return jsonify({'error': 'Sync setting not found'}), 404
             
             setting.sync_interval_minutes = interval_minutes
             setting.updated_by = request.current_user['user_id']
             db.commit()
             
             return jsonify({
                 'success': True,
                 'message': f'SAP order sync interval updated to {interval_minutes} minutes',
                 'setting': {
                     'sync_interval_minutes': setting.sync_interval_minutes
                 }
             }), 200
     ```

  **1.4. Update Scheduler**:
  - Modify `backend/services/sync_scheduler.py` to use interval-based scheduling if `sync_interval_minutes` is set
  - If `sync_interval_minutes` is set, schedule using `schedule.every(interval_minutes).minutes.do(...)`
  - If `sync_interval_minutes` is NULL, use existing time-based scheduling

#### 2. Create SAP Log Page
- **Action**: Create new page to display all SAP JSON requests and responses with user-friendly details view
- **New Frontend File**: `Frontend/client/src/pages/hercules-sfms/SapLog.tsx`
- **New Backend Model**: `backend/models/sap_log.py`
- **New Backend Routes**: `backend/routes/sap_log_routes.py`
- **Implementation Details**:

  **2.1. Create Database Model**:
  - Create `backend/models/sap_log.py`:
     ```python
     class SapLog(PostgresBase):
         __tablename__ = "sap_logs"
         
         id = Column(Integer, primary_key=True, autoincrement=True)
         direction = Column(String(10), nullable=False)  # 'sent' or 'received'
         endpoint = Column(String(200), nullable=True)  # SAP endpoint URL
         method = Column(String(10), nullable=True)  # 'GET', 'POST', etc.
         request_payload = Column(JSONB, nullable=True)  # JSON sent to SAP
         response_payload = Column(JSONB, nullable=True)  # JSON received from SAP
         status_code = Column(Integer, nullable=True)  # HTTP status code
         error_message = Column(Text, nullable=True)  # Error message if failed
         duration_ms = Column(Integer, nullable=True)  # Request duration in milliseconds
         po_number = Column(String(50), nullable=True, index=True)  # Related order (if applicable)
         log_type = Column(String(50), nullable=True)  # 'order_confirmation', 'order_sync', 'kpi', 'raw_data', etc.
         created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
         
         def __repr__(self):
             return f"<SapLog(id={self.id}, direction={self.direction}, endpoint={self.endpoint})>"
     ```

  **2.2. Create Logging Utility**:
  - Create `backend/utils/sap_logger.py`:
     ```python
     def log_sap_request(endpoint, method, payload, po_number=None, log_type=None):
         """Log SAP request before sending"""
         # Store in database
         # Return log_id for linking with response
     
     def log_sap_response(log_id, response_payload, status_code, error_message=None, duration_ms=None):
         """Log SAP response after receiving"""
         # Update existing log entry with response
     ```

  **2.3. Integrate Logging into SAP Services**:
  - Modify `backend/services/sap_confirmation.py`:
     - Before sending request: Call `log_sap_request()`
     - After receiving response: Call `log_sap_response()`
  - Modify `backend/routes/sap_sync.py`:
     - Log order sync requests/responses
  - Modify `backend/routes/kpi_routes.py`:
     - Log KPI send requests/responses
  - Modify `backend/routes/process_orders.py`:
     - Log push confirmation requests/responses

  **2.4. Create Backend API**:
  - Create `backend/routes/sap_log_routes.py`:
     ```python
     @sap_log_bp.route("/sap-logs", methods=["GET"])
     def get_sap_logs():
         """Get SAP logs with pagination and filtering"""
         # Query parameters: page, limit, direction, log_type, po_number, date_from, date_to
         # Return paginated list of logs
     
     @sap_log_bp.route("/sap-logs/<int:log_id>", methods=["GET"])
     def get_sap_log_detail(log_id):
         """Get detailed view of a single SAP log entry"""
         # Return full request/response JSON with formatting
     ```

  **2.5. Create Frontend Page**:
  - Create `Frontend/client/src/pages/hercules-sfms/SapLog.tsx`:
     - Table/list view showing:
       - Timestamp
       - Direction (Sent/Received icon)
       - Endpoint
       - Method
       - Status Code (with color coding)
       - PO Number (if applicable)
       - Log Type
       - Duration
     - Click on row to open detail modal showing:
       - Full request JSON (formatted, syntax highlighted)
       - Full response JSON (formatted, syntax highlighted)
       - Headers
       - Error message (if any)
       - Copy to clipboard buttons
     - Filters:
       - Date range
       - Direction (Sent/Received)
       - Log Type
       - PO Number
       - Status Code
     - Pagination
     - Export to JSON/CSV option

#### 3. Error Handling Across All Screens
- **Action**: Ensure consistent error handling and user-friendly error messages across all pages
- **Implementation**:
  - **3.1. Create Error Boundary Component**:
     - Create `Frontend/client/src/components/ErrorBoundary.tsx`:
       - Catches React errors
       - Displays user-friendly error message
       - Logs error to backend
       - Provides "Reload" button
  - **3.2. Standardize Error Messages**:
     - Create `Frontend/client/src/utils/errorMessages.ts`:
       - Centralized error message mapping
       - User-friendly messages for common errors
       - Technical details for admin users
  - **3.3. Add Try-Catch to All API Calls**:
     - Wrap all `fetch()` calls in try-catch
     - Display toast notifications for errors
     - Log errors to backend
  - **3.4. Add Loading States**:
     - Show loading indicators during API calls
     - Disable buttons during operations
     - Prevent duplicate submissions
  - **3.5. Add Network Error Handling**:
     - Detect network failures
     - Show "Connection lost" message
     - Provide retry option
  - **3.6. Validate User Input**:
     - Client-side validation before API calls
     - Show validation errors immediately
     - Prevent invalid submissions

#### 4. Error Log Reprocessing
- **Action**: Add reprocessing option for error log orders (SAP errors, not offline) with scrap + confirmed text fields
- **Frontend File**: `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
- **Backend File**: `backend/routes/process_orders.py`
- **Implementation Details**:

  **4.1. Update Error Log Display**:
  - In error log modal, add "Reprocess" button for each error entry
  - Only show for errors where `error_type === 'sap_failed'` and `source !== 'offline'`
  - Hide reprocess button for offline errors (handled separately in Feature 3)

  **4.2. Create Reprocess Modal**:
  - Similar to manual confirmation modal
  - Fields:
     - PO Number (read-only)
     - Material (read-only)
     - Current Confirmed Qty (read-only)
     - Scrap (editable, default from payload if available)
     - Confirmed Text (editable, default from payload if available)
     - Error Message (read-only, shows original error)
  - Buttons: "Cancel", "Reprocess Order"

  **4.3. Backend Reprocess Endpoint**:
  - Create `POST /api/error-log/<int:log_id>/reprocess`:
     ```python
     @error_log_bp.route("/error-log/<int:log_id>/reprocess", methods=["POST"])
     def reprocess_error_order(log_id):
         """Reprocess an order from error log"""
         data = request.get_json()
         scrap = data.get('scrap', 0.0)
         confirmed_text = data.get('confirmed_text', '')
         
         # Get error log entry
         error_log = db.query(ErrorLog).filter(ErrorLog.id == log_id).first()
         if not error_log:
             return jsonify({'error': 'Error log not found'}), 404
         
         # Get original payload
         payload = error_log.payload
         if not payload:
             return jsonify({'error': 'No payload found in error log'}), 400
         
         # Update payload with new scrap and confirmed_text
         payload['scrap'] = scrap
         payload['confirmed_text'] = confirmed_text
         
         # Try to send to SAP again
         sap_service = SAPConfirmationService()
         result = sap_service.push_confirmation([payload], 'online')
         
         if result.get('success'):
             # Mark error log as resolved
             error_log.status = 'Resolved'
             error_log.resolved_at = datetime.now()
             db.commit()
             return jsonify({'success': True, 'message': 'Order reprocessed successfully'})
         else:
             # Update error log with new error
             error_log.error_message = result.get('error', 'Reprocess failed')
             error_log.payload = payload  # Update with new scrap/confirmed_text
             db.commit()
             return jsonify({'success': False, 'error': result.get('error')}), 500
     ```

  **4.4. Bulk Reprocessing**:
  - Add "Select All" / "Deselect All" checkboxes
  - Add "Reprocess Selected" button
  - For bulk reprocess:
     - Show modal to enter scrap/confirmed_text (applied to all selected)
     - OR allow individual values per order
     - Process each order sequentially
     - Show progress and results

### Implementation Steps

1. **Add SAP Sync Interval to Admin Settings**:
   - Add `sync_interval_minutes` field to database model
   - Create migration script
   - Update Admin UI with input field
   - Create/update backend API endpoint
   - Update scheduler to use interval-based scheduling

2. **Create SAP Logging System**:
   - Create `SapLog` database model
   - Create logging utility functions
   - Integrate logging into all SAP service calls
   - Create backend API endpoints
   - Create frontend SAP Log page
   - Add route to navigation

3. **Implement Error Handling**:
   - Create ErrorBoundary component
   - Create error message utility
   - Add try-catch to all API calls
   - Add loading states
   - Add network error detection
   - Add input validation

4. **Add Error Log Reprocessing**:
   - Update error log modal UI
   - Create reprocess modal component
   - Create backend reprocess endpoint
   - Add bulk reprocessing support
   - Test reprocessing flow

### Expected Result

After implementation:
- **Admin Settings**: User can set SAP order sync interval in minutes (e.g., every 15 minutes)
- **SAP Log Page**: 
  - New page showing all SAP requests/responses
  - Clickable entries to view full JSON details
  - Filters and pagination
  - Export functionality
- **Error Handling**: 
  - Consistent error messages across all screens
  - User-friendly error display
  - Network error detection and retry
  - Input validation
- **Error Log Reprocessing**:
  - "Reprocess" button in error log modal
  - Reprocess modal with scrap + confirmed text fields
  - Bulk reprocessing support
  - Error log marked as resolved after successful reprocess

### Files to Create/Modify

**New Files**:
- `backend/models/sap_log.py` - SAP log database model
- `backend/utils/sap_logger.py` - SAP logging utility
- `backend/routes/sap_log_routes.py` - SAP log API routes
- `Frontend/client/src/pages/hercules-sfms/SapLog.tsx` - SAP log page
- `Frontend/client/src/components/ErrorBoundary.tsx` - Error boundary component
- `Frontend/client/src/utils/errorMessages.ts` - Error message utility

**Files to Modify**:
- `backend/models/user_roles.py` - Add `sync_interval_minutes` field
- `backend/routes/sync_interval_routes.py` - Add interval update endpoint
- `backend/services/sync_scheduler.py` - Support interval-based scheduling
- `Frontend/client/src/pages/hercules-sfms/Admin.tsx` - Add interval input
- `backend/services/sap_confirmation.py` - Add SAP logging
- `backend/routes/sap_sync.py` - Add SAP logging
- `backend/routes/kpi_routes.py` - Add SAP logging
- `backend/routes/process_orders.py` - Add SAP logging, add reprocess endpoint
- `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx` - Add reprocess UI
- All frontend pages - Add error handling

### Testing Checklist
- [ ] Admin can set SAP sync interval in minutes
- [ ] Scheduler uses interval-based scheduling when set
- [ ] SAP requests are logged to database
- [ ] SAP responses are logged to database
- [ ] SAP Log page displays all logs
- [ ] Clicking log entry shows full JSON details
- [ ] Filters work correctly (date, direction, type, PO, status)
- [ ] Export functionality works
- [ ] Error boundary catches React errors
- [ ] Error messages are user-friendly
- [ ] Network errors are detected and handled
- [ ] Input validation works
- [ ] Loading states show during API calls
- [ ] Error log shows "Reprocess" button for SAP errors
- [ ] Reprocess modal opens with correct fields
- [ ] Reprocessing sends order to SAP with new scrap/confirmed_text
- [ ] Error log marked as resolved after successful reprocess
- [ ] Bulk reprocessing works
- [ ] No console errors
- [ ] All existing functionality still works

---

## Notes for AI Agents

- **Always read the entire file** before making changes
- **Test incrementally**: Make one change, verify it works, then proceed
- **Preserve existing functionality**: Only remove/modify what is explicitly specified
- **Maintain styling**: Keep existing theme support (light/dark mode)
- **Check dependencies**: Ensure all imports and components are still valid after removals
- **Verify data flow**: Ensure API calls and data fetching remain intact

