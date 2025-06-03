"""
Database handler for weather records using SQLite
"""

import sqlite3
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
import os

class WeatherDatabase:
    """
    Handle SQLite database operations for weather records
    """
    
    def __init__(self, db_path: str = "weather_records.db"):
        """
        Initialize the database connection and create tables if they don't exist
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create the weather records table if it doesn't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS weather_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        location TEXT NOT NULL,
                        date TEXT NOT NULL,
                        temperature INTEGER NOT NULL,
                        wind_speed TEXT NOT NULL,
                        wind_direction TEXT NOT NULL,
                        forecast TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(location, date)
                    )
                ''')
                conn.commit()
                print("Database initialized successfully")
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
    
    def save_weather_record(self, location: str, date_str: str, temperature: int, 
                          wind_speed: str, wind_direction: str, forecast: str = "") -> bool:
        """
        Save a weather record to the database
        
        Args:
            location: Location string (e.g., "City, State")
            date_str: Date string in YYYY-MM-DD format
            temperature: Temperature in Fahrenheit
            wind_speed: Wind speed string
            wind_direction: Wind direction string
            forecast: Weather forecast description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO weather_records 
                    (location, date, temperature, wind_speed, wind_direction, forecast)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (location, date_str, temperature, wind_speed, wind_direction, forecast))
                conn.commit()
                print(f"Weather record saved: {location} on {date_str}")
                return True
        except sqlite3.Error as e:
            print(f"Error saving weather record: {e}")
            return False
    
    def get_all_records(self) -> List[Dict]:
        """
        Retrieve all weather records from the database
        
        Returns:
            List of dictionaries containing weather records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT location, date, temperature, wind_speed, wind_direction, forecast, created_at
                    FROM weather_records
                    ORDER BY date DESC, location ASC
                ''')
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    records.append({
                        'location': row[0],
                        'date': row[1],
                        'temperature': row[2],
                        'wind_speed': row[3],
                        'wind_direction': row[4],
                        'forecast': row[5],
                        'created_at': row[6]
                    })
                return records
        except sqlite3.Error as e:
            print(f"Error retrieving records: {e}")
            return []
    
    def get_records_by_location(self, location: str) -> List[Dict]:
        """
        Retrieve weather records for a specific location
        
        Args:
            location: Location string to search for
            
        Returns:
            List of dictionaries containing weather records for the location
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT location, date, temperature, wind_speed, wind_direction, forecast, created_at
                    FROM weather_records
                    WHERE location LIKE ?
                    ORDER BY date DESC
                ''', (f'%{location}%',))
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    records.append({
                        'location': row[0],
                        'date': row[1],
                        'temperature': row[2],
                        'wind_speed': row[3],
                        'wind_direction': row[4],
                        'forecast': row[5],
                        'created_at': row[6]
                    })
                return records
        except sqlite3.Error as e:
            print(f"Error retrieving records by location: {e}")
            return []
    
    def delete_record(self, location: str, date_str: str) -> bool:
        """
        Delete a weather record from the database
        
        Args:
            location: Location string
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM weather_records
                    WHERE location = ? AND date = ?
                ''', (location, date_str))
                conn.commit()
                if cursor.rowcount > 0:
                    print(f"Deleted record: {location} on {date_str}")
                    return True
                else:
                    print(f"No record found to delete: {location} on {date_str}")
                    return False
        except sqlite3.Error as e:
            print(f"Error deleting record: {e}")
            return False
    
    def get_record_count(self) -> int:
        """
        Get the total number of weather records in the database
        
        Returns:
            Number of records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM weather_records')
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Error getting record count: {e}")
            return 0