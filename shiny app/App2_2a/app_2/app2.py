from shiny import App, render, ui, reactive
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd

# Define the UI
app_ui = ui.page_fluid(
    ui.input_select(
        id='type_subtype',
        label='Select Alert Type and Subtype:',
        choices=[]  # Placeholder for dynamic dropdown values
    ),
    ui.input_slider(
        id='hour_slider',
        label='Select Hour:',
        min=0,
        max=23,
        step=1,
        value=12,  # Default to 12:00
        animate=True
    ),
    ui.output_plot('alert_plot')  # Output for the plot
)

# Define the server
def server(input, output, session):
    @reactive.calc
    def full_data():
        # Load the dataset (update the path as needed)
        df = pd.read_csv('/Users/samarnegahdar/Desktop/untitled folder/pset-VI/Waze_merged_data.csv')
        
        # Ensure the 'ts' column is in datetime format
        df['ts'] = pd.to_datetime(df['ts'], errors='coerce')

        # Create a new 'hour' column by extracting the hour from the 'ts' column
        df['hour'] = df['ts'].dt.hour.astype(str).str.zfill(2) + ":00"
        
        # If 'type_subtype' does not exist, create it by combining 'updated_type' and 'updated_subsubtype'
        if 'type_subtype' not in df.columns:
            df['type_subtype'] = df['updated_type'] + ' - ' + df['updated_subsubtype']  # Assuming 'updated_type' and 'updated_subsubtype' exist

        df['binned_lat_lon'] = df['binned_lat_lon'].apply(eval)  # Convert string tuples to actual tuples
        return df

    @reactive.effect
    def update_dropdown():
        # Populate the dropdown with unique type_subtype values
        type_subtype_list = full_data()['type_subtype'].unique().tolist()
        ui.update_select("type_subtype", choices=sorted(type_subtype_list))

    @reactive.calc
    def filtered_data():
        # Filter data based on the selected type_subtype and hour
        df = full_data()
        return df[(df['type_subtype'] == input.type_subtype()) & (df['hour'] == f"{input.hour_slider():02}:00")]

    @reactive.calc
    def load_base_map():
        # Load GeoJSON for the base map
        geojson_file = '/Users/samarnegahdar/Desktop/untitled folder/pset-VI/chicago_neighborhoods.geojson'
        gdf = gpd.read_file(geojson_file)
        return gdf

    @render.plot
    def alert_plot():
        # Prepare the top 10 locations for the selected type_subtype and hour
        df = filtered_data()
        top_locations = (
            df.groupby('binned_lat_lon')
            .size()
            .reset_index(name='alert_count')
            .sort_values(by='alert_count', ascending=False)
            .head(10)
        )

        # Ensure 'binned_lat_lon' has valid data
        top_locations = top_locations[top_locations['binned_lat_lon'].apply(lambda x: isinstance(x, tuple) and len(x) == 2)]

        # Split 'binned_lat_lon' into 'latitude' and 'longitude' only if it exists
        if not top_locations.empty and 'binned_lat_lon' in top_locations.columns:
            try:
                top_locations[['latitude', 'longitude']] = pd.DataFrame(
                    top_locations['binned_lat_lon'].tolist(),
                    index=top_locations.index
                )
            except Exception as e:
                print(f"Error while splitting binned_lat_lon into latitude and longitude: {e}")
        else:
            print("Warning: No valid locations found for the selected type_subtype.")

        # Check if the 'latitude' and 'longitude' columns exist before proceeding
        if 'latitude' not in top_locations.columns or 'longitude' not in top_locations.columns:
            print("Error: Latitude and Longitude data not available for the selected locations.")
            return None

        # Load base map
        gdf = load_base_map()

        # Create the Matplotlib plot
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot the base map
        gdf.plot(ax=ax, color='lightgray', edgecolor='white')

        # Add scatter points for the top locations
        scatter = ax.scatter(
            top_locations['longitude'],
            top_locations['latitude'],
            s=top_locations['alert_count'],
            c=top_locations['alert_count'],
            cmap='viridis',
            alpha=0.8,
            edgecolors='black'
        )

        # Add a color bar
        cbar = plt.colorbar(scatter, ax=ax, label='Alert Count')
        cbar.ax.tick_params(labelsize=10)

        # Set plot properties
        ax.set_title(f'Top 10 Locations for {input.type_subtype()} Alerts at {input.hour_slider()}:00', fontsize=16)
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.set_xlim([-87.8, -87.4])  # Set longitude range
        ax.set_ylim([41.8, 42.0])  # Set latitude range

        # Grid and labels
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.tick_params(axis='both', labelsize=10)

        return fig

# Create the app
app = App(app_ui, server)