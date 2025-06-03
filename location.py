"""
Location handling module that provides functions for converting zip codes and city/state to coordinates
"""

import pgeocode
from typing import Optional, Tuple
from geopy.geocoders import Nominatim

def get_coordinates_from_zip(zip_code: str, country: str = "US") -> Optional[Tuple[float, float]]:
    """
    Get coordinates from a zip code
    
    Args:
        zip_code: The zip/postal code
        country: The country code (default: US)
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    try:
        nomi = pgeocode.Nominatim(country)
        location = nomi.query_postal_code(zip_code)
        
        if location.empty:
            print(f"Zip code {zip_code} not found")
            return None
            
        return location.latitude.item(), location.longitude.item()
        
    except Exception as e:
        print(f"Error converting zip code: {e}")
        return None

def get_coordinates_from_city(city: str, state: str, country: str = "US") -> Optional[Tuple[float, float]]:
    """
    Get coordinates from city and state
    
    Args:
        city: The city name
        state: The state abbreviation
        country: The country code (default: US)
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    try:
        geolocator = Nominatim(user_agent="weather_app")
        location = geolocator.geocode(f"{city}, {state}, {country}")
        
        if not location:
            print(f"Location {city}, {state} not found")
            return None
            
        return location.latitude, location.longitude
        
    except Exception as e:
        print(f"Error converting city/state: {e}")
        return None
