# Real-Time Flood-Monitoring Application
This Streamlit application provides an interactive interface to monitor water levels, flow rates, and other measurements from flood monitoring stations throughout the UK. 

## Data Source
This application this uses Environment Agency flood and river level data from the real-time flood-monitoring API (Beta). Data is refreshed every 15 minutes. 
See the docs for reference: https://environment.data.gov.uk/flood-monitoring/doc/reference.

## Usage
To run the application, run this command in terminal: 

```streamlit run flood-monitoring.py```

Select a monitoring station from the dropdown menu to load available measurements. Once loaded, select a specific measurement type to view detailed time series data and station information. 
