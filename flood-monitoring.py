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
        self.page = requests.get(self.page_url)
        self.entries = self.page.json()["items"]
        self.stations = self.create_stations_dict()
        self.data = {}
        self.metadata = {}
        latest_possible_reading_time = self.get_rounded_timestamp()
        self.last_24_hrs = self.subtract_24_hours(latest_possible_reading_time)

    def retrieve_measure_metadata(self, measure_url):
        station_page = requests.get(measure_url)
        return station_page.json()["items"]

    def retrieve_station_data(self, station_id):
        """
        Returns the last 24 hours of recordings for a given station.
        """
        station_url = self.page_url + station_id
        # self.metadata = self.retrieve_station_metadata(station_url)

        station_page = requests.get(station_url + "/readings?since=" + self.last_24_hrs)
        station_data = station_page.json()["items"]

        for datapoint in station_data:
            measure = self.get_measure_name(datapoint)
            if measure not in self.data.keys():
                # initialise empty inner dict to hold timestamps,metadata and values
                self.data[measure] = {}
                self.data[measure]["timestamps"], self.data[measure]["values"] = [], []
                self.metadata[measure] = self.retrieve_measure_metadata(
                    datapoint["measure"]
                )
            timestamp = datapoint["dateTime"]
            value = datapoint["value"]
            self.data[measure]["timestamps"].append(timestamp)
            self.data[measure]["values"].append(value)

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

    def get_measure_name(self, data):
        return "-".join(
            data["measure"].split("/")[-1].split("-")[1:]
        )  # Extract measure name

    def create_stations_dict(self):
        stations_data = {}
        for entry in self.entries:
            label = entry["label"]
            if isinstance(label, list):
                label = entry["label"][0]
            stations_data[entry["stationReference"]] = label.title()
        return stations_data

    def plot_measure(self, df):
        """Plots the time series data."""
        # Convert timestamp to datetime
        df = df.sort_values("timestamps")
        df["timestamps"] = pd.to_datetime(df["timestamps"])
        # Plot
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df["timestamps"], df["values"], marker="o", linestyle="-")

        # Formatting
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Value")
        ax.set_title("Time Series Data")
        plt.xticks(rotation=45)  # Rotate x-axis labels for readability
        ax.grid()
        plt.tight_layout()
        st.pyplot(fig)  # Display the plot

    def create_measure_label(self, measure_metadata):
        return measure_metadata["parameterName"] + " - " + measure_metadata["qualifier"]

    def create_station_label(self, station_id):
        return station_id + ": " + tool.stations[station_id]


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
    measures = list(tool.data.keys())

    def get_measure_name(measure_id):
        return tool.create_measure_label(tool.metadata[measure_id])

    # Use format_func to display the friendly name
    measure_name = st.selectbox(
        "Select Measure", measures, format_func=get_measure_name
    )

    # Fetch and plot data when the measure is selected
    if measure_name:
        df = pd.DataFrame(tool.data[measure_name])
        st.write(df)  # Display the data in a table
        tool.plot_measure(df)  # Plot the data
