"""
demo_sap_server.py — Mock SAP server + Tkinter GUI (Postgres-backed).

Run from the backend folder (venv active):

  cd backend
  python demo_sap_server.py

Listens on port 6000 (matches SAP_MOCK_URL=http://localhost:6000/mock).

Requirements:
  pip install flask psycopg2-binary
"""

import threading
import json
import time
from datetime import datetime
from queue import Queue, Empty

# Flask
from flask import Flask, request, jsonify

# Tkinter
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Postgres driver
import psycopg2
import psycopg2.extras

# -------------------------
# CONFIG: Edit if needed
# -------------------------
PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "demo_server"
PG_USER = "postgres"
PG_PASS = "Hercules"

FLASK_PORT = 6000
AUTO_REFRESH_MS = 2000  # GUI auto-refresh interval

# -------------------------
# Helpers: Postgres access
# -------------------------

def get_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )

def init_db():
    """Create tables if not exist (safe even if you already created them)."""
    ddl_confirmations = """
    CREATE TABLE IF NOT EXISTS confirmations (
        id SERIAL PRIMARY KEY,
        po_number TEXT,
        material TEXT,
        confirmed_qty DOUBLE PRECISION,
        final_flag TEXT,
        payload JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    ddl_raw = """
    CREATE TABLE IF NOT EXISTS raw_data (
        id SERIAL PRIMARY KEY,
        payload JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    ddl_orders = """
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        payload JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(ddl_confirmations)
        cur.execute(ddl_raw)
        cur.execute(ddl_orders)
        conn.commit()
        cur.close()
        print("✅ DB initialized (tables ensured).")
    except Exception as e:
        print("❌ DB init error:", e)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def save_confirmation_to_db(data_dict):
    """
    data_dict expected to be a dict representing one confirmation entry
    Fields used: PROCESS_ORDER, MATERIAL, CONFIRMED_WEIGHT or CONFIRMED_QTY, FINAL_CONFIRMATION
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        po = data_dict.get("PROCESS_ORDER") or data_dict.get("po_number") or None
        material = data_dict.get("MATERIAL") or data_dict.get("material") or None
        # different code paths in your app use CONFIRMED_WEIGHT or CONFIRMED_QTY
        conf = data_dict.get("CONFIRMED_WEIGHT")
        if conf is None:
            conf = data_dict.get("CONFIRMED_QTY") or data_dict.get("confirmed_qty")
        try:
            conf_val = float(conf) if conf is not None else None
        except Exception:
            conf_val = None
        final_flag = data_dict.get("FINAL_CONFIRMATION", "") or data_dict.get("final_confirmation", "")
        payload_json = psycopg2.extras.Json(data_dict)
        cur.execute("""
            INSERT INTO confirmations (po_number, material, confirmed_qty, final_flag, payload)
            VALUES (%s, %s, %s, %s, %s)
        """, (po, material, conf_val, final_flag, payload_json))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print("❌ save_confirmation_to_db error:", e)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def save_raw_to_db(payload):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO raw_data (payload) VALUES (%s)", (psycopg2.extras.Json(payload),))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print("❌ save_raw_to_db error:", e)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def save_order_to_db(payload):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO orders (payload) VALUES (%s)", (psycopg2.extras.Json(payload),))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print("❌ save_order_to_db error:", e)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def fetch_confirmations(limit=200):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, po_number, material, confirmed_qty, final_flag, payload, created_at FROM confirmations ORDER BY id DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_orders(limit=200):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, payload, created_at FROM orders ORDER BY id DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_raw(limit=200):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, payload, created_at FROM raw_data ORDER BY id DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# -------------------------
# Flask Mock SAP server
# -------------------------
app = Flask("demo_sap_mock")

# Simple in-memory log queue for GUI
LOG_QUEUE = Queue(maxsize=500)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        LOG_QUEUE.put_nowait(f"{timestamp}  {msg}")
    except Exception:
        pass
    print(f"{timestamp}  {msg}")

@app.route("/mock/zmi_conf_online/CONF", methods=["GET", "POST"])
def mock_online_conf():
    if request.method == "GET":
        log("GET /mock/zmi_conf_online/CONF -> token request")
        return jsonify({"x-csrf-token": "demo-token"}), 200

    payload = request.get_json(silent=True)
    if not payload:
        payload = []

    log(f"POST /mock/zmi_conf_online/CONF -> received {len(payload)} item(s)")
    responses = []
    for item in payload:
        try:
            # save each incoming confirmation payload to Postgres
            saved = save_confirmation_to_db(item)
            responses.append({
                "PROCESS_ORDER": item.get("PROCESS_ORDER", ""),
                "MESSAGE": "Confirmation Saved Successfully (DEMO)",
                "STATUS": "SUCCESS"
            })
            log(f"Saved confirmation PO={item.get('PROCESS_ORDER')} saved={saved}")
        except Exception as e:
            responses.append({
                "PROCESS_ORDER": item.get("PROCESS_ORDER", ""),
                "MESSAGE": f"ERROR: {str(e)}",
                "STATUS": "ERROR"
            })
            log(f"Error saving confirmation PO={item.get('PROCESS_ORDER')}: {e}")

    return jsonify(responses), 200

@app.route("/mock/zmi_conf_offlin/CONFOFF", methods=["GET", "POST"])
def mock_offline_conf():
    if request.method == "GET":
        log("GET /mock/zmi_conf_offlin/CONFOFF -> token request")
        return jsonify({"x-csrf-token": "demo-token"}), 200

    payload = request.get_json(silent=True) or []
    log(f"POST /mock/zmi_conf_offlin/CONFOFF -> received {len(payload)} item(s)")
    responses = []
    for item in payload:
        try:
            save_confirmation_to_db(item)
            responses.append({
                "PROCESS_ORDER": item.get("PROCESS_ORDER", ""),
                "MESSAGE": "Offline Confirmation Saved (DEMO)",
                "STATUS": "SUCCESS"
            })
            log(f"Saved offline confirmation PO={item.get('PROCESS_ORDER')}")
        except Exception as e:
            responses.append({
                "PROCESS_ORDER": item.get("PROCESS_ORDER", ""),
                "MESSAGE": f"ERROR: {str(e)}",
                "STATUS": "ERROR"
            })
            log(f"Error saving offline confirmation PO={item.get('PROCESS_ORDER')}: {e}")
    return jsonify(responses), 200

@app.route("/mock/zmi_raw_hercl/HERC", methods=["POST"])
def mock_raw_hercl():
    payload = request.get_json(silent=True) or {}
    saved = save_raw_to_db(payload)
    log(f"POST /mock/zmi_raw_hercl/HERC -> saved={saved}")
    return "Data Saved Correctly (DEMO)", 200

@app.route("/mock/zmi_kpi_all/ALL", methods=["POST"])
def mock_all_kpi():
    payload = request.get_json(silent=True) or {}
    save_raw_to_db({"kpi_type": "all", "payload": payload})
    log("POST /mock/zmi_kpi_all/ALL -> received ALL KPI")
    return jsonify({"STATUS": "SUCCESS", "MESSAGE": "ALL KPI Saved (DEMO)"}), 200

@app.route("/mock/zmi_get_orders/GETORD", methods=["GET"])
def mock_get_orders():
    # Return a sample order list (and store the sample in orders table)
    sample_order = {
        "PROCESS_ORDER": "000013000001",
        "MATERIAL": "000000000001300001",
        "TOTAL_QTY": 100.0,
        "UOM": "TO",
        "PRIORITY_ID": "1",
        "CONFIRMED_QTY": 0,
        "PLANT": "3130",
        "CREATED_ON": "20250101"
    }
    save_order_to_db(sample_order)
    log("GET /mock/zmi_get_orders/GETORD -> returned sample order and saved to orders table")
    return jsonify([sample_order]), 200

# --------------------------------------------------------------------
# MOCK MILLING KPI ENDPOINT
# --------------------------------------------------------------------
@app.route("/mock/zmi_kpi_mill/MKPI", methods=["GET", "POST"])
def mock_milling_kpi():
    if request.method == "GET":
        log("GET /mock/zmi_kpi_mill/MKPI -> token request")
        return jsonify({"x-csrf-token": "demo-token"}), 200

    payload = request.get_json(silent=True) or {}
    log(f"POST /mock/zmi_kpi_mill/MKPI -> received milling KPI payload")

    # Store KPI in raw_data table for auditing
    save_raw_to_db({
        "kpi_type": "milling",
        "payload": payload
    })

    # Return SAP-style response
    return jsonify({
        "STATUS": "SUCCESS",
        "MESSAGE": "Milling KPI Saved Successfully (DEMO)"
    }), 200

# --------------------------------------------------------------------
# MOCK PACKING KPI ENDPOINT
# --------------------------------------------------------------------
@app.route("/mock/zmi_kpi_pack/PKPI", methods=["GET", "POST"])
def mock_packing_kpi():
    if request.method == "GET":
        log("GET /mock/zmi_kpi_pack/PKPI -> token request")
        return jsonify({"x-csrf-token": "demo-token"}), 200

    payload = request.get_json(silent=True) or {}
    log(f"POST /mock/zmi_kpi_pack/PKPI -> received packing KPI payload")

    # Store KPI in raw_data table
    save_raw_to_db({
        "kpi_type": "packing",
        "payload": payload
    })

    # SAP-style response
    return jsonify({
        "STATUS": "SUCCESS",
        "MESSAGE": "Packing KPI Saved Successfully (DEMO)"
    }), 200

def run_flask():
    # Disable Flask default logging to keep console cleaner
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=False, use_reloader=False, threaded=True)

# -------------------------
# Payload Viewer Dialog
# -------------------------
class PayloadViewerDialog:
    def __init__(self, parent, title, payload_data):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("700x500")
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create text widget with scrollbar
        frame = ttk.Frame(self.dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrolled text widget
        self.text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=80, height=25)
        self.text_widget.pack(fill="both", expand=True)
        
        # Format and display payload
        formatted_json = json.dumps(payload_data, indent=2, ensure_ascii=False)
        self.text_widget.insert("1.0", formatted_json)
        self.text_widget.config(state=tk.DISABLED)  # Make read-only
        
        # Close button
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        close_btn = ttk.Button(btn_frame, text="Close", command=self.dialog.destroy)
        close_btn.pack(side="right")
        
        # Center dialog on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

# -------------------------
# Tkinter GUI
# -------------------------
class DemoSAPGUI:
    def __init__(self, master):
        self.master = master
        master.title("Demo SAP Server (Postgres) — Local Sandbox")
        master.geometry("1100x700")

        # Store full row data for payload viewing
        self.confirmations_data = []
        self.orders_data = []
        self.raw_data = []

        # Top frame: controls + status
        top_frame = ttk.Frame(master)
        top_frame.pack(side="top", fill="x", padx=6, pady=6)

        self.btn_refresh = ttk.Button(top_frame, text="Refresh Now", command=self.refresh_all)
        self.btn_refresh.pack(side="left")

        ttk.Label(top_frame, text="   ").pack(side="left")
        self.btn_clear_confirmations = ttk.Button(top_frame, text="Clear Confirmations", command=self.clear_confirmations_prompt)
        self.btn_clear_confirmations.pack(side="left")

        ttk.Label(top_frame, text="   ").pack(side="left")
        self.btn_clear_raw = ttk.Button(top_frame, text="Clear Raw Data", command=self.clear_raw_prompt)
        self.btn_clear_raw.pack(side="left")

        ttk.Label(top_frame, text="   ").pack(side="left")
        self.btn_clear_orders = ttk.Button(top_frame, text="Clear Orders", command=self.clear_orders_prompt)
        self.btn_clear_orders.pack(side="left")

        ttk.Label(top_frame, text="   ").pack(side="left")
        self.lbl_status = ttk.Label(top_frame, text="Server: starting...")
        self.lbl_status.pack(side="right")

        # Notebook for tabs
        self.nb = ttk.Notebook(master)
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)

        # Confirmations tab - WITH PAYLOAD COLUMN
        self.tab_conf = ttk.Frame(self.nb)
        self.nb.add(self.tab_conf, text="Confirmations")
        self.tree_conf = ttk.Treeview(self.tab_conf, columns=("id","po","material","qty","final","payload","created_at"), show="headings")
        for c, w in [("id",60),("po",150),("material",140),("qty",80),("final",80),("payload",300),("created_at",200)]:
            self.tree_conf.heading(c, text=c)
            self.tree_conf.column(c, width=w)
        self.tree_conf.pack(fill="both", expand=True)
        # Bind double-click event
        self.tree_conf.bind("<Double-Button-1>", self.on_confirmation_double_click)

        # Orders tab
        self.tab_orders = ttk.Frame(self.nb)
        self.nb.add(self.tab_orders, text="Orders")
        self.tree_orders = ttk.Treeview(self.tab_orders, columns=("id","payload","created_at"), show="headings")
        self.tree_orders.heading("id", text="id"); self.tree_orders.column("id", width=60)
        self.tree_orders.heading("payload", text="payload"); self.tree_orders.column("payload", width=900)
        self.tree_orders.heading("created_at", text="created_at"); self.tree_orders.column("created_at", width=160)
        self.tree_orders.pack(fill="both", expand=True)
        # Bind double-click event
        self.tree_orders.bind("<Double-Button-1>", self.on_orders_double_click)

        # Raw data tab
        self.tab_raw = ttk.Frame(self.nb)
        self.nb.add(self.tab_raw, text="Raw Data")
        self.tree_raw = ttk.Treeview(self.tab_raw, columns=("id","payload","created_at"), show="headings")
        self.tree_raw.heading("id", text="id"); self.tree_raw.column("id", width=60)
        self.tree_raw.heading("payload", text="payload"); self.tree_raw.column("payload", width=900)
        self.tree_raw.heading("created_at", text="created_at"); self.tree_raw.column("created_at", width=160)
        self.tree_raw.pack(fill="both", expand=True)
        # Bind double-click event
        self.tree_raw.bind("<Double-Button-1>", self.on_raw_double_click)

        # Logs (bottom)
        bottom = ttk.LabelFrame(master, text="Server Logs")
        bottom.pack(side="bottom", fill="x", padx=6, pady=6)
        self.txt_log = tk.Text(bottom, height=8)
        self.txt_log.pack(fill="both", expand=True)

        # start periodic refresh
        self.master.after(1000, self.periodic_refresh)
        # update server status
        self.update_server_status("Running (mock SAP on port %s)" % FLASK_PORT)

    def update_server_status(self, txt):
        self.lbl_status['text'] = txt

    def periodic_refresh(self):
        try:
            self.refresh_all()
            self.update_logs()
        except Exception as e:
            print("GUI refresh error:", e)
        finally:
            self.master.after(AUTO_REFRESH_MS, self.periodic_refresh)

    def refresh_all(self):
        self.load_confirmations()
        self.load_orders()
        self.load_raw()

    def load_confirmations(self):
        try:
            rows = fetch_confirmations(limit=500)
            self.tree_conf.delete(*self.tree_conf.get_children())
            self.confirmations_data = []
            
            for r in rows:
                # r: (id, po_number, material, confirmed_qty, final_flag, payload, created_at)
                payload = r[5]
                # Store full data
                self.confirmations_data.append(r)
                
                # Convert payload dict to JSON string for display
                payload_str = json.dumps(payload, ensure_ascii=False) if payload else ""
                # Truncate for display
                if len(payload_str) > 200:
                    payload_str = payload_str[:200] + "..."
                
                # Insert with payload column included
                self.tree_conf.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4], payload_str, r[6]))
        except Exception as e:
            print("Error loading confirmations:", e)

    def load_orders(self):
        try:
            rows = fetch_orders(limit=200)
            self.tree_orders.delete(*self.tree_orders.get_children())
            self.orders_data = []
            
            for r in rows:
                # r: (id, payload, created_at)
                self.orders_data.append(r)
                
                payload_str = json.dumps(r[1], ensure_ascii=False) if r[1] else ""
                if len(payload_str) > 200:
                    payload_str = payload_str[:200] + "..."
                self.tree_orders.insert("", "end", values=(r[0], payload_str, r[2]))
        except Exception as e:
            print("Error loading orders:", e)

    def load_raw(self):
        try:
            rows = fetch_raw(limit=200)
            self.tree_raw.delete(*self.tree_raw.get_children())
            self.raw_data = []
            
            for r in rows:
                self.raw_data.append(r)
                
                payload_str = json.dumps(r[1], ensure_ascii=False) if r[1] else ""
                if len(payload_str) > 200:
                    payload_str = payload_str[:200] + "..."
                self.tree_raw.insert("", "end", values=(r[0], payload_str, r[2]))
        except Exception as e:
            print("Error loading raw data:", e)

    def on_confirmation_double_click(self, event):
        """Handle double-click on confirmation row"""
        selection = self.tree_conf.selection()
        if not selection:
            return
        
        item = self.tree_conf.item(selection[0])
        row_id = item['values'][0]  # Get the id from first column
        
        # Find the full data for this row
        for r in self.confirmations_data:
            if r[0] == row_id:
                payload = r[5]
                PayloadViewerDialog(self.master, f"Confirmation Payload - ID: {row_id}", payload)
                break

    def on_orders_double_click(self, event):
        """Handle double-click on orders row"""
        selection = self.tree_orders.selection()
        if not selection:
            return
        
        item = self.tree_orders.item(selection[0])
        row_id = item['values'][0]
        
        for r in self.orders_data:
            if r[0] == row_id:
                payload = r[1]
                PayloadViewerDialog(self.master, f"Order Payload - ID: {row_id}", payload)
                break

    def on_raw_double_click(self, event):
        """Handle double-click on raw data row"""
        selection = self.tree_raw.selection()
        if not selection:
            return
        
        item = self.tree_raw.item(selection[0])
        row_id = item['values'][0]
        
        for r in self.raw_data:
            if r[0] == row_id:
                payload = r[1]
                PayloadViewerDialog(self.master, f"Raw Data Payload - ID: {row_id}", payload)
                break

    def update_logs(self):
        appended = 0
        try:
            while True:
                line = LOG_QUEUE.get_nowait()
                self.txt_log.insert("end", line + "\n")
                appended += 1
                # keep log text length manageable
                if int(self.txt_log.index('end-1c').split('.')[0]) > 2000:
                    self.txt_log.delete('1.0', '2.0')
        except Empty:
            pass

    # Clearing helpers (dangerous, for testing only)
    def clear_confirmations_prompt(self):
        if messagebox.askyesno("Clear confirmations", "Delete ALL rows from confirmations table?"):
            self.clear_confirmations()

    def clear_confirmations(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM confirmations")
        conn.commit()
        cur.close()
        conn.close()
        self.refresh_all()
        log("All confirmations cleared via GUI")

    def clear_raw_prompt(self):
        if messagebox.askyesno("Clear raw data", "Delete ALL rows from raw_data table?"):
            self.clear_raw()

    def clear_raw(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM raw_data")
        conn.commit()
        cur.close()
        conn.close()
        self.refresh_all()
        log("All raw_data cleared via GUI")

    def clear_orders_prompt(self):
        if messagebox.askyesno("Clear orders", "Delete ALL rows from orders table?"):
            self.clear_orders()

    def clear_orders(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM orders")
        conn.commit()
        cur.close()
        conn.close()
        self.refresh_all()
        log("All orders cleared via GUI")

# -------------------------
# Main
# -------------------------
def main():
    # init DB (safe - creates tables if missing)
    init_db()

    # start Flask server in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    log("Flask mock SAP server started in background thread.")

    # start Tkinter GUI in main thread
    root = tk.Tk()
    gui = DemoSAPGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
