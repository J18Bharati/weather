import re
import sys
from datetime import datetime, date, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox

from weather import Weather
from location import get_coordinates_from_zip, get_coordinates_from_city
from database import WeatherDatabase


class InputWidget(BoxLayout):
    """
    Widget for user input of ZIP code and weather data retrieval.
    
    Provides a horizontal layout with:
    - ZIP code input field
    - "Get Weather" button
    
    Attributes:
        zip_input: TextInput widget for ZIP code entry
        fetch_button: Button widget to trigger weather data fetch
    """
    def __init__(self, fetch_callback, **kwargs):
        """
        Initialize the InputWidget.
        
        Args:
            fetch_callback: Function to be called when weather data is requested
            **kwargs: Additional keyword arguments passed to BoxLayout
        """
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = "40dp"

        self.zip_input = TextInput(
            hint_text="(US) ZIP Code or City, State",
            multiline=False,
            size_hint=(0.7, 1),
            font_size="18sp",
        )
        self.fetch_button = Button(
            text="Get Weather",
            size_hint=(0.3, 1),
            font_size="18sp",
        )
        self.fetch_button.bind(on_press=lambda _: fetch_callback(self.zip_input.text.strip()))
        self.add_widget(self.zip_input)
        self.add_widget(self.fetch_button)


class WeatherInfoWidget(BoxLayout):
    """
    Widget for displaying current weather information.
    
    Displays weather data in a two-column layout:
    - Left column: Temperature and wind information
    - Right column: Detailed weather description
    
    Attributes:
        temp_label: Label for displaying temperature
        wind_label: Label for displaying wind information
        forecast_label: Label for displaying weather description
    """
    def __init__(self, **kwargs):
        """
        Initialize the WeatherInfoWidget.
        
        Args:
            **kwargs: Additional keyword arguments passed to BoxLayout
        """
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.spacing = 10
        self.size_hint_y = None
        self.height = "180dp"  # reserve space for temp+wind on left, forecast on right

        # Left column: temperature above wind
        left_column = BoxLayout(orientation="vertical", spacing=5, size_hint_x=0.5)

        self.temp_label = Label(
            text="",
            font_size="48sp",
            halign="center",
            valign="middle",
            size_hint_y=0.6,
        )
        self.temp_label.bind(size=self._update_label_text_size)

        self.wind_label = Label(
            text="",
            font_size="16sp",
            halign="center",
            valign="middle",
            size_hint_y=0.4,
        )
        self.wind_label.bind(size=self._update_label_text_size)

        left_column.add_widget(self.temp_label)
        left_column.add_widget(self.wind_label)

        # Right column: forecast spans entire left_column height
        self.forecast_label = Label(
            text="",
            font_size="16sp",
            halign="left",
            valign="top",
            padding=(10, 10),
            size_hint_x=0.5,
        )
        self.forecast_label.bind(size=self._update_forecast_text_size)

        self.add_widget(left_column)
        self.add_widget(self.forecast_label)

    def _update_label_text_size(self, instance, _):
        instance.text_size = instance.size

    def _update_forecast_text_size(self, instance, _):
        instance.text_size = (instance.width * 0.95, None)

    def update(self, temp: str, wind: str, forecast: str):
        """
        Update the weather information display.
        
        Args:
            temp: Temperature string
            wind: Wind information string
            forecast: Weather description string
        """
        self.temp_label.text = temp
        self.wind_label.text = wind
        self.forecast_label.text = forecast


class ForecastListWidget(ScrollView):
    """
    Scrollable widget for displaying future weather forecasts.
    
    Each forecast entry includes:
    - Time period name
    - Temperature
    - Wind information
    - Short weather description
    
    Attributes:
        container: BoxLayout containing all forecast entries
    """
    def __init__(self, **kwargs):
        """
        Initialize the ForecastListWidget.
        
        Args:
            **kwargs: Additional keyword arguments passed to ScrollView
        """
        super().__init__(**kwargs)
        # ScrollView should expand vertically as needed
        self.size_hint = (1, 1)
        self.do_scroll_x = False
        self.do_scroll_y = True

        # Container for future‐forecast rows
        self.container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=10, padding=(0, 5))
        self.container.bind(minimum_height=self.container.setter("height"))
        self.add_widget(self.container)

    def populate(self, future_list):
        """
        Populate the forecast list with future weather forecasts.
        
        Args:
            future_list: List of dicts containing future weather forecasts
        """
        self.container.clear_widgets()
        for period in future_list:
            # Each row: [Name][Temp][Wind][ShortForecast]
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height="40dp", spacing=10)

            name_label = Label(
                text=period["name"],
                font_size="12sp",
                size_hint_x=0.25,
                halign="left",
                valign="middle",
            )
            name_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, inst.size))

            temp_label = Label(
                text=f"{period['temperature']}°F",
                font_size="12sp",
                size_hint_x=0.15,
                halign="center",
                valign="middle",
            )
            temp_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, inst.size))

            wind_label = Label(
                text=f"{period['wind_speed']} {period['wind_direction']}",
                font_size="12sp",
                size_hint_x=0.25,
                halign="left",
                valign="middle",
            )
            wind_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, inst.size))

            short_label = Label(
                text=period["forecast"],
                font_size="12sp",
                size_hint_x=0.35,
                halign="left",
                valign="middle",
            )
            short_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, inst.size))

            row.add_widget(name_label)
            row.add_widget(temp_label)
            row.add_widget(wind_label)
            row.add_widget(short_label)
            self.container.add_widget(row)


class ConfirmUpdatePopup(Popup):
    """
    Popup for confirming record updates when duplicates exist
    """
    def __init__(self, location, date_str, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Record Already Exists"
        self.size_hint = (0.7, 0.5)
        self.callback = callback
        
        main_layout = BoxLayout(orientation="vertical", spacing=15, padding=10)
        
        message_label = Label(
            text=f"A weather record for {location} on {date_str} already exists.\n\nDo you want to update it?",
            font_size="16sp",
            halign="center",
            valign="middle",
            text_size=(None, None)
        )
        message_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, (inst.width, None)))
        
        button_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height="50dp", spacing=10)
        
        update_btn = Button(text="Update", size_hint_x=0.5)
        update_btn.bind(on_press=lambda x: self.confirm_update(True))
        
        cancel_btn = Button(text="Cancel", size_hint_x=0.5)
        cancel_btn.bind(on_press=lambda x: self.confirm_update(False))
        
        button_layout.add_widget(update_btn)
        button_layout.add_widget(cancel_btn)
        
        main_layout.add_widget(message_label)
        main_layout.add_widget(button_layout)
        
        self.content = main_layout
    
    def confirm_update(self, update):
        """Handle user's choice"""
        self.callback(update)
        self.dismiss()


class SaveRecordsPopup(Popup):
    """
    Popup for selecting date range to save weather records
    """
    def __init__(self, weather_data, location, save_callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Save Weather Records"
        self.size_hint = (0.8, 0.7)
        self.weather_data = weather_data
        self.location = location
        self.save_callback = save_callback
        
        # Main layout
        main_layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        
        # Instructions
        instruction_label = Label(
            text=f"Select dates to save weather records for {location}:",
            size_hint_y=None,
            height="30dp",
            font_size="16sp"
        )
        main_layout.add_widget(instruction_label)
        
        # Date selection area
        scroll = ScrollView()
        date_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        date_container.bind(minimum_height=date_container.setter("height"))
        
        self.date_checkboxes = {}
        today = date.today()
        
        # Create checkboxes for today through next week (8 days total)
        for i in range(8):
            check_date = today + timedelta(days=i)
            date_str = check_date.strftime("%Y-%m-%d")
            day_name = check_date.strftime("%A, %B %d, %Y")
            
            # Find matching weather data for this date
            matching_forecast = None
            for forecast in weather_data:
                if forecast.get('daytime', True):  # Only save daytime forecasts
                    matching_forecast = forecast
                    break
            
            if matching_forecast:
                row = BoxLayout(orientation="horizontal", size_hint_y=None, height="40dp")
                
                checkbox = CheckBox(size_hint_x=None, width="40dp")
                self.date_checkboxes[date_str] = {
                    'checkbox': checkbox, 
                    'forecast': matching_forecast
                }
                
                date_label = Label(
                    text=day_name,
                    size_hint_x=0.7,
                    halign="left",
                    valign="middle"
                )
                date_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, inst.size))
                
                temp_label = Label(
                    text=f"{matching_forecast['temperature']}°F",
                    size_hint_x=0.2,
                    halign="center",
                    valign="middle"
                )
                
                row.add_widget(checkbox)
                row.add_widget(date_label)
                row.add_widget(temp_label)
                date_container.add_widget(row)
        
        scroll.add_widget(date_container)
        main_layout.add_widget(scroll)
        
        # Buttons
        button_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height="50dp", spacing=10)
        
        select_all_btn = Button(text="Select All", size_hint_x=0.3)
        select_all_btn.bind(on_press=self.select_all)
        
        save_btn = Button(text="Save Selected", size_hint_x=0.4)
        save_btn.bind(on_press=self.save_selected)
        
        cancel_btn = Button(text="Cancel", size_hint_x=0.3)
        cancel_btn.bind(on_press=self.dismiss)
        
        button_layout.add_widget(select_all_btn)
        button_layout.add_widget(save_btn)
        button_layout.add_widget(cancel_btn)
        
        main_layout.add_widget(button_layout)
        self.content = main_layout
    
    def select_all(self, instance):
        """Select all checkboxes"""
        for date_info in self.date_checkboxes.values():
            date_info['checkbox'].active = True
    
    def save_selected(self, instance):
        """Save selected weather records"""
        selected_count = 0
        for date_str, date_info in self.date_checkboxes.items():
            if date_info['checkbox'].active:
                forecast = date_info['forecast']
                success = self.save_callback(
                    self.location,
                    date_str,
                    forecast['temperature'],
                    forecast['wind_speed'],
                    forecast['wind_direction'],
                    forecast['forecast']
                )
                if success:
                    selected_count += 1
        
        # Show success message
        if selected_count > 0:
            success_popup = Popup(
                title="Success",
                content=Label(text=f"Saved {selected_count} weather record(s)!"),
                size_hint=(0.6, 0.4)
            )
            success_popup.open()
        
        self.dismiss()


class ViewRecordsPopup(Popup):
    """
    Popup for viewing saved weather records with delete functionality
    """
    def __init__(self, records, parent_app, **kwargs):
        super().__init__(**kwargs)
        self.title = "Saved Weather Records"
        self.size_hint = (0.9, 0.8)
        self.parent_app = parent_app  # Reference to main app for database operations
        self.records = records  # Store records for refresh
        self.record_checkboxes = {}  # Store checkboxes for each record
        
        self.build_content()
    
    def build_content(self):
        """Build the popup content"""
        main_layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        
        if not self.records:
            no_records_label = Label(
                text="No weather records saved yet.",
                font_size="18sp",
                halign="center",
                valign="middle"
            )
            main_layout.add_widget(no_records_label)
        else:
            # Header with select all checkbox
            header_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height="40dp")
            
            self.select_all_checkbox = CheckBox(size_hint_x=None, width="40dp")
            self.select_all_checkbox.bind(active=self.on_select_all)
            
            header_label = Label(
                text=f"Total Records: {len(self.records)} (Select All)",
                font_size="16sp",
                halign="left",
                valign="middle"
            )
            header_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, inst.size))
            
            header_layout.add_widget(self.select_all_checkbox)
            header_layout.add_widget(header_label)
            main_layout.add_widget(header_layout)
            
            # Records list
            scroll = ScrollView()
            records_container = BoxLayout(
                orientation="vertical", 
                size_hint_y=None, 
                spacing=5,
                padding=(5, 5)
            )
            records_container.bind(minimum_height=records_container.setter("height"))
            
            self.record_checkboxes.clear()
            
            for i, record in enumerate(self.records):
                record_row = BoxLayout(
                    orientation="vertical", 
                    size_hint_y=None, 
                    height="120dp",  
                    padding=(10, 5)
                )
                
                # Checkbox and location/date row
                checkbox_location_row = BoxLayout(orientation="horizontal", size_hint_y=0.3)
                
                checkbox = CheckBox(size_hint_x=None, width="40dp")
                self.record_checkboxes[i] = checkbox
                
                location_label = Label(
                    text=record['location'],
                    font_size="14sp",
                    bold=True,
                    size_hint_x=0.5,
                    halign="left",
                    valign="middle"
                )
                location_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, inst.size))
                
                date_label = Label(
                    text=record['date'],
                    font_size="14sp",
                    size_hint_x=0.5,
                    halign="right",
                    valign="middle"
                )
                date_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, inst.size))
                
                checkbox_location_row.add_widget(checkbox)
                checkbox_location_row.add_widget(location_label)
                checkbox_location_row.add_widget(date_label)
                
                # Weather details row
                details_row = BoxLayout(orientation="horizontal", size_hint_y=0.4)
                
                temp_label = Label(
                    text=f"{record['temperature']}°F",
                    font_size="12sp",
                    size_hint_x=0.3,
                    halign="left",
                    valign="middle"
                )
                
                wind_label = Label(
                    text=f"{record['wind_speed']} {record['wind_direction']}",
                    font_size="12sp",
                    size_hint_x=0.4,
                    halign="center",
                    valign="middle"
                )
                
                forecast_label = Label(
                    text=record['forecast'][:30] + "..." if len(record['forecast']) > 30 else record['forecast'],
                    font_size="12sp",
                    size_hint_x=0.3,
                    halign="right",
                    valign="middle"
                )
                forecast_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, inst.size))
                
                details_row.add_widget(temp_label)
                details_row.add_widget(wind_label)
                details_row.add_widget(forecast_label)
                
                record_row.add_widget(checkbox_location_row)
                record_row.add_widget(details_row)
                
                # Add separator line
                separator = Label(text="─" * 50, size_hint_y=None, height="10dp", font_size="10sp")
                
                records_container.add_widget(record_row)
                records_container.add_widget(separator)
            
            scroll.add_widget(records_container)
            main_layout.add_widget(scroll)
        
        # Bottom buttons
        button_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height="50dp", spacing=10)
        
        delete_selected_btn = Button(
            text="Delete Selected",
            size_hint_x=0.4,
            background_color=(1, 0.3, 0.3, 1)  # Red color
        )
        delete_selected_btn.bind(on_press=self.confirm_delete_selected)
        
        close_btn = Button(text="Close", size_hint_x=0.6)
        close_btn.bind(on_press=self.dismiss)
        
        button_layout.add_widget(delete_selected_btn)
        button_layout.add_widget(close_btn)
        
        main_layout.add_widget(button_layout)
        
        self.content = main_layout
    
    def on_select_all(self, checkbox, value):
        """Handle select all checkbox"""
        for record_checkbox in self.record_checkboxes.values():
            record_checkbox.active = value
    
    def get_selected_records(self):
        """Get list of selected records"""
        selected = []
        for i, checkbox in self.record_checkboxes.items():
            if checkbox.active:
                selected.append(self.records[i])
        return selected
    
    def confirm_delete_selected(self, instance):
        """Show confirmation dialog before deleting selected records"""
        selected_records = self.get_selected_records()
        if not selected_records:
            no_selection_popup = Popup(
                title="No Selection",
                content=Label(text="Please select at least one record to delete."),
                size_hint=(0.6, 0.4)
            )
            no_selection_popup.open()
            return
        
        confirm_popup = BulkDeleteConfirmationPopup(
            selected_records, 
            self.delete_selected_records
        )
        confirm_popup.open()
    
    def delete_selected_records(self, selected_records):
        """Delete multiple selected records from the database"""
        success_count = 0
        for record in selected_records:
            success = self.parent_app.db.delete_record(record['location'], record['date'])
            if success:
                success_count += 1
        
        if success_count > 0:
            # Remove deleted records from our list
            remaining_records = []
            deleted_keys = set((r['location'], r['date']) for r in selected_records if 
                             any(self.parent_app.db.delete_record(r['location'], r['date']) for r in selected_records))
            
            # Refresh records from database to ensure accuracy
            self.records = self.parent_app.db.get_all_records()
            
            # Rebuild the content
            self.clear_widgets()
            self.build_content()
            
            # Show success message
            success_popup = Popup(
                title="Deleted",
                content=Label(text=f"Successfully deleted {success_count} record(s)!"),
                size_hint=(0.7, 0.4)
            )
            success_popup.open()
            
            # Close the records display window after a short delay
            Clock.schedule_once(lambda dt: self.dismiss(), 0.5)
        else:
            # Show error message
            error_popup = Popup(
                title="Error",
                content=Label(text="Failed to delete the selected records!"),
                size_hint=(0.6, 0.4)
            )
            error_popup.open()


class BulkDeleteConfirmationPopup(Popup):
    """
    Popup for confirming bulk record deletion
    """
    def __init__(self, selected_records, delete_callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Confirm Bulk Delete"
        self.size_hint = (0.8, 0.6)
        self.selected_records = selected_records
        self.delete_callback = delete_callback
        
        main_layout = BoxLayout(orientation="vertical", spacing=15, padding=10)
        
        message_label = Label(
            text=f"Are you sure you want to delete {len(selected_records)} weather record(s)?\n\nThis action cannot be undone.",
            font_size="16sp",
            halign="center",
            valign="middle",
            text_size=(None, None)
        )
        message_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, (inst.width, None)))
        
        # Show list of records to be deleted
        if len(selected_records) <= 5:  # Only show details if not too many
            records_text = "\n".join([f"• {r['location']} on {r['date']}" for r in selected_records])
            records_label = Label(
                text=f"Records to delete:\n{records_text}",
                font_size="14sp",
                halign="center",
                valign="middle",
                text_size=(None, None)
            )
            records_label.bind(size=lambda inst, _: inst.setter("text_size")(inst, (inst.width, None)))
            main_layout.add_widget(records_label)
        
        button_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height="50dp", spacing=10)
        
        delete_btn = Button(
            text="Delete All", 
            size_hint_x=0.5,
            background_color=(1, 0.3, 0.3, 1)  # Red color
        )
        delete_btn.bind(on_press=lambda x: self.confirm_delete())
        
        cancel_btn = Button(text="Cancel", size_hint_x=0.5)
        cancel_btn.bind(on_press=lambda x: self.dismiss())
        
        button_layout.add_widget(delete_btn)
        button_layout.add_widget(cancel_btn)
        
        main_layout.add_widget(message_label)
        main_layout.add_widget(button_layout)
        
        self.content = main_layout
    
    def confirm_delete(self):
        """Handle user's confirmation to delete all selected records"""
        self.delete_callback(self.selected_records)
        self.dismiss()

class TemperatureDisplay(BoxLayout):
    def __init__(self, **kwargs):
        """
        Initialize the TemperatureDisplay.
        
        Args:
            **kwargs: Additional keyword arguments passed to BoxLayout
        """
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 20
        self.spacing = 10

        # Initialize database
        self.db = WeatherDatabase()
        
        # Store current weather data and weather object for saving
        self.current_weather_data = None
        self.current_weather_obj = None
        self.pending_save_info = None  # For handling duplicate confirmation

        self.input_widget = InputWidget(self.on_fetch_weather)
        self.weather_info = WeatherInfoWidget()
        self.forecast_list = ForecastListWidget()
        
        # Bottom buttons layout
        button_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height="50dp", spacing=10)
        
        self.save_button = Button(
            text="Save Records",
            size_hint_x=0.25,
            font_size="16sp",
        )
        self.save_button.bind(on_press=self.on_save_records)
        
        self.view_button = Button(
            text="View Records",
            size_hint_x=0.25,
            font_size="16sp",
        )
        self.view_button.bind(on_press=self.on_view_records)
        
        self.export_button = Button(
            text="Export Records to XML",
            size_hint_x=0.25,
            font_size="16sp",
        )
        self.export_button.bind(on_press=self.on_export_records)

        self.info_button = Button(
            text="Info",
            size_hint_x=0.25,
            font_size="16sp",
        )
        self.info_button.bind(on_press=self.show_info_popup)
        
        button_layout.add_widget(self.save_button)
        button_layout.add_widget(self.view_button)
        button_layout.add_widget(self.export_button)
        button_layout.add_widget(self.info_button)

        # Add widgets: Input on top, then weather info, then future forecast list, then buttons
        self.add_widget(self.input_widget)
        self.add_widget(self.weather_info)
        self.add_widget(self.forecast_list)
        self.add_widget(button_layout)

        # Static bottom label
        nomen_label = Label(
            text="Jatin Bharati",
            size_hint_y=None,
            height="30dp",  # Adjust height as needed
            font_size="12sp", # Adjust font size as needed
            halign="center",
            valign="middle"
        )
        self.add_widget(nomen_label)

    def on_fetch_weather(self, zip_code):
        """
        Handle the weather data fetch request.
        
        Args:
            zip_code: ZIP code string
        """
        self.weather_info.update("Fetching...", "", "")
        self.forecast_list.container.clear_widgets()
        Clock.schedule_once(lambda dt: self._fetch_and_update(zip_code), 0)

    def _fetch_and_update(self, zip_code):
        """
        Fetch weather data and update the display.
        
        Args:
            zip_code: ZIP code string
        """
        current, future_list, desc, weather_obj = fetch_weather_data(zip_code)
        if current:
            temp = f"{current['temperature']}°F/{round((current['temperature'] - 32) * 10 / 9)/2}°C"
            wind = f"Wind: {current['wind_speed']} {current['wind_direction']}"
            self.weather_info.update(temp, wind, desc)
            self.forecast_list.populate(future_list)
            
            # Store data for saving
            self.current_weather_data = future_list
            self.current_weather_obj = weather_obj
            
        else:
            self.weather_info.update("Not found", "", "")
            self.forecast_list.container.clear_widgets()
            self.current_weather_data = None
            self.current_weather_obj = None

    def on_save_records(self, instance):
        """Handle save records button press"""
        if not self.current_weather_data or not self.current_weather_obj:
            error_popup = Popup(
                title="Error",
                content=Label(text="Please fetch weather data first!"),
                size_hint=(0.6, 0.4)
            )
            error_popup.open()
            return
        
        # Get location from weather object
        if self.current_weather_obj.current_city and self.current_weather_obj.current_state:
            location = f"{self.current_weather_obj.current_city}, {self.current_weather_obj.current_state}"
        else:
            location = "Unknown Location"
        
        # Open save records popup
        save_popup = SaveRecordsPopup(
            self.current_weather_data,
            location,
            self.save_weather_record
        )
        save_popup.open()

    def on_view_records(self, instance):
        """Handle view records button press"""
        records = self.db.get_all_records()
        view_popup = ViewRecordsPopup(records, self)
        view_popup.open()

    def on_export_records(self, instance):
        """Handle export records button press"""
        records = self.db.get_all_records()
        if not records:
            error_popup = Popup(
                title="No Records",
                content=Label(text="No weather records to export!"),
                size_hint=(0.6, 0.4)
            )
            error_popup.open()
            return
        
        success = self.export_records_to_xml(records)
        if success:
            success_popup = Popup(
                title="Export Successful",
                content=Label(text=f"Exported {len(records)} records to weather_records.xml"),
                size_hint=(0.7, 0.4)
            )
            success_popup.open()
        else:
            error_popup = Popup(
                title="Export Failed",
                content=Label(text="Failed to export records to XML file!"),
                size_hint=(0.6, 0.4)
            )
            error_popup.open()

    def export_records_to_xml(self, records):
        """
        Export weather records to XML file
        
        Args:
            records: List of weather record dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create root element
            root = ET.Element("weather_records")
            root.set("export_date", datetime.now().isoformat())
            root.set("total_records", str(len(records)))
            
            # Add each record
            for record in records:
                record_elem = ET.SubElement(root, "weather_record")
                
                # Add record fields as sub-elements
                ET.SubElement(record_elem, "location").text = record['location']
                ET.SubElement(record_elem, "date").text = record['date']
                ET.SubElement(record_elem, "temperature").text = str(record['temperature'])
                ET.SubElement(record_elem, "wind_speed").text = record['wind_speed']
                ET.SubElement(record_elem, "wind_direction").text = record['wind_direction']
                ET.SubElement(record_elem, "forecast").text = record['forecast']
                ET.SubElement(record_elem, "created_at").text = record['created_at']
            
            # Create tree and write to file with pretty formatting
            tree = ET.ElementTree(root)
            rough_string = ET.tostring(root, encoding='utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            # Remove the first line (XML declaration gets duplicated)
            pretty_xml = '\n'.join(pretty_xml.split('\n')[1:])
            
            with open("weather_records.xml", "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(pretty_xml)
            
            print(f"Exported {len(records)} records to weather_records.xml")
            return True
        except Exception as e:
            print(f"Error exporting to XML: {e}")
            return False

    def save_weather_record(self, location, date_str, temperature, wind_speed, wind_direction, forecast):
        """
        Save a weather record to the database
        
        Args:
            location: Location string
            date_str: Date string in YYYY-MM-DD format
            temperature: Temperature in Fahrenheit
            wind_speed: Wind speed string
            wind_direction: Wind direction string
            forecast: Weather forecast description
            
        Returns:
            True if successful, False otherwise
        """
        # Check if record already exists
        existing_records = self.db.get_records_by_location(location)
        duplicate_found = False
        
        for record in existing_records:
            if record['date'] == date_str:
                duplicate_found = True
                break
        
        if duplicate_found:
            # Store the save information for later use
            self.pending_save_info = {
                'location': location,
                'date_str': date_str,
                'temperature': temperature,
                'wind_speed': wind_speed,
                'wind_direction': wind_direction,
                'forecast': forecast
            }
            
            # Show confirmation popup
            confirm_popup = ConfirmUpdatePopup(
                location, 
                date_str, 
                self.handle_duplicate_confirmation
            )
            confirm_popup.open()
            return False  # Don't save yet, wait for confirmation
        else:
            # No duplicate, save directly
            return self.db.save_weather_record(location, date_str, temperature, wind_speed, wind_direction, forecast)

    def handle_duplicate_confirmation(self, should_update):
        """
        Handle the user's response to duplicate record confirmation
        
        Args:
            should_update: Boolean indicating if user wants to update the existing record
        """
        if should_update and self.pending_save_info:
            # User confirmed update, save the record
            success = self.db.save_weather_record(
                self.pending_save_info['location'],
                self.pending_save_info['date_str'],
                self.pending_save_info['temperature'],
                self.pending_save_info['wind_speed'],
                self.pending_save_info['wind_direction'],
                self.pending_save_info['forecast']
            )
            if success:
                update_popup = Popup(
                    title="Updated",
                    content=Label(text="Weather record updated successfully!"),
                    size_hint=(0.6, 0.4)
                )
                update_popup.open()
        
        # Clear pending save info
        self.pending_save_info = None

    def show_info_popup(self, instance):
        """Display an informational popup."""
        info_text = (
            "PM Accelerator\n\n"
            "A platform to transparently showcase PM skills to ease the "
            "application / hiring process for PMs and companies."
        )
        content_label = Label(
            text=info_text, 
            halign='center', 
            valign='top', 
            padding=(10, 10)
        )
        # Ensure text wraps in Label within Popup
        content_label.bind(size=lambda *args: setattr(content_label, 'text_size', (content_label.width - 20, None))) # subtract padding
        
        popup = Popup(
            title="Information",
            content=content_label,
            size_hint=(0.8, 0.6)
        )
        popup.open()


def fetch_weather_data(zip_code: str):
    """
    Fetch weather data for the given ZIP code.
    
    Args:
        zip_code: 5-digit ZIP code string
        
    Returns:
      - current: dict or None
      - future_list: list of dicts (from get_future_forecast)
      - desc: string (e.g. text forecast)
      - weather_obj: Weather object for accessing location info
    """
    try:
        if re.fullmatch(r"\d{5}", zip_code):
            print(f"Fetching weather for ZIP code: {zip_code}")
            latitude, longitude = get_coordinates_from_zip(zip_code)
        else:
            city, state = zip_code.split(",")
            latitude, longitude = get_coordinates_from_city(city, state)
        if latitude is None or longitude is None:
            return None, [], "", None

        weather = Weather(latitude, longitude)
        current = weather.get_current_forecast()
        future_list = list(weather.get_future_forecast())
        desc = str(weather)
        return current, future_list, desc, weather
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None, [], "", None


class WeatherApp(App):
    def build(self):
        Window.size = (750, 550)
        return TemperatureDisplay()


if __name__ == "__main__":
    WeatherApp().run()