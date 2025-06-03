"""
Location handling module that provides functions for converting zip codes and city/state to coordinates
"""

import pgeocode
from typing import Optional, Tuple
import zipcodes

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
    Get coordinates from city and state using zipcodes library with fuzzy matching
    
    Args:
        city: The city name
        state: The state name or abbreviation
        country: The country code (default: US)
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    try:
        # Clean and standardize input
        city = city.strip().title()
        state = state.strip()
        
        # Try to get state code from input (works with both abbreviation and full name)
        state_code = _get_state_code(state)
        if not state_code:
            # If state wasn't an abbreviation, try using it as is
            state_code = state.title()
            
        # First try exact match
        results = zipcodes.filter_by(city=city, state=state_code)
        
        # If no exact match, try fuzzy matching
        if not results:
            # Get all zipcodes for the state
            state_zips = zipcodes.filter_by(state=state_code)
            if not state_zips:
                print(f"No zipcodes found for state: {state_code}")
                return None
                
            # Try to find the closest matching city name
            for zip_entry in state_zips:
                if city.lower() in zip_entry['city'].lower():
                    return float(zip_entry['lat']), float(zip_entry['long'])
            
            print(f"Location {city}, {state} not found")
            return None
            
        # If we found results, return coordinates from first result
        coords = results[0]
        return float(coords['lat']), float(coords['long'])
        
    except Exception as e:
        print(f"Error converting city/state: {e}")
        return None

# Helper function to get state code from abbreviation or full name
def _get_state_code(state: str) -> Optional[str]:
    """Convert state name to abbreviation"""
    # Clean input
    state = state.strip()
    
    # Mapping of full state names to abbreviations
    state_mapping = {
        # Full names (lowercase for matching)
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY'
    }
    
    # If input is already an abbreviation, return it as is
    if len(state) == 2:
        return state.upper()
    
    # Try to get abbreviation from full name
    state_code = state_mapping.get(state.lower())
    if state_code:
        return state_code
    
    return None
