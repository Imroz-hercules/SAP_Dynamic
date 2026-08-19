/**
 * SAP Hercules API Service
 * Handles sending Hercules data to SAP with CSRF token authentication
 */

interface HerculesData {
  ASMReporting_5ID: number;
  CreatedOn: string;
  DM101: number;
  DM102: number;
  DM201: number;
  DM202: number;
  DM203: number;
  Dummy?: string | null;
  Dummy2?: string | null;
  Dummy3?: string | null;
  GUID: string;
  PL601_TOT: number;
  PL602_TOT: number;
  PL603_TOT: number;
  PreviousRecordGUID: string;
  SL601_COUNTER: number;
  SL601_DAMAGED: number;
  SL601_Product: string;
  SL601_SIZE: number;
  SL602_COUNTER: number;
  SL602_DAMAGED: number;
  SL602_PRODUCT: string;
  SL602_SIZE: number;
  SL603_COUNTER: number;
  SL603_DAMAGED: number;
  SL603_Product: string;
  SL603_SIZE: number;
  SL606_COUNTER: number;
  SL606_DAMAGED: number;
  SL606_Product: string;
  SL606_SIZE: number;
  SL606_TOT: number;
  SL607_COUNTER: number;
  SL607_DAMAGED: number;
  SL607_PRODUCT: string;
  SL607_SIZE: number;
  SL607_TOT: number;
  WG101: number;
  WG101_Destination: number;
  WG101_Product: string;
  WG201: number;
  WG201_Destination: number;
  WG201_Product: string;
  WG202: number;
  WG202_Product: string;
  WG301: number;
  WG302: number;
  WG501: number;
  WG501_Destination: number;
  WG501_Product: string;
  WG502: number;
  WG502_Destination: number;
  WG502_Product: string;
  WG503: number;
  WG503_Product: string;
}

interface SAPResponse {
  success: boolean;
  message: string;
  response?: string;
  error?: string;
}

class SAPHerculesService {
  private readonly SAP_URL = 'http://vhmioqs4ci.sap.mc3.com.sa:8000/zmi_raw_hercl/HERC?sap-client=200';
  private readonly SAP_USERNAME = '99999';
  private readonly SAP_PASSWORD = 'P@ssw0rdP@ssw0rd';

  /**
   * Create Basic Authentication header
   */
  private getAuthHeader(): string {
    const credentials = btoa(`${this.SAP_USERNAME}:${this.SAP_PASSWORD}`);
    return `Basic ${credentials}`;
  }

  /**
   * Step 1: Fetch CSRF token from SAP
   */
  private async fetchCSRFToken(): Promise<{ token: string; cookies: string }> {
    console.log('🔐 Fetching CSRF token from SAP...');

    try {
      const response = await fetch(this.SAP_URL, {
        method: 'GET',
        headers: {
          'x-csrf-token': 'fetch',
          'Authorization': this.getAuthHeader(),
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch CSRF token: ${response.status} ${response.statusText}`);
      }

      const csrfToken = response.headers.get('x-csrf-token');
      const cookies = response.headers.get('set-cookie') || '';

      if (!csrfToken) {
        throw new Error('CSRF token not found in response headers');
      }

      console.log('✅ CSRF token fetched successfully');
      return { token: csrfToken, cookies };

    } catch (error) {
      console.error('❌ Error fetching CSRF token:', error);
      throw error;
    }
  }

  /**
   * Step 2: Send Hercules data to SAP with CSRF token
   */
  async sendHerculesDataToSAP(data: HerculesData): Promise<SAPResponse> {
    try {
      console.log('🚀 Starting SAP Hercules data send process...');
      console.log('📊 Data to send:', data);

      // Step 1: Get CSRF token
      const { token: csrfToken } = await this.fetchCSRFToken();

      // Step 2: Send POST request with data
      console.log('📤 Sending Hercules data to SAP...');

      const response = await fetch(this.SAP_URL, {
        method: 'POST',
        headers: {
          'x-csrf-token': csrfToken,
          'Authorization': this.getAuthHeader(),
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(data)
      });

      const responseText = await response.text();
      console.log('📥 SAP Response:', responseText);

      if (response.ok && responseText.includes('Data Saved Correctly')) {
        console.log('✅ Hercules data sent successfully to SAP');
        return {
          success: true,
          message: 'Data Saved Correctly',
          response: responseText
        };
      } else {
        console.error('❌ Failed to send Hercules data to SAP');
        return {
          success: false,
          message: 'Failed to send data to SAP',
          response: responseText,
          error: `HTTP ${response.status}: ${response.statusText}`
        };
      }

    } catch (error: any) {
      console.error('❌ Error sending Hercules data to SAP:', error);
      return {
        success: false,
        message: 'Network or server error',
        error: error.message || 'Unknown error occurred'
      };
    }
  }

  /**
   * Send latest record from database to SAP via backend endpoint
   */
  async sendLatestRecordToSAP(): Promise<SAPResponse> {
    try {
      console.log('🚀 Sending Hercules data to SAP via backend...');
      
      // Use backend endpoint that handles SAP communication
      const response = await fetch('/api/hercules/send-to-sap', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      console.log('📥 Backend response:', result);
      
      return {
        success: result.success || false,
        message: result.message || 'Unknown response',
        response: result.response,
        error: result.error
      };

    } catch (error: any) {
      console.error('❌ Error sending Hercules data via backend:', error);
      return {
        success: false,
        message: 'Failed to send Hercules data',
        error: error.message || 'Unknown error occurred'
      };
    }
  }
}

// Export singleton instance
export const sapHerculesService = new SAPHerculesService();
export type { HerculesData, SAPResponse };
