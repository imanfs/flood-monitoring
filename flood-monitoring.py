import requests
import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st


class MeasurementTool:
    def __init__(
        self,
    ):
        self.root = "https://environment.data.gov.uk/flood-monitoring"
        self.page_url = self.root + "/id/stations/"
        self.session = requests.Session()  # Use a session for connection pooling
        self.last_24_hrs = self.subtract_24h_from_now()

        self.stations = self._initialize_stations()

    def _initialize_stations(self):
        """Initialize stations dictionary with caching.
        Maps station label to its reference code."""
        page = self.session.get(self.page_url)
        entries = page.json()["items"]

        stations_data = {}
        for entry in entries:
            label = entry["label"]
            if isinstance(label, list):
                label = entry["label"][0]
            stations_data[entry["stationReference"]] = label.title()
        return stations_data

    def retrieve_metadata(self, url):
        """Retrieve and cache metadata."""
        page = self.session.get(url)
        return page.json()["items"]

    def retrieve_station_data(self, station_id):
        """
        Returns the last 24 hours of recordings for a given station.
        """
        self.readings = {}
        self.measure_metadata = {}

        station_url = self.page_url + station_id
        self.station_metadata = self.retrieve_metadata(station_url)

        station_page = self.session.get(
            f"{station_url}/readings?since={self.last_24_hrs}"
        )
        station_readings = station_page.json()["items"]

        for reading in station_readings:
            measure = self.get_measure_id(reading)
            if measure not in self.readings.keys():
                # initialise empty inner dict to hold timestamps,metadata and values
                self.readings[measure] = {}
                (
                    self.readings[measure]["timestamps"],
                    self.readings[measure]["values"],
                ) = [], []
                self.measure_metadata[measure] = self.retrieve_metadata(
                    reading["measure"]
                )

            self.readings[measure]["timestamps"].append(reading["dateTime"])
            self.readings[measure]["values"].append(reading["value"])

    def get_rounded_current_time(self):
        """
        Returns the current timestamp rounded down to the nearest 15-minute increment.
        """
        now = dt.datetime.now(dt.timezone.utc)
        rounded_minutes = now.minute - (
            now.minute % 15
        )  # Round down to nearest 15-minute mark
        rounded_time = now.replace(minute=rounded_minutes, second=0, microsecond=0)
        return rounded_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def subtract_24h_from_now(self):
        """
        Subtracts 24 hours from a given timestamp and returns it in the same format.
        """
        curr_timestamp_rounded = (
            self.get_rounded_current_time()
        )  # rounded down to last 15 m interval
        datetime = dt.datetime.strptime(curr_timestamp_rounded, "%Y-%m-%dT%H:%M:%SZ")
        new_dt = datetime - dt.timedelta(hours=24)
        return new_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def plot_measure(self, df):
        """Plots the time series data."""

        df = df.sort_values("timestamps")
        df["timestamps"] = pd.to_datetime(df["timestamps"])

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df["timestamps"], df["values"], marker="o", linestyle="-")

        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Value")
        ax.set_title("Time Series Data")
        plt.xticks(rotation=45)  # readability
        ax.grid()
        plt.tight_layout()
        st.pyplot(fig)

    def get_measure_id(self, data):
        """
        Retrieves the unique identifier used for a measure.
        eg. {root}/id/measures/1029TH-level-downstage-i-15_min -> level-downstage-i-15_min
        """
        return "-".join(data["measure"].split("/")[-1].split("-")[1:])

    def create_measure_label(self, measure_metadata):
        """
        Creates a formatted measure label based on metadata.
        """
        return f"{measure_metadata['parameterName']} - {measure_metadata['qualifier']}"

    def create_station_label(self, station_id):
        """
        Creates a formatted station labebl based on station name and ID.
        """
        return f"{station_id}: {tool.stations[station_id]}"


# Create an instance of MeasurementTool
tool = MeasurementTool()

# Streamlit interactive UI
st.title("Flood Monitoring Station Data")


def get_station_name(station_id):
    return tool.create_station_label(station_id)


# Dropdown for station selection
station_id = st.selectbox(
    "Select Station", tool.stations.keys(), format_func=get_station_name
)


# Only show the measure selector if a station is selected
if station_id:
    # Retrieve measurements for the selected station
    tool.retrieve_station_data(station_id)

    # Get the list of available measures (keys from `self.data`)
    measures = list(tool.readings.keys())

    def get_measure_name(measure_id):
        return tool.create_measure_label(tool.measure_metadata[measure_id])

    # Use format_func to display the friendly name
    measure_name = st.selectbox(
        "Select Measure", measures, format_func=get_measure_name
    )

    # Fetch and plot data when the measure is selected
    if measure_name:
        df = pd.DataFrame(tool.readings[measure_name])
        st.write(df)  # Display the data in a table
        tool.plot_measure(df)  # Plot the data
