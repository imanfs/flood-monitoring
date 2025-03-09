import requests
import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import concurrent.futures
import re


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

        # Group data by measure to reduce processing time
        measures_data = {}
        for reading in station_readings:
            measure = self.get_measure_id(reading)
            if measure not in measures_data:
                measures_data[measure] = {
                    "timestamps": [],
                    "values": [],
                    "measure_url": reading["measure"],
                }

            measures_data[measure]["timestamps"].append(reading["dateTime"])
            measures_data[measure]["values"].append(reading["value"])

        # Fetch all measure metadata concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_measure = {
                executor.submit(self.retrieve_metadata, data["measure_url"]): measure
                for measure, data in measures_data.items()
            }

            for future in concurrent.futures.as_completed(future_to_measure):
                measure = future_to_measure[future]
                try:
                    self.measure_metadata[measure] = future.result()
                except Exception as exc:
                    st.error(f"Error retrieving metadata for {measure}: {exc}")

        # Process and store the results
        for measure, data in measures_data.items():
            self.readings[measure] = {
                "timestamps": data["timestamps"],
                "values": data["values"],
            }

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
        """Creates a formatted measure label based on metadata."""
        return f"{measure_metadata['parameterName']} - {measure_metadata['qualifier']}"

    def create_station_label(self, station_id):
        """Creates a formatted station label based on station name and ID."""
        return f"{station_id}: {tool.stations[station_id]}"

    def get_station_info(self):
        """Extracts key station information for display."""
        station_info = {}
        if hasattr(self, "station_metadata"):
            info_keys = [
                "town",
                "riverName",
                "eaAreaName",
                "eaRegionName",
                "catchmentName",
            ]
            for key in info_keys:
                if key in self.station_metadata:
                    # convert camelCase to Title Case
                    display_key = " ".join(
                        word.capitalize() for word in re.findall(r"[A-Z]?[a-z]+", key)
                    )
                    station_info[display_key] = self.station_metadata[key]
        return station_info


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

    measure_name = st.selectbox(
        "Select Measure", measures, format_func=get_measure_name
    )  # Use format_func to display the formatted name

    # Fetch and plot data when the measure is selected
    if measure_name:
        st.subheader("Station Information")
        station_info = tool.get_station_info()

        # Create two columns for cleaner station info display
        col1, col2 = st.columns(2)

        with col1:
            if "Town" in station_info:
                st.write(f"**Town:** {station_info['Town']}")
            if "River Name" in station_info:
                st.write(f"**River:** {station_info['River Name']}")

        with col2:
            if "Ea Area Name" in station_info:
                st.write(f"**Area:** {station_info['Ea Area Name']}")
            if "Ea Region Name" in station_info:
                st.write(f"**Region:** {station_info['Ea Region Name']}")

        if "Catchment Name" in station_info:
            st.write(f"**Catchment:** {station_info['Catchment Name']}")

        st.markdown("---")  # Horizontal line to separate info from data

        st.subheader(
            f"Measurement Data: {tool.create_measure_label(tool.measure_metadata[measure_name])}"
        )

        df = pd.DataFrame(tool.readings[measure_name])
        st.write(df)  # Display the data in a table
        tool.plot_measure(df)  # Plot the data
