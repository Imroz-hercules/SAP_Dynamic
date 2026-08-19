#!/usr/bin/env python3
"""
Database Configuration Reader for Hercules KPI
Reads database configuration from JSON file created during installation.
"""

import json
import os
from typing import Dict, Any, Optional

def load_database_config() -> Optional[Dict[str, Any]]:
    """
    Load database configuration from JSON file.
    Returns None if file doesn't exist or is invalid.
    """
    config_file = os.path.join(os.path.dirname(__file__), 'database_config.json')
    
    if not os.path.exists(config_file):
        print(f"⚠️ Database config file not found: {config_file}")
        return None
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"✅ Database configuration loaded from: {config_file}")
        return config
    except Exception as e:
        print(f"❌ Error loading database config: {e}")
        return None

def get_mssql_connection_string() -> Optional[str]:
    """Get MSSQL connection string from config"""
    config = load_database_config()
    if not config or 'mssql' not in config:
        return None
    
    mssql_config = config['mssql']
    username = mssql_config.get('username', '').strip()
    password = mssql_config.get('password', '').strip()
    
    # If username/password are empty, use Windows Authentication
    if not username or not password:
        return f"mssql+pyodbc://{mssql_config['server']}/{mssql_config['database']}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
    else:
        return f"mssql+pyodbc://{username}:{password}@{mssql_config['server']}/{mssql_config['database']}?driver=ODBC+Driver+17+for+SQL+Server"

def get_postgres_connection_string() -> Optional[str]:
    """Get PostgreSQL connection string from config"""
    config = load_database_config()
    if not config or 'postgresql' not in config:
        return None
    
    pg_config = config['postgresql']
    return f"postgresql://{pg_config['username']}:{pg_config['password']}@{pg_config['host']}:{pg_config['port']}/{pg_config['database']}"

def get_database_config() -> Dict[str, Any]:
    """Get complete database configuration"""
    config = load_database_config()
    if not config:
        # Return default configuration if no config file
        return {
            'mssql': {
                'server': 'localhost',
                'database': 'HerculesKPI',
                'username': 'sa',
                'password': ''
            },
            'postgresql': {
                'host': 'localhost',
                'port': '5432',
                'database': 'Hercules2',
                'username': 'postgres',
                'password': ''
            }
        }
    return config

if __name__ == "__main__":
    # Test the configuration reader
    config = load_database_config()
    if config:
        print("Database Configuration:")
        print(json.dumps(config, indent=2))
        
        mssql_conn = get_mssql_connection_string()
        if mssql_conn:
            print(f"\nMSSQL Connection String: {mssql_conn}")
        
        pg_conn = get_postgres_connection_string()
        if pg_conn:
            print(f"PostgreSQL Connection String: {pg_conn}")
    else:
        print("No database configuration found.")
