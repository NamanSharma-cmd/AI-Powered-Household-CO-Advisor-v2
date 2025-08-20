import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.graph_objects as go
from predictor_v2 import get_prediction_and_recommendation

APPLIANCE_MAP = {
    1: {1: 'Fridge', 2: 'Freezer_1', 3: 'Freezer_2', 4: 'Washer_Dryer', 5: 'Washing_Machine', 6: 'Dishwasher', 7: 'Computer', 8: 'Television_Site', 9: 'Electric_Heater'},
    2: {1: 'Fridge-Freezer', 2: 'Washing_Machine', 3: 'Dishwasher', 4: 'Television_Site', 5: 'Microwave', 6: 'Toaster', 7: 'Hi-Fi', 8: 'Kettle', 9: 'Overhead_Fan'},
    3: {1: 'Toaster', 2: 'Fridge-Freezer', 3: 'Freezer', 4: 'Tumble_Dryer', 5: 'Dishwasher', 6: 'Washing_Machine', 7: 'Television_Site', 8: 'Microwave', 9: 'Kettle'},
    4: {1: 'Fridge', 2: 'Freezer', 3: 'Fridge-Freezer', 4: 'Washing_Machine_1', 5: 'Washing_Machine_2', 6: 'Desktop_Computer', 7: 'Television_Site', 8: 'Microwave', 9: 'Kettle'},
    5: {1: 'Fridge-Freezer', 2: 'Tumble_Dryer', 3: 'Washing_Machine', 4: 'Dishwasher', 5: 'Desktop_Computer', 6: 'Television_Site', 7: 'Microwave', 8: 'Kettle', 9: 'Toaster'},
    6: {1: 'Freezer', 2: 'Washing_Machine', 3: 'Dishwasher', 4: 'MJY_Computer', 5: 'TV_Satellite', 6: 'Microwave', 7: 'Kettle', 8: 'Toaster', 9: 'PGM_Computer'},
    7: {1: 'Fridge', 2: 'Freezer_1', 3: 'Freezer_2', 4: 'Tumble_Dryer', 5: 'Washing_Machine', 6: 'Dishwasher', 7: 'Television_Site', 8: 'Toaster', 9: 'Kettle'},
    8: {1: 'Fridge', 2: 'Freezer', 3: 'Washer_Dryer', 4: 'Washing_Machine', 5: 'Toaster', 6: 'Computer', 7: 'Television_Site', 8: 'Microwave', 9: 'Kettle'},
    9: {1: 'Fridge-Freezer', 2: 'Washer_Dryer', 3: 'Washing_Machine', 4: 'Dishwasher', 5: 'Television_Site', 6: 'Microwave', 7: 'Kettle', 8: 'Hi-Fi', 9: 'Electric_Heater'},
    10: {1: 'Blender', 2: 'Toaster', 3: 'Chest_Freezer', 4: 'Fridge-Freezer', 5: 'Washing_Machine', 6: 'Dishwasher', 7: 'Television_Site', 8: 'Microwave', 9: 'K_Mix'},
    11: {1: 'Fridge', 2: 'Fridge-Freezer', 3: 'Washing_Machine', 4: 'Dishwasher', 5: 'Computer_Site', 6: 'Microwave', 7: 'Kettle', 8: 'Router', 9: 'Hi-Fi'},
    12: {1: 'Fridge-Freezer', 4: 'Computer_Site', 5: 'Microwave', 6: 'Kettle', 7: 'Toaster', 8: 'Television'},
    13: {1: 'Television_Site', 2: 'Freezer', 3: 'Washing_Machine', 4: 'Dishwasher', 6: 'Network_Site', 7: 'Microwave', 8: 'Microwave_2', 9: 'Kettle'},
    15: {1: 'Fridge-Freezer', 2: 'Tumble_Dryer', 3: 'Washing_Machine', 4: 'Dishwasher', 5: 'Computer_Site', 6: 'Television_Site', 7: 'Microwave', 8: 'Hi-Fi', 9: 'Toaster'},
    16: {1: 'Fridge-Freezer_1', 2: 'Fridge-Freezer_2', 3: 'Electric_Heater_1', 4: 'Electric_Heater_2', 5: 'Washing_Machine', 6: 'Dishwasher', 7: 'Computer_Site', 8: 'Television_Site', 9: 'Dehumidifier'},
    17: {1: 'Freezer', 2: 'Fridge-Freezer', 3: 'Tumble_Dryer', 4: 'Washing_Machine', 5: 'Computer_Site', 6: 'Television_Site', 7: 'Microwave', 8: 'Kettle', 9: 'TV_Site_Bedroom'},
    18: {1: 'Fridge_Garage', 2: 'Freezer_Garage', 3: 'Fridge-Freezer', 4: 'Washer_Dryer_Garage', 5: 'Washing_Machine', 6: 'Dishwasher', 7: 'Desktop_Computer', 8: 'Television_Site', 9: 'Microwave'},
    19: {1: 'Fridge_Freezer', 2: 'Washing_Machine', 3: 'Television_Site', 4: 'Microwave', 5: 'Kettle', 6: 'Toaster', 7: 'Bread-maker', 8: 'Games_Console', 9: 'Hi-Fi'},
    20: {1: 'Fridge', 2: 'Freezer', 3: 'Tumble_Dryer', 4: 'Washing_Machine', 5: 'Dishwasher', 6: 'Computer_Site', 7: 'Television_Site', 8: 'Microwave', 9: 'Kettle'},
    21: {1: 'Fridge-Freezer', 2: 'Tumble_Dryer', 3: 'Washing_Machine', 4: 'Dishwasher', 5: 'Food_Mixer', 6: 'Television', 7: 'Kettle', 8: 'Vivarium', 9: 'Pond_Pump'}
}

# --- Database Functions (with Caching) ---
DB_FILE = "emission_history_v2.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS history (timestamp TEXT, house_id INTEGER, predicted_co2 REAL)')
    conn.commit()
    conn.close()

def add_to_history(co2, house_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO history VALUES (?,?,?)", (timestamp, house_id, co2))
    conn.commit()
    conn.close()

@st.cache_data
def view_history():
    """Retrieves and sorts all historical data from the database."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM history", conn)
    conn.close()
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
    return df

init_db()

def set_page_to_home():
    st.session_state.page_selection = 'Home / Overview'
# --- Plotting Functions ---
def create_custom_plotly_chart(df, title):
    """Creates a Plotly line chart with dotted lines across large gaps."""
    fig = go.Figure()
    if df.empty: return fig
    gap_threshold = timedelta(hours=2)
    time_diffs = df.index.to_series().diff()
    segments = []
    current_segment_start_idx = 0
    for i in range(1, len(df)):
        if time_diffs.iloc[i] > gap_threshold:
            segments.append(df.iloc[current_segment_start_idx:i])
            current_segment_start_idx = i
    segments.append(df.iloc[current_segment_start_idx:])
    for i, segment in enumerate(segments):
        fig.add_trace(go.Scatter(x=segment.index, y=segment.iloc[:, 0], mode='lines', line=dict(color='#1f77b4', width=2), name='Recorded Data', showlegend=(i == 0)))
        if i < len(segments) - 1:
            next_segment = segments[i+1]
            gap_start_x, gap_start_y = segment.index[-1], segment.iloc[-1, 0]
            gap_end_x, gap_end_y = next_segment.index[0], next_segment.iloc[0, 0]
            fig.add_trace(go.Scatter(x=[gap_start_x, gap_end_x], y=[gap_start_y, gap_end_y], mode='lines', line=dict(color='#ff7f0e', width=2, dash='dot'), name='Unrecorded Gap', showlegend=(i == 0)))
    fig.update_layout(title=dict(text=title, font=dict(size=24)), xaxis_title='Date and Time', yaxis_title='Predicted CO₂ Emissions (kg)', template='plotly_white', legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    return fig

@st.cache_data
def generate_comparison_chart(df):
    """Groups data by day and house, then plots the comparison chart."""
    st.write("First-time calculation for comparison chart...") # This will only appear once per session
    
    # FIX: Group by house_id and day first, then calculate the mean. This is the correct method.
    daily_avg_per_house = df.groupby(['house_id', pd.Grouper(freq='D')])['predicted_co2'].mean()
    
    # Unstack the results to get a pivot-table-like format with houses as columns
    comparison_df = daily_avg_per_house.unstack(level='house_id')
    
    # Create the Plotly figure
    fig = go.Figure()
    for house in comparison_df.columns:
        fig.add_trace(go.Scatter(
            x=comparison_df.index,
            y=comparison_df[house],
            mode='lines',
            name=f'House {int(house)}'
        ))
    
    fig.update_layout(
        title=dict(text="Comparison of Daily Average Emissions", font=dict(size=24)),
        xaxis_title='Date',
        yaxis_title='Average Daily CO₂ Emissions (kg)',
        template='plotly_white',
        legend_title_text='House ID'
    )
    return fig


# --- STREAMLIT DASHBOARD LAYOUT ---
st.set_page_config(layout="wide")
st.title('💡 Household CO₂ Emissions Dashboard')
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to", 
    ("Home / Overview", "Historical Deep Dive", "Neighbourhood Comparison"), 
    key='page_selection'
)
# --- Sidebar Controls ---
st.sidebar.title("Controls")
house_ids = sorted([i for i in range(1, 22) if i != 14])
options_list = ['All Houses'] + house_ids

st.sidebar.header('Real-Time Simulation')

# FIX: This dropdown is now OUTSIDE the form.
# This allows the app to rerun and update the appliance list when you change the house.
simulation_house_id = st.sidebar.selectbox('Simulate for House', options=house_ids)

# The form now only contains the widgets that should be submitted together.
with st.sidebar.form(key='simulation_form'):
    st.subheader('Current Weather')
    temp_c = st.slider('Temperature (°C)', -10, 40, 15)
    humidity_p = st.slider('Humidity (%)', 0, 100, 60)
    rain_mm = st.slider('Rainfall (mm)', 0, 10, 0)
    
    st.subheader('Live Appliance Data (Watts)')
    live_data = {}
    
    # This list of appliances is now correctly updated based on the selection above
    house_appliances = APPLIANCE_MAP.get(simulation_house_id, {})

    if not house_appliances:
        st.write("No specific appliances listed for this house.")
    else:
        for appliance_name in sorted(house_appliances.values()):
            max_w = 3000
            power_w = st.slider(f"{appliance_name.replace('_', ' ')}", 0, max_w, 0)
            live_data[appliance_name] = power_w
            
    submitted = st.form_submit_button('Calculate & Save Emissions', on_click=set_page_to_home)

if submitted:
    weather_data = {'max_temp °c': temp_c, 'humidity %': humidity_p, 'rain mm': rain_mm}
    co2, rec = get_prediction_and_recommendation(live_data, weather_data, simulation_house_id)
    add_to_history(co2, simulation_house_id)
    st.session_state.recommendation = rec   
    st.rerun()


# --- Main Page ---
# --- Main Page ---
history_df = view_history()

# --- Page 1: Home / Overview ---
if page == "Home / Overview":
    st.header("Dashboard at a Glance")
    
    # --- KPI Cards ---
    if not history_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        today_df = history_df[history_df.index.date == today]
        yesterday_df = history_df[history_df.index.date == yesterday]
        
        # Calculate sums safely, defaulting to 0 if no data
        today_co2 = today_df['predicted_co2'].sum() if not today_df.empty else 0
        yesterday_co2 = yesterday_df['predicted_co2'].sum() if not yesterday_df.empty else 0
        
        # Calculate weekly average safely
        weekly_df = history_df[history_df.index.date > (today - timedelta(days=7))]
        weekly_avg = weekly_df.resample('D')['predicted_co2'].sum().mean() if not weekly_df.empty else 0
        
        col1.metric("Today's Total Emissions", f"{today_co2:.2f} kg CO₂")
        col2.metric("Yesterday's Total Emissions", f"{yesterday_co2:.2f} kg CO₂")
        col3.metric("7-Day Daily Average", f"{weekly_avg:.2f} kg CO₂")
        col4.metric("Latest Recorded Emission", f"{history_df['predicted_co2'].iloc[-1]:.4f} kg CO₂")
    
    st.markdown("---")
    
    # --- Live Recommendation ---
    if 'recommendation' in st.session_state:
        st.info(f"**Latest AI Recommendation:** {st.session_state.recommendation}")
        
    # --- 24-Hour Trend Chart ---
    st.subheader("Recent 24-Hour Emissions Trend (Sum of All Houses)")
    if not history_df.empty:
        recent_df = history_df[history_df.index > (datetime.now() - timedelta(hours=24))]
        if not recent_df.empty:
            hourly_recent_sum = recent_df.resample('H')['predicted_co2'].sum()
            st.line_chart(hourly_recent_sum)
        else:
            st.write("No data recorded in the last 24 hours.")

# --- Page 2: Historical Deep Dive ---
elif page == "Historical Deep Dive":
    st.header("Historical Deep Dive")
    
    # Move the house selector here
    options_list = ['All Houses'] + house_ids
    selected_house_view = st.selectbox('Select a House to View', options=options_list, index=1)
    
    if selected_house_view == 'All Houses':
        df_to_plot = history_df.groupby(history_df.index)['predicted_co2'].sum().to_frame(name='predicted_co2')
        title = "Total Neighbourhood Emissions"
    else:
        df_to_plot = history_df[history_df['house_id'] == selected_house_view][['predicted_co2']]
        title = f"Emissions for House {selected_house_view}"
        
    if not df_to_plot.empty:
        fig = create_custom_plotly_chart(df_to_plot, title)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Solid lines represent continuous data, while dotted lines indicate a gap in the record.")
    else:
        st.warning("No historical data available for this selection.")
        
# --- Page 3: Neighbourhood Comparison ---
elif page == "Neighbourhood Comparison":
    st.header("Neighbourhood Comparison")
    
    if not history_df.empty:
        fig = generate_comparison_chart(history_df)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("This chart shows the daily average CO₂ emissions for each house, allowing you to compare their patterns over time.")
    else:
        st.warning("No historical data yet.")