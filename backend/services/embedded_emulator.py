"""
Embedded SCADA Emulator Service
================================
A lightweight SCADA emulator that runs within the Flask backend.
Generates synthetic SCADA data for demo/testing purposes.

Features:
- Configurable scale activation (turn on/off individual scales)
- Adjustable data generation speed (interval, step min/max)
- Reset to zero or realistic starting values
- Thread-safe value generation
- Persistent state across requests
"""

import threading
import random
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any

log = logging.getLogger("embedded_emulator")

# =============================================================================
# SCALE CONFIGURATION - Organized by Category
# =============================================================================

# Input/process monitoring fields (Wheat input scales) - LO/HI pairs
INPUT_FIELDS = [
    "WG101_LO", "WG101_HI",
    "WG201_LO", "WG201_HI",
    "WG202_LO", "WG202_HI",
    "WG301_LO", "WG301_HI",
    "WG302_LO", "WG302_HI",
]

# Milling streams (cumulative TON counters) - LO/HI pairs
MILLING_FIELDS = [
    "WG501_LO", "WG501_HI",
    "WG502_LO", "WG502_HI",
    "WG503_LO", "WG503_HI",
]

# Water dosing meters
WATER_FIELDS = [
    "DM101", "DM102", "DM201", "DM202", "DM203",
]

# Packing palletizer bag counters
PACKING_FIELDS = [
    "PL601_TOT", "PL602_TOT", "PL603_TOT",
    "SL607_TOT", "SL606_TOT",
]

# Combined list of all SCADA keys (mutable — refreshed from scada_tags)
SCADA_KEYS = list(INPUT_FIELDS + MILLING_FIELDS + WATER_FIELDS + PACKING_FIELDS)

# Category mapping for display
SCALE_CATEGORIES = {
    "INPUT": {
        "name": "Input Scales (Wheat)",
        "fields": INPUT_FIELDS,
        "color": "#3b82f6",
        "description": "Wheat input monitoring scales"
    },
    "MILLING": {
        "name": "Milling Scales (Flour/Bran)",
        "fields": MILLING_FIELDS,
        "color": "#22c55e",
        "description": "Flour and bran production scales"
    },
    "WATER": {
        "name": "Water Meters",
        "fields": WATER_FIELDS,
        "color": "#06b6d4",
        "description": "Water dosing meters"
    },
    "PACKING": {
        "name": "Packing Palletizers",
        "fields": PACKING_FIELDS,
        "color": "#f59e0b",
        "description": "Bag counting palletizers"
    },
}

# Realistic starting values (matching real SCADA data patterns)
REALISTIC_STARTING_VALUES = {
    # INPUT scales - HI stays constant, LO increments
    "WG101_LO": 708000, "WG101_HI": 226847,
    "WG201_LO": 319800, "WG201_HI": 228566,
    "WG202_LO": 921600, "WG202_HI": 232093,
    "WG301_LO": 970900, "WG301_HI": 5011,
    "WG302_LO": 791900, "WG302_HI": 1458,
    # MILLING scales
    "WG501_LO": 99400, "WG501_HI": 41458,
    "WG502_LO": 535000, "WG502_HI": 26985,
    "WG503_LO": 651200, "WG503_HI": 45646,
    # Water meters - start at 0, increment slowly (simulates cumulative water usage)
    # ✅ FIX (Jan 26, 2026): Start at 0 so delta calculation works correctly
    "DM101": 0.0, "DM102": 0.0, "DM201": 0.0, "DM202": 0.0, "DM203": 0.0,
    # Packing palletizers (integer counters)
    "PL601_TOT": 100000, "PL602_TOT": 1312600, "PL603_TOT": 1636400,
    "SL607_TOT": 93500, "SL606_TOT": 61900,
}


class EmbeddedEmulator:
    """
    Embedded SCADA Emulator that generates synthetic data.
    Thread-safe singleton that can be controlled via API.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - only one emulator instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize emulator state (only runs once due to singleton)."""
        if self._initialized:
            return
        
        self._initialized = True
        self._data_lock = threading.RLock()  # RLock allows reentrant locking (same thread can acquire multiple times)
        
        # Scale values
        self.scale_values: Dict[str, float] = {k: 0.0 for k in SCADA_KEYS}
        
        # Active scales (which ones are accumulating)
        self.active_scales: Set[str] = set(SCADA_KEYS)
        
        # Configuration
        self.config = {
            "interval": 10.0,        # Seconds between data updates
            "step_min": 1.0,         # Minimum increment per tick
            "step_max": 10.0,        # Maximum increment per tick
            "jitter": 0.2,           # Jitter factor (0-1)
        }
        
        # Load config from DB if available
        self._load_config_from_db()
        
        # Running state
        self.running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Last generated data (for API)
        self.last_row: Dict[str, Any] = {}
        self.last_update_time: Optional[datetime] = None
        
        # ✅ FIX (Jan 26, 2026): Don't auto-initialize with realistic values
        # Start with all zeros - user can click "Reset Realistic" if they want realistic values
        # This ensures "Reset to 0" works properly without backend restart overriding it
        # self._init_realistic_values()  # Commented out - start with zeros
        
        # Load config from DB if available
        self._load_config_from_db()
        self.load_active_scales_from_db()
        
        log.info("🛰️ Embedded SCADA Emulator initialized")
    
    def _init_realistic_values(self):
        """Initialize with realistic starting values."""
        for key, value in REALISTIC_STARTING_VALUES.items():
            if key in self.scale_values:
                self.scale_values[key] = float(value)
        log.info("📊 Initialized with realistic starting values")
    
    def _load_config_from_db(self):
        """Load configuration from system_settings table."""
        try:
            from models.system_settings import get_setting
            
            interval = get_setting("emulator_interval", self.config["interval"])
            step_min = get_setting("emulator_step_min", self.config["step_min"])
            step_max = get_setting("emulator_step_max", self.config["step_max"])
            
            self.config["interval"] = float(interval)
            self.config["step_min"] = float(step_min)
            self.config["step_max"] = float(step_max)
            
            log.info(f"⚙️ Loaded config from DB: {self.config}")
        except Exception as e:
            log.warning(f"⚠️ Failed to load config from DB (using defaults): {e}")
    
    # =========================================================================
    # Configuration Methods
    # =========================================================================
    
    def get_config(self) -> dict:
        """Get current configuration."""
        # No lock for read-only access - Python dict operations are atomic
        return {
            **dict(self.config),
            "running": self.running,
            "active_scale_count": len(self.active_scales),
            "total_scale_count": len(SCADA_KEYS),
        }
    
    def set_config(self, **kwargs) -> dict:
        """Update configuration."""
        with self._data_lock:
            for key, value in kwargs.items():
                if key in self.config and value is not None:
                    self.config[key] = float(value)
            
            # Ensure step_min <= step_max
            if self.config["step_min"] > self.config["step_max"]:
                self.config["step_max"] = self.config["step_min"]
            
            log.info(f"⚙️ Config updated: {self.config}")
            return self.get_config()
            
    def load_active_scales_from_db(self):
        """Load active scales from database."""
        try:
            from models.system_settings import get_setting
            import json
            
            active_json = get_setting("emulator_active_scales", "[]")
            if active_json:
                active_list = json.loads(active_json)
                if active_list:
                    with self._data_lock:
                        self.active_scales = set(active_list)
                    log.info(f"⚙️ Loaded active scales from DB: {len(active_list)} scales")
        except Exception as e:
            log.warning(f"⚠️ Failed to load active scales from DB: {e}")

    def save_active_scales_to_db(self):
        """Save active scales to database."""
        try:
            from models.system_settings import set_setting
            import json
            
            with self._data_lock:
                active_list = list(self.active_scales)
                
            set_setting("emulator_active_scales", json.dumps(active_list), "json")
        except Exception as e:
            log.error(f"Error saving active scales to DB: {e}")
    
    # =========================================================================
    # Scale Control Methods
    # =========================================================================
    
    def get_scales_status(self) -> dict:
        """Get all scales with their current values and active status."""
        # No lock for read-only access - quick snapshot
        scale_values_copy = dict(self.scale_values)
        active_scales_copy = set(self.active_scales)
        
        scales = {}
        for key in SCADA_KEYS:
            scales[key] = {
                "value": scale_values_copy.get(key, 0.0),
                "active": key in active_scales_copy,
            }
        
        # Also return combined values for LO/HI pairs
        combined = {}
        processed_bases = set()
        for key in SCADA_KEYS:
            if key.endswith("_LO"):
                base = key[:-3]
                if base not in processed_bases:
                    hi_key = base + "_HI"
                    lo_val = int(scale_values_copy.get(key, 0))
                    hi_val = int(scale_values_copy.get(hi_key, 0))
                    # Zero-pad LO to 6 digits to ensure consistent concatenation
                    combined[base] = float(str(hi_val) + str(lo_val).zfill(6)) if hi_val > 0 else float(lo_val)
                    processed_bases.add(base)
            elif not key.endswith("_HI"):
                combined[key] = scale_values_copy.get(key, 0.0)
        
        return {
            "scales": scales,
            "combined": combined,
            "categories": SCALE_CATEGORIES,
            "active_count": len(active_scales_copy),
            "total_count": len(SCADA_KEYS),
        }
    
    def get_all_scales(self) -> dict:
        """Return raw scale values dictionary.
        
        Used by kpi_incremental.py to get SCADA values in demo/emulator mode.
        Returns a flat dict of {scale_name: value} for all scales.
        """
        return dict(self.scale_values)
    
    def set_scale_active(self, scale: str, active: bool) -> bool:
        """Toggle a single scale on/off."""
        with self._data_lock:
            if scale not in SCADA_KEYS:
                return False
            
            if active:
                self.active_scales.add(scale)
                # If toggling _LO, also toggle _HI
                if scale.endswith("_LO"):
                    hi_scale = scale[:-3] + "_HI"
                    if hi_scale in SCADA_KEYS:
                        self.active_scales.add(hi_scale)
            else:
                self.active_scales.discard(scale)
                if scale.endswith("_LO"):
                    hi_scale = scale[:-3] + "_HI"
                    self.active_scales.discard(hi_scale)
            
            # Save to DB
            self.save_active_scales_to_db()
            
            return True
    
    def set_scales_bulk(self, on: list = None, off: list = None, set_all: list = None) -> dict:
        """Bulk update scale activation."""
        with self._data_lock:
            if set_all is not None:
                self.active_scales = {s for s in set_all if s in SCADA_KEYS}
            else:
                for scale in (on or []):
                    if scale in SCADA_KEYS:
                        self.active_scales.add(scale)
                for scale in (off or []):
                    self.active_scales.discard(scale)
            
            # Save to DB
            self.save_active_scales_to_db()
            
            return {"active_scales": sorted(list(self.active_scales))}
    
    def set_category_active(self, category: str, active: bool) -> bool:
        """Enable/disable all scales in a category."""
        if category not in SCALE_CATEGORIES:
            return False
        
        with self._data_lock:
            fields = SCALE_CATEGORIES[category]["fields"]
            for field in fields:
                if active:
                    self.active_scales.add(field)
                else:
                    self.active_scales.discard(field)
            
            # Save to DB
            self.save_active_scales_to_db()
            
            return True
    
    # =========================================================================
    # Reset Methods
    # =========================================================================
    
    def reset_to_zero(self) -> dict:
        """Reset all values to zero."""
        with self._data_lock:
            for key in SCADA_KEYS:
                self.scale_values[key] = 0.0
            self.last_row = {}
            log.info("🔄 All values reset to zero")
            return {"status": "reset_to_zero", "message": "All values reset to zero"}
    
    def reset_to_realistic(self) -> dict:
        """Reset to realistic starting values."""
        with self._data_lock:
            for key in SCADA_KEYS:
                self.scale_values[key] = 0.0
            self._init_realistic_values()
            self.last_row = {}
            log.info("🔄 Values reset to realistic starting values")
            return {"status": "reset_to_realistic", "message": "Values reset to realistic starting values"}
    
    def reset_category(self, category: str) -> bool:
        """Reset values for a specific category to zero."""
        if category not in SCALE_CATEGORIES:
            return False
        
        with self._data_lock:
            for field in SCALE_CATEGORIES[category]["fields"]:
                self.scale_values[field] = 0.0
            log.info(f"🔄 {category} values reset to zero")
            return True
    
    # =========================================================================
    # Data Generation
    # =========================================================================
    
    def generate_tick(self) -> dict:
        """
        Generate one tick of data - increment active scales.
        
        Real SCADA behavior:
        - HI values stay CONSTANT (high-order part, rarely changes)
        - LO values INCREMENT slowly (low-order part, +1 to +10 per tick)
        - Backend concatenates as strings: str(int(HI)) + str(int(LO))
        """
        with self._data_lock:
            cfg = self.config
            active = set(self.active_scales)
            
            for key in SCADA_KEYS:
                if key not in active:
                    continue
                
                # Generate increment
                increment = random.uniform(cfg["step_min"], cfg["step_max"])
                
                # Apply jitter occasionally
                if random.random() < cfg["jitter"]:
                    increment *= random.uniform(0.2, 1.5)
                
                # Handle different field types
                if key.endswith("_LO"):
                    # Increment LO value with overflow handling (like real SCADA)
                    new_lo = self.scale_values[key] + int(increment)
                    base_tag = key[:-3]  # strip _LO
                    try:
                        from services.scada_tag_registry import get_rollover_max
                        lo_max = int(get_rollover_max(base_tag, default=1000000.0) or 1000000)
                    except Exception:
                        lo_max = 1000000
                    if new_lo >= lo_max:
                        # Roll over LO and increment HI
                        hi_key = key[:-3] + "_HI"
                        if hi_key in self.scale_values:
                            overflow_count = int(new_lo // lo_max)
                            self.scale_values[hi_key] += overflow_count
                        new_lo = new_lo % lo_max
                    self.scale_values[key] = new_lo
                elif key.endswith("_HI"):
                    # HI only changes on LO overflow - don't increment directly
                    pass
                elif key.startswith("DM"):
                    # Water meters - very small decimal increments (simulates water flow per tick)
                    # In production, DM values are 30-sec readings (0.5-2.0 typical)
                    # In demo with 1-sec ticks, use 0.01-0.03 per tick → ~0.3-0.9 per 30 seconds
                    self.scale_values[key] += random.uniform(0.01, 0.03)
                else:
                    # Packing palletizers - integer increments
                    self.scale_values[key] += int(increment)
            
            # Build last_row with transformed values
            self.last_row = self._build_api_response()
            self.last_update_time = datetime.now(timezone.utc)
            
            return self.last_row
    
    def _build_api_response(self) -> dict:
        """Build the API response format (matching external emulator format)."""
        # Transform scales: combine LO/HI pairs into single values
        transformed_scales = {}
        raw_scales = {}
        processed_bases = set()
        
        for key in SCADA_KEYS:
            raw_scales[key] = self.scale_values.get(key, 0.0)
            
            if key.endswith("_LO"):
                base_key = key[:-3]
                hi_key = base_key + "_HI"
                
                if base_key not in processed_bases:
                    lo_val = int(self.scale_values.get(key, 0))
                    hi_val = int(self.scale_values.get(hi_key, 0))
                    
                    # Concatenate HI + LO as strings (matching real SCADA behavior)
                    # Zero-pad LO to 6 digits to ensure consistent concatenation
                    if hi_val > 0:
                        combined_str = str(hi_val) + str(lo_val).zfill(6)
                        transformed_scales[base_key] = float(combined_str)
                    else:
                        transformed_scales[base_key] = float(lo_val)
                    
                    processed_bases.add(base_key)
            
            elif key.endswith("_HI"):
                continue  # Skip - handled by _LO processing
            
            else:
                # Single-value fields
                transformed_scales[key] = self.scale_values.get(key, 0.0)
        
        return {
            "scales": transformed_scales,
            "raw_scales": raw_scales,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "embedded_emulator",
        }
    
    def get_latest(self) -> dict:
        """Get latest data (API endpoint format)."""
        # No lock for read-only access
        if not self.last_row:
            # Generate initial data if none exists
            return self._build_api_response()
        return dict(self.last_row)  # Return a copy
    
    # =========================================================================
    # Worker Thread Control
    # =========================================================================
    
    def start(self) -> dict:
        """Start the emulator worker thread."""
        if self.running:
            return {"status": "already_running", "message": "Emulator is already running"}
        
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        self.running = True
        
        log.info("🚀 Emulator worker started")
        return {"status": "started", "message": "Emulator started successfully"}
    
    def stop(self) -> dict:
        """Stop the emulator worker thread."""
        if not self.running:
            return {"status": "already_stopped", "message": "Emulator is not running"}
        
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        self.running = False
        
        log.info("⏹️ Emulator worker stopped")
        return {"status": "stopped", "message": "Emulator stopped successfully"}
    
    def _worker_loop(self):
        """Background worker that generates data at intervals."""
        log.info(f"🔄 Emulator worker loop started - {len(self.active_scales)} active scales")
        
        while not self._stop_event.is_set():
            self.generate_tick()
            
            # Sleep for the configured interval (check stop event periodically)
            interval = self.config.get("interval", 10.0)
            sleep_time = 0
            while sleep_time < interval and not self._stop_event.is_set():
                time.sleep(0.1)
                sleep_time += 0.1
        
        log.info("🔄 Emulator worker loop ended")
    
    def get_status(self) -> dict:
        """Get emulator status summary."""
        # No lock for read-only access
        return {
            "running": self.running,
            "config": dict(self.config),
            "active_scales": len(self.active_scales),
            "total_scales": len(SCADA_KEYS),
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
            "categories": list(SCALE_CATEGORIES.keys()),
        }


# =============================================================================
# Global emulator instance (singleton)
# =============================================================================
emulator = EmbeddedEmulator()


def get_emulator() -> EmbeddedEmulator:
    """Get the global emulator instance."""
    return emulator
