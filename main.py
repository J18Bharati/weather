import re
import sys

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

from weather import Weather
from location import get_coordinates_from_zip, get_coordinates_from_city


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

        self.input_widget = InputWidget(self.on_fetch_weather)
        self.weather_info = WeatherInfoWidget()
        self.forecast_list = ForecastListWidget()

        # Add widgets: Input on top, then weather info, then future forecast list
        self.add_widget(self.input_widget)
        self.add_widget(self.weather_info)
        self.add_widget(self.forecast_list)

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
        current, future_list, desc = fetch_weather_data(zip_code)
        if current:
            temp = f"{current['temperature']}°F/{round((current['temperature'] - 32) * 10 / 9)/2}°C"
            wind = f"Wind: {current['wind_speed']} {current['wind_direction']}"
            self.weather_info.update(temp, wind, desc)
            self.forecast_list.populate(future_list)
        else:
            self.weather_info.update("Not found", "", "")
            self.forecast_list.container.clear_widgets()


def fetch_weather_data(zip_code: str):
    """
    Fetch weather data for the given ZIP code.
    
    Args:
        zip_code: 5-digit ZIP code string
        
    Returns:
      - current: dict or None
      - future_list: list of dicts (from get_future_forecast)
      - desc: string (e.g. text forecast)
    """
    try:
        if re.fullmatch(r"\d{5}", zip_code):
            print(f"Fetching weather for ZIP code: {zip_code}")
            latitude, longitude = get_coordinates_from_zip(zip_code)
        else:
            city, state = zip_code.split(",")
            latitude, longitude = get_coordinates_from_city(city, state)
        if latitude is None or longitude is None:
            return None, [], ""

        weather = Weather(latitude, longitude)
        current = weather.get_current_forecast()
        future_list = list(weather.get_future_forecast())
        desc = str(weather)
        return current, future_list, desc
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None, [], ""


class WeatherApp(App):
    def build(self):
        Window.size = (720, 540)
        return TemperatureDisplay()


if __name__ == "__main__":
    WeatherApp().run()
