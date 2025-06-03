"""
Weather class that provides weather information using NWS API
"""

import requests
from typing import Optional, Dict, List
from datetime import datetime
import math

class Weather:
    """
    A class to fetch and provide weather information using NWS API
    
    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        self.forecast_url = None
        self.hourly_forecast_url = None
        self.forecast_data = None
        self.hourly_forecast_data = None
        self.current_city = None
        self.current_state = None
        self.update()

    def change_location(self, latitude: float, longitude: float) -> None:
        """Update the location information"""
        self.latitude = latitude
        self.longitude = longitude
        self.update()

    def update(self) -> None:
        """Get the grid point for the location"""
        try:
            url = f"https://api.weather.gov/points/{self.latitude},{self.longitude}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            properties = data['properties']
            
            # Store forecast URLs
            self.forecast_url = properties['forecast']
            self.hourly_forecast_url = properties.get('forecastHourly')
            
            # Store city and state information
            relative_location = properties.get('relativeLocation', {}).get('properties', {})
            self.current_city = relative_location.get('city')
            self.current_state = relative_location.get('state')

            print(f"Current location: {self.current_city}, {self.current_state}")
            print(f"Forecast URL: {self.forecast_url}")
            print(f"Hourly Forecast URL: {self.hourly_forecast_url}")

            self._update_forecast()
            self._update_hourly_forecast()

        except requests.RequestException as e:
            print(f"Error updating location: {e}")
            self.forecast_url = None
            self.hourly_forecast_url = None

    def _update_forecast(self) -> None:
        """
        Get the forecast data for the location
        """
        if not self.forecast_url:
            self._update()
            if not self.forecast_url:
                return

        try:
            response = requests.get(self.forecast_url)
            response.raise_for_status()
            self.forecast_data = response.json()['properties']['periods']
        except requests.RequestException as e:
            print(f"Error fetching forecast: {e}")
            self.forecast_data = None

    def _update_hourly_forecast(self) -> Optional[List[Dict]]:
        """
        Get hourly weather forecast
        """
        if not self.hourly_forecast_url:
            self._update()
            if not self.hourly_forecast_url:
                return None

        try:
            response = requests.get(self.hourly_forecast_url)
            response.raise_for_status()
            self.hourly_forecast_data = response.json()['properties']['periods']
            
        except requests.RequestException as e:
            print(f"Error fetching hourly forecast: {e}")
            self.hourly_forecast_data = None
    
    def get_current_forecast(self) -> Optional[Dict]:
        """
        Get the current forecast as a dictionary
        
        Returns:
            Dictionary containing current forecast information or None if not available
        """
        if not self.hourly_forecast_data:
            self._update_hourly_forecast()
            if not self.hourly_forecast_data:
                return None

        # Get the current period (first one in the list)
        current_period = self.hourly_forecast_data[0]
        
        return {
            'name': current_period['name'], # Included or the sake of consistency with get_future_forecast, would be an empty string
            'temperature': current_period['temperature'],
            'daytime': current_period['isDaytime'],
            'wind_speed': current_period['windSpeed'],
            'wind_direction': current_period['windDirection'],
            'precipitation_probability': current_period['probabilityOfPrecipitation']['value'],
            'forecast': current_period['shortForecast']
        }
    
    def get_future_forecast(self):
        """
        Yield future weather forecast 
        
        Yields:
            Dictionary containing future forecast information
        """
        if not self.forecast_data:
            self._update_forecast()
            if not self.forecast_data:
                return

        for period in self.forecast_data[1:]:

            yield {
                'name': period['name'],
                'temperature': period['temperature'],
                'daytime': period['isDaytime'],
                'wind_speed': period['windSpeed'],
                'wind_direction': period['windDirection'],
                'precipitation_probability': period['probabilityOfPrecipitation']['value'],
                'forecast': period['shortForecast']
            }

    def __str__(self):
        """Return a string representation of the current weather conditions"""
        period = self.forecast_data[0]
        return f"{period['name']}: {period['detailedForecast']}"
