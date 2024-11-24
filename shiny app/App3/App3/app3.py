from shiny import App, render, ui, reactive
import pandas as pd
import matplotlib.pyplot as plt
import requests
import geopandas as gpd

# Define the UI
app_ui = ui.page_fluid(
    # Add the switch button
    ui.input_switch(
        id='switch_button',
        label="Toggle to switch to range of hours:",
        value=False  # Default state is "off" (single hour slider)
    ),

    # Dropdown to choose a combination of type and subtype
    ui.input_select(
        id='type_subtype',
        label='Select Alert Type and Subtype:',
        choices=[]  # Placeholder for dynamic dropdown values
    ),

    # Conditional display of hour inputs
    ui.output_ui("hour_selector"),  # Placeholder for dynamic hour selection UI

    # Output plot
    ui.output_plot('alert_plot')
)

# Define the server logic
def server(input, output, session):
    @reactive.calc
    def full_data():
        # Load the dataset (update the path as needed)
        df = pd.read_csv('/Users/samarnegahdar/Desktop/untitled folder/student30538/problem_sets/ps6/Waze_merged_data.csv')
        df['binned_lat_lon'] = df['binned_lat_lon'].apply(eval)  # Convert string tuples to actual tuples
        df['ts'] = pd.to_datetime(df['ts'], errors='coerce')  # Ensure 'ts' is in datetime format
        df['hour'] = df['ts'].dt.hour.astype(str).str.zfill(2) + ":00"  # Extract hour in the format 'HH:00'
        df['type_subtype'] = df['updated_type'] + ' - ' + df['updated_subsubtype']  # Create type_subtype column
        return df

    @reactive.effect
    def update_dropdown():
        # Populate the dropdown with unique type_subtype values
        type_subtype_list = full_data()['type_subtype'].unique().tolist()
        ui.update_select("type_subtype", choices=sorted(type_subtype_list))

    @reactive.calc
    def filtered_data():
        # Filter data based on the selected type_subtype
        df = full_data()
        return df[df['type_subtype'] == input.type_subtype()]

    # Dynamically render the appropriate hour slider
    @render.ui
    def hour_selector():
        if input.switch_button():
            # Display hour range slider if switch is on
            return ui.input_slider(
                id='hour_range',
                label='Select Hour Range:',
                min=0,
                max=23,
                step=1,
                value=[6, 9],  # Default range: 6AM to 9AM
                animate=True
            )
        else:
            # Display single hour slider if switch is off
            return ui.input_slider(
                id='hour_single',
                label='Select Hour:',
                min=0,
                max=23,
                step=1,
                value=12,  # Default hour: 12PM
                animate=True
            )

    @render.plot
    def alert_plot():
        # Filter data based on the selected type_subtype
        df = filtered_data()

        # Filter data based on selected hour(s)
        if input.switch_button():
            # Hour range filter
            hour_range = input.hour_range()
            df = df[df['hour'].isin([f"{str(hour).zfill(2)}:00" for hour in range(hour_range[0], hour_range[1] + 1)])]
        else:
            # Single hour filter
            single_hour = input.hour_single()
            df = df[df['hour'] == f"{str(single_hour).zfill(2)}:00"]

        # Count alerts for top locations
        df['alert_count'] = 1
        top_locations = (
            df.groupby(['binned_lat_lon'])['alert_count']
            .sum()
            .reset_index()
            .sort_values(by='alert_count', ascending=False)
            .head(10)
        )

        # Ensure valid lat/lon data
        top_locations[['latitude', 'longitude']] = pd.DataFrame(
            top_locations['binned_lat_lon'].tolist(),
            index=top_locations.index
        )

        # Load GeoJSON for the base map (Chicago neighborhoods)
        geojson_url = "https://data.cityofchicago.org/api/geospatial/bbvz-uum9?method=export&format=GeoJSON"
        response = requests.get(geojson_url)
        chicago_geojson = response.json()
        gdf = gpd.GeoDataFrame.from_features(chicago_geojson['features'])

        # Set plot size
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot the base map
        gdf.plot(ax=ax, color='lightgray', edgecolor='white')

        # Add scatter points for the top locations
        scatter = ax.scatter(
            top_locations['longitude'],
            top_locations['latitude'],
            s=top_locations['alert_count'] * 50,
            c=top_locations['alert_count'],
            cmap='viridis',
            alpha=0.8,
            edgecolors='black'
        )

        # Add a color bar
        cbar = plt.colorbar(scatter, ax=ax, fraction=0.03, pad=0.04)
        cbar.set_label('Alert Count', fontsize=12)

        # Set plot properties
        ax.set_title(f'Top 10 Locations for {input.type_subtype()} Alerts', fontsize=16)
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)

        # Set geographical bounds
        ax.set_xlim([-87.8, -87.4])
        ax.set_ylim([41.8, 42.0])

        ax.grid(True, linestyle='--', alpha=0.5)
        ax.tick_params(axis='both', labelsize=10)

        return fig

# Create the app
app = App(app_ui, server)