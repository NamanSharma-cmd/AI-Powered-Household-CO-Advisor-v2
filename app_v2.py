import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import time
import os
import joblib

# Import our refined predictor
from predictor_v2 import get_prediction_and_recommendation

# --- Constants ---
DB_FILE = "emission_history_v2.db"
LIVE_DATA_FILE = "live_data.csv"
COMMAND_FILE = "command.txt"

# Appliance Map
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

# --- Database Functions ---
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

def view_history():
    """Retrieves and sorts all historical data from the database."""
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()
        
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query("SELECT * FROM history", conn)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
    except Exception as e:
        st.error(f"Database Error: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

# Initialize DB on startup
init_db()

# --- Helper Functions ---
def create_custom_plotly_chart(df, title):
    """Creates a Plotly line chart with dotted lines across large gaps."""
    fig = go.Figure()
    if df.empty: return fig
    
    # Define gap threshold (e.g., 2 hours)
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
        # Solid line for continuous data
        fig.add_trace(go.Scatter(
            x=segment.index, 
            y=segment['predicted_co2'], 
            mode='lines+markers', 
            line=dict(color='#00CC96', width=2),
            marker=dict(size=4),
            name='Recorded Data', 
            showlegend=(i == 0)
        ))
        
        # Dotted line for gaps
        if i < len(segments) - 1:
            next_segment = segments[i+1]
            gap_start_x, gap_start_y = segment.index[-1], segment['predicted_co2'].iloc[-1]
            gap_end_x, gap_end_y = next_segment.index[0], next_segment['predicted_co2'].iloc[0]
            
            fig.add_trace(go.Scatter(
                x=[gap_start_x, gap_end_x], 
                y=[gap_start_y, gap_end_y], 
                mode='lines', 
                line=dict(color='#EF553B', width=2, dash='dot'), 
                name='Missing Data / Gap', 
                showlegend=(i == 0)
            ))
            
    fig.update_layout(
        title=dict(text=title, font=dict(size=20)),
        xaxis_title='Time', 
        yaxis_title='CO₂ Emissions (kg)',
        template='plotly_white',
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def display_simulation_results(co2, rec, runtime, live_data, weather_data):
    """Helper to display consistent results across simulation scenarios."""
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted CO₂", f"{co2:.4f} kg")
    c2.metric("Scrubber Runtime", f"{runtime} min")
    status = "High" if co2 > 0.05 else "Normal"
    c3.metric("Risk Level", status, delta="Alert" if status=="High" else "Safe", delta_color="inverse")
    
    # Recommendation
    if co2 > 0.05:
        st.error(f"**Recommendation:** {rec}")
    else:
        st.success(f"**Recommendation:** {rec}")
        
    # Charts Row
    ch1, ch2 = st.columns(2)
    
    with ch1:
        # Gauge
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = co2,
            title = {'text': "CO₂ Emission Level"},
            gauge = {
                'axis': {'range': [0, max(0.1, co2 * 1.5)]},
                'bar': {'color': "black"},
                'steps': [
                    {'range': [0, 0.05], 'color': "lightgreen"},
                    {'range': [0.05, 1.0], 'color': "salmon"}],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 0.05}
            }))
        fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
    with ch2:
        # Power Pie Chart
        active_appliances = {k: v for k, v in live_data.items() if v > 0}
        if active_appliances:
            df_apps = pd.DataFrame(list(active_appliances.items()), columns=['Appliance', 'Watts'])
            fig_pie = px.pie(df_apps, values='Watts', names='Appliance', hole=0.4)
            fig_pie.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No active appliances.")

    # Projected Reduction (if needed)
    if runtime > 0:
        st.markdown("### 📉 Projected Reduction")
        minutes = list(range(0, runtime + 10, 5))
        values = []
        for m in minutes:
            val = co2 - (co2 / runtime * m)
            values.append(max(0, val))
        
        df_proj = pd.DataFrame({'Time (min)': minutes, 'Remaining CO₂ (kg)': values})
        fig_proj = px.area(df_proj, x='Time (min)', y='Remaining CO₂ (kg)', markers=True)
        fig_proj.add_vline(x=runtime, line_dash="dash", line_color="green", annotation_text="Target Reached")
        st.plotly_chart(fig_proj, use_container_width=True)

# --- Page Config ---
st.set_page_config(
    page_title="CO₂ Scrubber Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Sidebar Navigation ---
st.sidebar.title("🌱 Eco-Scrubber AI")
page = st.sidebar.radio("Navigation", ["Overview", "AI Calculator", "History", "Comparison", "Live Monitor", "Simulation / Demo"])

st.sidebar.markdown("---")
st.sidebar.info("v2.1 - Enhanced Visualization")

# --- Main Content ---

# 1. OVERVIEW PAGE
if page == "Overview":
    st.title("📊 Dashboard Overview")
    
    # Fetch Data
    history_df = view_history()
    
    # --- Top Row: Gauge & Latest Insight ---
    col_gauge, col_insight = st.columns([1, 2])
    
    latest_val = 0
    if not history_df.empty:
        latest_val = history_df['predicted_co2'].iloc[-1]
    
    with col_gauge:
        # Gauge Chart for Latest Reading
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = latest_val,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Latest CO₂ Emission (kg)"},
            delta = {'reference': 0.05, 'increasing': {'color': "red"}, 'decreasing': {'color': "green"}},
            gauge = {
                'axis': {'range': [0, max(0.05, latest_val * 1.5)], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "darkblue"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 0.05], 'color': '#00CC96'},
                    {'range': [0.05, 0.1], 'color': '#FFA15A'},
                    {'range': [0.1, 1.0], 'color': '#EF553B'}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0.05}}))
        fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_insight:
        st.subheader("Latest AI Insight")
        if 'last_prediction' in st.session_state:
            pred = st.session_state.last_prediction
            st.info(f"**Time:** {pred['time'].strftime('%H:%M:%S')}\n\n**Recommendation:** {pred['rec']}")
            if pred.get('runtime', 0) > 0:
                st.warning(f"**Action Required:** Scrubber needs to run for **{pred['runtime']} minutes**.")
        elif not history_df.empty:
             st.info("Latest data loaded from history. Run a calculation to get fresh insights.")
        else:
             st.info("No data available. Go to 'AI Calculator' or 'Simulation' to generate data.")

    # --- KPI Cards ---
    if not history_df.empty:
        st.markdown("### 📈 Key Performance Indicators")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        today_df = history_df[history_df.index.date == today]
        yesterday_df = history_df[history_df.index.date == yesterday]
        
        today_total = today_df['predicted_co2'].sum()
        yesterday_total = yesterday_df['predicted_co2'].sum()
        delta = today_total - yesterday_total
        
        kpi1.metric("Today's Total Emissions", f"{today_total:.3f} kg", delta=f"{delta:.3f} kg")
        kpi2.metric("Yesterday's Total", f"{yesterday_total:.3f} kg")
        
        avg_emission = history_df['predicted_co2'].mean()
        kpi3.metric("Avg Emission / Event", f"{avg_emission:.4f} kg")
        
        count_events = len(today_df)
        kpi4.metric("Events Today", f"{count_events}")
        
        # --- Recent Trend Chart ---
        st.markdown("### 🕒 Recent Activity (24h)")
        recent_df = history_df[history_df.index > (datetime.now() - timedelta(hours=24))]
        if not recent_df.empty:
            fig_trend = px.area(recent_df, y='predicted_co2', title="24-Hour Emission Trend", 
                                labels={'predicted_co2': 'CO₂ (kg)', 'timestamp': 'Time'},
                                color_discrete_sequence=['#636EFA'])
            fig_trend.update_layout(xaxis_title=None)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.caption("No data recorded in the last 24 hours.")

# 2. AI CALCULATOR PAGE (New Dedicated Page)
elif page == "AI Calculator":
    st.title("🧮 AI Emission Calculator")
    st.markdown("Manually input appliance usage and weather conditions to predict CO₂ output.")
    
    col_input, col_result = st.columns([1, 2]) # Adjusted ratio for more dashboard space
    
    house_ids = sorted([i for i in range(1, 22) if i != 14])
    
    with col_input:
        with st.form(key='calculator_form'):
            st.subheader("1. Configuration")
            sim_house_id = st.selectbox('Select House Profile', options=house_ids)
            
            st.subheader("2. Weather Conditions")
            temp_c = st.slider('Temperature (°C)', -10, 40, 15)
            humidity_p = st.slider('Humidity (%)', 0, 100, 60)
            rain_mm = st.slider('Rainfall (mm)', 0, 10, 0)
            
            st.subheader("3. Appliance Usage (Watts)")
            st.caption("Adjust power consumption.")
            
            live_data = {}
            house_appliances = APPLIANCE_MAP.get(sim_house_id, {})
            
            if house_appliances:
                for appliance_name in sorted(house_appliances.values()):
                    power_w = st.slider(f"{appliance_name.replace('_', ' ')}", 0, 3000, 0, key=f"calc_{appliance_name}")
                    live_data[appliance_name] = power_w
            else:
                st.warning("No appliances found for this house.")
                
            calc_submitted = st.form_submit_button('Calculate Emissions', type="primary")

    with col_result:
        st.subheader("4. Prediction Dashboard")
        
        if calc_submitted:
            weather_data = {'max_temp_°c': temp_c, 'humidity_%': humidity_p, 'rain_mm': rain_mm}
            co2, rec, runtime = get_prediction_and_recommendation(live_data, weather_data, sim_house_id)
            
            # Save to history
            add_to_history(co2, sim_house_id)
            st.session_state.last_prediction = {'co2': co2, 'rec': rec, 'runtime': runtime, 'time': datetime.now()}
            
            # --- ROW 1: Key Metrics & Gauge ---
            r1c1, r1c2, r1c3 = st.columns([1.5, 1, 1])
            
            with r1c1:
                # Gauge
                fig_res_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = co2,
                    title = {'text': "Predicted CO₂ (kg)"},
                    gauge = {
                        'axis': {'range': [0, max(0.05, co2 * 1.5)]},
                        'bar': {'color': "black"},
                        'steps': [
                            {'range': [0, 0.05], 'color': "lightgreen"},
                            {'range': [0.05, 1.0], 'color': "salmon"}],
                    }))
                fig_res_gauge.update_layout(height=220, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_res_gauge, use_container_width=True)
            
            with r1c2:
                # Runtime Metric
                st.metric("Scrubber Runtime", f"{runtime} min", help="Required operation time")
                st.progress(min(runtime / 60, 1.0)) # Simple visual progress bar (max 60 min scale)
                
            with r1c3:
                # Status Metric
                status = "High" if co2 > 0.05 else "Normal"
                st.metric("Risk Level", status, delta="Alert" if status=="High" else "Safe", delta_color="inverse")

            st.markdown("---")

            # --- ROW 2: Detailed Charts ---
            r2c1, r2c2 = st.columns(2)
            
            with r2c1:
                st.markdown("#### ⚡ Power Breakdown")
                active_appliances = {k: v for k, v in live_data.items() if v > 0}
                if active_appliances:
                    df_apps = pd.DataFrame(list(active_appliances.items()), columns=['Appliance', 'Watts'])
                    fig_pie = px.pie(df_apps, values='Watts', names='Appliance', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No active appliances.")

            with r2c2:
                st.markdown("#### 📊 vs. Historical Average")
                # Calculate Average
                hist_df = view_history()
                avg_co2 = 0.0
                if not hist_df.empty:
                    house_hist = hist_df[hist_df['house_id'] == sim_house_id]
                    if not house_hist.empty:
                        avg_co2 = house_hist['predicted_co2'].mean()
                
                comp_df = pd.DataFrame({
                    'Metric': ['Current Prediction', 'House Average'],
                    'CO₂ (kg)': [co2, avg_co2]
                })
                fig_bar = px.bar(comp_df, x='Metric', y='CO₂ (kg)', color='Metric', 
                                 color_discrete_map={'Current Prediction': '#EF553B', 'House Average': '#636EFA'})
                fig_bar.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

            # --- ROW 3: Weather Context & Recommendation ---
            r3c1, r3c2 = st.columns([1, 2])
            
            with r3c1:
                st.markdown("#### 🌦️ Weather Context")
                # Radar Chart for Weather
                # Normalize: Temp (0-40), Humidity (0-100), Rain (0-10)
                # Invert Temp because Low Temp = High Heating = High CO2 risk usually
                w_categories = ['Cold Stress', 'Humidity', 'Rainfall']
                w_values = [
                    max(0, (20 - temp_c)/30) if temp_c < 20 else 0, # Rough "Cold Stress" metric
                    humidity_p / 100,
                    min(rain_mm / 10, 1.0)
                ]
                
                fig_radar = go.Figure(data=go.Scatterpolar(
                    r=w_values,
                    theta=w_categories,
                    fill='toself',
                    name='Weather Severity'
                ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                    showlegend=False,
                    height=250,
                    margin=dict(l=30, r=30, t=20, b=20)
                )
                st.plotly_chart(fig_radar, use_container_width=True)

            with r3c2:
                st.markdown("#### 🤖 AI Recommendation")
                if co2 > 0.05:
                    st.error(f"{rec}")
                else:
                    st.success(f"{rec}")
                
                with st.expander("View Input Summary"):
                    st.json({
                        "House ID": sim_house_id,
                        "Weather": weather_data,
                        "Active Appliances": active_appliances
                    })

        else:
            st.info("👈 Configure settings and click 'Calculate Emissions' to generate the dashboard.")

# 3. HISTORY PAGE
elif page == "History":
    st.title("📜 Historical Analysis")
    history_df = view_history()
    
    if not history_df.empty:
        col_filter, col_down = st.columns([3, 1])
        house_ids = sorted([i for i in range(1, 22) if i != 14])
        
        with col_filter:
            house_filter = st.selectbox("Filter by House", ["All"] + house_ids)
        
        if house_filter != "All":
            filtered_df = history_df[history_df['house_id'] == house_filter]
            title = f"Emissions History - House {house_filter}"
        else:
            filtered_df = history_df
            title = "Emissions History - All Houses"
            
        # 1. Custom Plotly Chart with Gaps
        fig_history = create_custom_plotly_chart(filtered_df, title)
        st.plotly_chart(fig_history, use_container_width=True)
        
        # 2. Heatmap Analysis
        st.markdown("### 🔥 Emission Intensity Heatmap")
        st.caption("Average CO₂ emissions by Day of Week and Hour of Day.")
        
        if not filtered_df.empty:
            # Prepare data for heatmap
            heatmap_df = filtered_df.copy()
            heatmap_df['hour'] = heatmap_df.index.hour
            heatmap_df['day_of_week'] = heatmap_df.index.day_name()
            
            # Pivot
            heatmap_data = heatmap_df.pivot_table(index='day_of_week', columns='hour', values='predicted_co2', aggfunc='mean')
            
            # Sort days
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heatmap_data = heatmap_data.reindex(days_order)
            
            fig_heat = px.imshow(heatmap_data, 
                                 labels=dict(x="Hour of Day", y="Day of Week", color="Avg CO₂"),
                                 x=heatmap_data.columns,
                                 y=heatmap_data.index,
                                 color_continuous_scale='RdBu_r',
                                 aspect="auto")
            fig_heat.update_layout(height=400)
            st.plotly_chart(fig_heat, use_container_width=True)
        
        with col_down:
            st.markdown("<br>", unsafe_allow_html=True) # Spacer
            csv = filtered_df.to_csv().encode('utf-8')
            st.download_button("Download CSV", csv, "emissions_history.csv", "text/csv", use_container_width=True)
            
        st.dataframe(filtered_df.sort_index(ascending=False), use_container_width=True)
    else:
        st.warning("No history found.")

# 4. COMPARISON PAGE
elif page == "Comparison":
    st.title("🏘️ Neighbourhood Comparison")
    history_df = view_history()
    
    if not history_df.empty:
        # 1. Total Emissions Bar Chart
        total_by_house = history_df.groupby('house_id')['predicted_co2'].sum().reset_index()
        fig_bar = px.bar(total_by_house, x='house_id', y='predicted_co2', 
                     title="Total Emissions by House", color='predicted_co2',
                     labels={'predicted_co2': 'Total CO₂ (kg)', 'house_id': 'House ID'},
                     color_continuous_scale='Viridis')
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # 2. Box Plot for Distribution
        st.markdown("### Emission Distribution per House")
        fig_box = px.box(history_df, x='house_id', y='predicted_co2', 
                         title="Emission Variability by House",
                         labels={'predicted_co2': 'CO₂ (kg)', 'house_id': 'House ID'})
        st.plotly_chart(fig_box, use_container_width=True)
    else:
        st.warning("Not enough data for comparison.")

# 5. LIVE MONITOR PAGE
elif page == "Live Monitor":
    st.title("🔌 Hardware Control Center")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Manual Override")
        st.caption("Directly control the ESP32 relays.")
        
        if st.button("🟢 START SCRUBBER", use_container_width=True):
            try:
                with open(COMMAND_FILE, "w") as f:
                    f.write("1")
                st.success("Command Sent: ON")
            except Exception as e:
                st.error(f"Failed to send command: {e}")
        
        if st.button("🔴 STOP SCRUBBER", use_container_width=True):
            try:
                with open(COMMAND_FILE, "w") as f:
                    f.write("0")
                st.warning("Command Sent: OFF")
            except Exception as e:
                st.error(f"Failed to send command: {e}")
                
        st.markdown("---")
        st.info("Ensure `bridge.py` is running to communicate with the ESP32.")

    with col2:
        st.subheader("Live Sensor Data")
        
        # Auto-refresh mechanism
        if st.checkbox("Enable Auto-Refresh", value=True):
            if os.path.exists(LIVE_DATA_FILE):
                try:
                    # Read last 50 lines efficiently
                    df = pd.read_csv(LIVE_DATA_FILE)
                    if not df.empty:
                        last_50 = df.tail(50)
                        latest = df.iloc[-1]
                        
                        # Metrics
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Air Quality (Raw)", int(latest['sensor_value']))
                        m2.metric("Voltage", f"{float(latest['voltage']):.2f} V")
                        
                        status = "NORMAL"
                        if int(latest['sensor_value']) > 1000:
                            status = "HIGH"
                            m3.error(f"Status: {status}")
                        else:
                            m3.success(f"Status: {status}")
                        
                        # Chart
                        fig = px.line(last_50, x='timestamp', y='sensor_value', title="Real-Time Sensor Readings")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Data file is empty.")
                except Exception as e:
                    st.error(f"Error reading live data: {e}")
            else:
                st.warning("Waiting for data... (File not found)")
            
# 6. SIMULATION / DEMO PAGE
elif page == "Simulation / Demo":
    st.title("🧪 System Simulation & Demonstration")
    st.markdown("Use these preset test cases to demonstrate the system's response to different conditions.")
    
    # Tabs for different scenarios
    tab1, tab2, tab3 = st.tabs(["✅ Normal Scenario", "⚠️ Abnormal Scenario", "🛠️ Custom Test Case"])
    
    # --- Normal Test Case ---
    with tab1:
        st.subheader("Scenario: Mild Weather, Low Usage")
        st.info("Simulates a typical day with low appliance usage and mild weather.")
        
        # Define Params
        normal_weather = {'max_temp_°c': 20, 'humidity_%': 50, 'rain_mm': 0}
        normal_appliances = {'Fridge': 100, 'Router': 10, 'Television': 80}
        
        # Display Params
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Weather Parameters:**")
            st.json(normal_weather)
        with c2:
            st.markdown("**Appliance Usage (Watts):**")
            st.json(normal_appliances)
            
        if st.button("Run Normal Test", use_container_width=True):
            co2, rec, runtime = get_prediction_and_recommendation(normal_appliances, normal_weather, 1)
            
            st.markdown("---")
            st.subheader("Test Results")
            display_simulation_results(co2, rec, runtime, normal_appliances, normal_weather)
            
            # Ensure scrubber is OFF
            with open(COMMAND_FILE, "w") as f:
                f.write("0")
            st.toast("System Status: IDLE")

    # --- Abnormal Test Case ---
    with tab2:
        st.subheader("Scenario: Cold Weather, High Load")
        st.error("Simulates high load (heating + heavy appliances) in cold weather.")
        
        # Define Params
        abnormal_weather = {'max_temp_°c': -2, 'humidity_%': 85, 'rain_mm': 5}
        abnormal_appliances = {
            'Electric_Heater': 2500, 
            'Tumble_Dryer': 2000, 
            'Washing_Machine': 1500,
            'Fridge': 150
        }
        
        # Display Params
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Weather Parameters:**")
            st.json(abnormal_weather)
        with c2:
            st.markdown("**Appliance Usage (Watts):**")
            st.json(abnormal_appliances)
            
        if st.button("Run Abnormal Test", type="primary", use_container_width=True):
            co2, rec, runtime = get_prediction_and_recommendation(abnormal_appliances, abnormal_weather, 1)
            
            st.markdown("---")
            st.subheader("Test Results")
            display_simulation_results(co2, rec, runtime, abnormal_appliances, abnormal_weather)
            
            # Trigger Scrubber
            with open(COMMAND_FILE, "w") as f:
                f.write("1")
            st.toast("🚨 SCRUBBER ACTIVATED!", icon="⚠️")

    # --- Custom Test Case ---
    with tab3:
        st.subheader("Scenario: Custom User Input")
        st.markdown("Define your own parameters to test the system.")
        
        c_input, c_weather = st.columns(2)
        
        with c_weather:
            st.markdown("#### Weather")
            cust_temp = st.slider("Temperature (°C)", -10, 40, 10, key="cust_temp")
            cust_hum = st.slider("Humidity (%)", 0, 100, 50, key="cust_hum")
            cust_rain = st.slider("Rainfall (mm)", 0, 10, 0, key="cust_rain")
            
        with c_input:
            st.markdown("#### Appliances")
            # Simplified list for custom test
            cust_heater = st.slider("Electric Heater (W)", 0, 3000, 0, key="cust_heater")
            cust_washer = st.slider("Washing Machine (W)", 0, 3000, 0, key="cust_washer")
            cust_dryer = st.slider("Tumble Dryer (W)", 0, 3000, 0, key="cust_dryer")
            cust_fridge = st.slider("Fridge (W)", 0, 500, 100, key="cust_fridge")
            
        if st.button("Run Custom Test", use_container_width=True):
            cust_weather = {'max_temp_°c': cust_temp, 'humidity_%': cust_hum, 'rain_mm': cust_rain}
            cust_appliances = {
                'Electric_Heater': cust_heater,
                'Washing_Machine': cust_washer,
                'Tumble_Dryer': cust_dryer,
                'Fridge': cust_fridge
            }
            
            co2, rec, runtime = get_prediction_and_recommendation(cust_appliances, cust_weather, 1)
            
            st.markdown("---")
            st.subheader("Test Results")
            display_simulation_results(co2, rec, runtime, cust_appliances, cust_weather)
