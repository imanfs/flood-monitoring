import requests
import datetime as dt
import pandas as pd
from collections import defaultdict
import matplotlib.pyplot as plt
import streamlit as st


class MeasurementTool:
    def __init__(
        self,
    ):
        self.root = "https://environment.data.gov.uk/flood-monitoring"
        self.page_url = self.root + "/id/stations/"
        self.page = requests.get(self.page_url)
        self.entries = self.page.json()["items"]
        self.stations = self.create_stations_list()
        self.data = defaultdict(lambda: {"timestamps": [], "values": []})

    def retrieve_measurement(self, station_id):
        station_url = self.page_url + station_id
        latest_possible_reading_time = self.get_rounded_timestamp()
        last_24_hrs = self.subtract_24_hours(latest_possible_reading_time)
        station_page = requests.get(station_url + "/readings?since=" + last_24_hrs)
        station_data = station_page.json()["items"]

        for item in station_data:
            measure_name = "-".join(
                item["measure"].split("/")[-1].split("-")[1:]
            )  # Extract measure name
            timestamp = item["dateTime"]
            value = item["value"]
            self.data[measure_name]["timestamps"].append(timestamp)
            self.data[measure_name]["values"].append(value)

    def get_rounded_timestamp(self):
        """Returns the current timestamp rounded down to the nearest 15-minute increment."""
        now = dt.datetime.now(dt.timezone.utc)
        rounded_minutes = now.minute - (
            now.minute % 15
        )  # Round down to nearest 15-minute mark
        rounded_time = now.replace(minute=rounded_minutes, second=0, microsecond=0)
        return rounded_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def subtract_24_hours(self, timestamp: str) -> str:
        """Subtracts 24 hours from a given timestamp and returns it in the same format."""
        datetime = dt.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        new_dt = datetime - dt.timedelta(hours=24)
        return new_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def create_stations_list(self):
        stations = []
        station_ids = []
        for entry in self.entries:
            stations.append(entry["@id"])
            station_ids.append(entry["stationReference"])
        return station_ids

    def plot_measure(self, df):
        """Plots the time series data."""
        # Convert timestamp to datetime
        df["timestamps"] = pd.to_datetime(df["timestamps"])

        # Plot
        plt.figure(figsize=(10, 5))
        plt.plot(df["timestamps"], df["values"], marker="o", linestyle="-")

        # Formatting
        plt.xlabel("Timestamp")
        plt.ylabel("Value")
        plt.title("Time Series Data")
        plt.xticks(rotation=45)  # Rotate x-axis labels for readability
        plt.grid()
        plt.tight_layout()
        st.pyplot()  # Display the plot


# Create an instance of MeasurementTool
tool = MeasurementTool()

# Streamlit interactive UI
st.title("Flood Monitoring Station Data")

# Dropdown for station selection
station_id = st.selectbox("Select Station", tool.stations)

# Only show the measure selector if a station is selected
if station_id:
    # Retrieve measurements for the selected station
    tool.retrieve_measurement(station_id)

    # Get the list of available measures (keys from `self.data`)
    measures = list(tool.data.keys())

    # Dropdown for measure selection
    measure_name = st.selectbox("Select Measure", measures)

    # Fetch and plot data when the measure is selected
    if measure_name:
        df = pd.DataFrame(tool.data[measure_name])
        st.write(df)  # Display the data in a table
        tool.plot_measure(df)  # Plot the data
