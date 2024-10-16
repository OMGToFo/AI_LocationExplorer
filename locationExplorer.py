import streamlit as st
import folium
from streamlit_folium import folium_static

from folium.plugins import PolyLineTextPath

from geopy.geocoders import Nominatim
import openai
from openai import OpenAI
import pandas as pd
import re



#fetch location
from streamlit_js_eval import streamlit_js_eval, copy_to_clipboard, create_share_link, get_geolocation
import json

# Set up OpenAI API key
openai.api_key = st.text_input("Enter ChatGPT Api Key", value="")

if openai.api_key =="":
    st.info("Enter ChatGPTApi Key to start exploring and get some inspiration for a short trip."
            " Remember - ChatGPT sometimes hallucinates")
    st.stop()

client = OpenAI(
    # This is the default and can be omitted
    api_key=openai.api_key , )

lat=""
long=""
ActuallocationAdress=""
EndpointIsStartText=""
Actualaddress=""
transport=""
tourLengthText = ""



# Function to get latitude and longitude from a location name
def get_lat_long(location_name):
    geolocator = Nominatim(user_agent="ailocationxplorer")
    location = geolocator.geocode(location_name)
    if location:
        return location.latitude, location.longitude
    return None, None





# Function to generate the prompt for ChatGPT
def generate_prompt(lat, long, duration, pois):

    if EndpointIsStart == True:
        EndpointIsStartText = "The route should end at the starting point at {lat} and longitude {long}, "
    else:
        EndpointIsStartText =""


    poi_str = ', '.join(pois)
    return (f"just create a table with the columns Description,Latitude,Longitude, Duration and populate it with values from the route starting at latitude {lat} and longitude {long}, {EndpointIsStartText}, "  
            f"lasting for {duration} hours {transport}, {tourLengthText} with stops including: {poi_str} and write the exact name and adress of the stops for example name of restaurant into the table"
            f" after the table, write an informative description of the route")

#f" do not write any text in your answer in addition to the table"



# Function to call OpenAI API for route generation
def get_route(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",  # Use GPT-3.5 or GPT-4 (e.g., "gpt-4")
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,  # Adjust the length of the response as needed
    )
    return response.choices[0].message.content



# Function to parse ChatGPT table response into usable data

# Function to parse ChatGPT table response into usable data
def parse_table_response(response):
    # Split lines of the response
    lines = response.strip().split('\n')

    # Debugging output to see the lines
    #st.write("Response Lines:", lines)

    # Check if the response has at least the header and data
    if len(lines) < 3:
        st.error("Unexpected response format")
        return []

    table_data = []

    # Loop through the lines starting from the third line (actual data)
    for line in lines[2:]:  # Start after header and separator
        cells = line.split('|')
        # Remove leading and trailing whitespace from each cell and filter out empty cells
        cells = [cell.strip() for cell in cells if cell.strip()]

        if len(cells) < 4:  # Ensure the row has enough columns (4: Description, Latitude, Longitude, Duration)
            continue

        description = cells[0]  # Description is a string, so no conversion needed

        try:
            latitude = float(cells[1])  # Latitude should be a float
            longitude = float(cells[2])  # Longitude should be a float
        except ValueError:
            #st.warning(f"Skipping row due to ValueError: {cells}")  # Debugging: Show problematic rows
            continue

        duration = cells[3]  # Duration is a string (keep as is)

        table_data.append((description, latitude, longitude, duration))

    # Debugging output to check the parsed data
    #st.write("Parsed Table Data:", table_data)

    return table_data


# Function to display stops and the route with dotted line and arrows on a folium map
def plot_route_with_arrows(locations):
    # Create a base map centered around the first location
    map_center = [locations[0][1], locations[0][2]]  # Center the map on the first location
    folium_map = folium.Map(location=map_center, zoom_start=13)

    # List to store coordinates for the route line
    coordinates = []

    for i, (description, lat, lon, duration) in enumerate(locations):
        # Add markers for each stop

        folium.Marker(
            location=[lat, lon],
            popup=f"{description} ({duration} hour)",
            icon=folium.Icon(icon="info-sign"),
        ).add_to(folium_map)

        # Collect coordinates for the route
        coordinates.append((lat, lon))

    # Add a dotted polyline (route) between the points
    folium.PolyLine(
        locations=coordinates,
        color="blue",
        weight=2,
        dash_array="5, 5"  # Dotted line with dash pattern
    ).add_to(folium_map)

    # Add arrows to indicate direction
    folium.plugins.PolyLineTextPath(
        folium.PolyLine(locations=coordinates),  # Use the same coordinates as the PolyLine
        text='▶',  # The arrow symbol
        repeat=True,  # Repeat arrows along the path
        offset=6,  # Offset between arrows
        attributes={'fill': 'red', 'font-weight': 'bold', 'font-size': '24'}  # Arrow styling
    ).add_to(folium_map)

    # Fit the map to the bounds of all the coordinates
    folium_map.fit_bounds(coordinates)

    # Return the generated map
    return folium_map




# Streamlit App Layout
st.title("AI Location Explorer")
st.info("Get some inspiration for the exploration of a location along selected POIs ")

loc = get_geolocation()
if loc:
    #st.write(f"Your coordinates are {loc}")
    lat = loc['coords']['latitude']
    long = loc['coords']['longitude']

    actualLocation = (lat, long)
    # Initialize Nominatim API
    geolocator = Nominatim(user_agent="actualLocationAdressTest")

    # Get the location (address)
    ActuallocationAdress = geolocator.reverse(actualLocation, exactly_one=True)

    # Extract the address
    Actualaddress = ActuallocationAdress.address

with st.form("my_form"):
    # User input for location (either name or latitude and longitude)
    location_name = st.text_input("Enter a location name (or the actual location is used):", value=Actualaddress)
    #lat = st.text_input("Latitude", "")
    #long = st.text_input("Longitude", "")

    # Validate user inputs and use geopy if necessary
    if location_name:
        lat, long = get_lat_long(location_name)
        if lat and long:
            st.write("")
            #st.write(f"Latitude {lat}, Longitude {long}")

        else:
            st.write("Location not found, please check the name.")
    elif lat and long:
        try:
            lat, long = float(lat), float(long)
        except ValueError:
            st.error("Please enter valid numeric values for latitude and longitude.")

    # Duration slider (in hours)
    duration = st.slider("Select excursion duration (hours)", min_value=0.25, max_value=24.0, step=0.25)

    st.write("")

    transport = st.selectbox(
        "How would you like to get along?",
        ("walking", "cycling", "driving car"),
    )

    st.write("")


    with st.expander("Optional - Length of tour in km"):
        tourLength = st.slider(
            "Lenght ouf tour (km):", value=(0, 100)
        )

        tourLengthMin = str(tourLength[0]) + " kilometers"
        tourLengthMax = str(tourLength[1]) + " kilometers"

        # st.write("tourLengthMin:", tourLengthMin)

        # st.write("tourLengthMax:", tourLengthMax)

        if tourLength[0] == 0:
            tourLengthMinText = ""
        else:
            tourLengthMinText = "at least " + tourLengthMin + " "

        if tourLength[1] == 100:
            tourLengthMaxText = ""
        else:
            tourLengthMaxText = "maximum " + tourLengthMax

        # st.write("tourLengthMinText:", tourLengthMinText)

        # st.write("tourLengthMaxText:", tourLengthMaxText)

        # if tourLength[0] == 0 and tourLength[1] == 100:
        #    tourLengthText = ""
        if tourLength[0] != 0 and tourLength[1] != 100:
            tourLengthText = "The tour should be " + tourLengthMinText + "and " + tourLengthMaxText
            #st.write(tourLengthText)
        if tourLength[0] != 0 or tourLength[1] != 100:
            tourLengthText = "The tour should be " + tourLengthMinText + tourLengthMaxText
            #st.write(tourLengthText)

    st.write("")


    # Checkboxes for POIs
    poi_options = ["Shopping", "Museums", "Bars", "Cafes", "Restaurants", "Photospots", "Viewpoint", "Churches", "Touristic Sites", "Grocery Store", "Toilets", "Parking", "Chargingstation", "Tourist Information", "Hotel", "Interesting Architecture", "Beach"]
    selected_pois = st.multiselect("Select points of interest (POIs):", poi_options)

    EndpointIsStart = st.checkbox("Round-Trip")

    submitted = st.form_submit_button("Generate Route")
    if submitted:

        if lat and long and selected_pois:

            with st.spinner("Generating route"):

                #st.success("Start!")
                # Create prompt for ChatGPT
                prompt = generate_prompt(lat, long, duration, selected_pois)

                # Fetch the route from OpenAI's API
                route_description = get_route(prompt)

                # Display the route in a table
                if route_description:
                    st.subheader("Suggested Route")
                    st.write(route_description)  # Display the raw output for reference

                    # Parse the response table and extract data
                    #st.write("table_data: ")
                    table_data = parse_table_response(route_description)

                    #table_data_df = pd.DataFrame(table_data, columns=["Description", "Latitude", "Longitude", "Duration (hours)"])

                    #st.write(table_data_df)



                    # Show the route on a map using Folium


                    # Call the function to plot the route
                    folium_map = plot_route_with_arrows(table_data)

                    # Display the folium map in the Streamlit app
                    folium_static(folium_map, width=725)
