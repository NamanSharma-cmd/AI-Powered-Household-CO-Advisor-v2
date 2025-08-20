import joblib
import pandas as pd
from datetime import datetime

# Load the new v2 model with the correct filename
model = joblib.load('co_model_v2.joblib')

# --- CRITICAL ---
# This list must be the one you copied from your training notebook
FEATURE_ORDER = ['House_ID', 'Occupancy', 'Blender', 'Bread-maker', 'Chest_Freezer', 'Computer', 'Computer_Site', 'Dehumidifier', 'Desktop_Computer', 'Dishwasher', 'Electric_Heater', 'Electric_Heater_1', 'Electric_Heater_2', 'Food_Mixer', 'Freezer', 'Freezer_1', 'Freezer_2', 'Freezer_Garage', 'Fridge', 'Fridge-Freezer', 'Fridge-Freezer_1', 'Fridge-Freezer_2', 'Fridge_Freezer', 'Fridge_Garage', 'Games_Console', 'Hi-Fi', 'K_Mix', 'Kettle', 'MJY_Computer', 'Microwave', 'Microwave_2', 'Network_Site', 'Overhead_Fan', 'PGM_Computer', 'Pond_Pump', 'Router', 'TV_Satellite', 'TV_Site_Bedroom', 'Television', 'Television_Site', 'Toaster', 'Tumble_Dryer', 'Vivarium', 'Washer_Dryer', 'Washer_Dryer_Garage', 'Washing_Machine', 'Washing_Machine_1', 'Washing_Machine_2', 'max_temp_°c', 'humidity_%', 'rain_mm', 'Hour_of_Day', 'Day_of_Week', 'Is_Weekend', 'Type_Detached', 'Type_Mid-terrace', 'Type_Semi-detached', 'Type_nan', 'Size_2_bed', 'Size_3_bed', 'Size_4_bed', 'Size_5_bed', 'Size_nan', 'Construction_Year_1850-1899', 'Construction_Year_1878', 'Construction_Year_1919-1944', 'Construction_Year_1945-1964', 'Construction_Year_1965-1974', 'Construction_Year_1966', 'Construction_Year_1975-1980', 'Construction_Year_1981-1990', 'Construction_Year_1988', 'Construction_Year_1991-1995', 'Construction_Year_2005', 'Construction_Year_Unknown', 'Construction_Year_mid_60s', 'Construction_Year_post_2002', 'Construction_Year_nan'] # PASTE YOUR LIST HERE

def get_prediction_and_recommendation(live_data, weather_data, house_id):
    """
    Takes live data for v2, makes a CO2 prediction, and returns a recommendation.
    """
    
    all_data = live_data.copy()
    all_data.update(weather_data)
    all_data['House_ID'] = house_id

    # Create a pandas DataFrame from the combined data
    live_df = pd.DataFrame([all_data])
    
    # Create time-based features
    now = datetime.now()
    live_df['Hour_of_Day'] = now.hour
    live_df['Day_of_Week'] = now.weekday()
    live_df['Is_Weekend'] = 1 if live_df['Day_of_Week'].iloc[0] >= 5 else 0
    
    # Set all feature columns, filling missing ones with 0
    for col in FEATURE_ORDER:
        if col not in live_df.columns:
            live_df[col] = 0
            
    # Ensure the columns are in the exact same order as the training data
    live_df = live_df[FEATURE_ORDER]
    
    # Make a prediction
    predicted_co2 = model.predict(live_df)[0]
    
    # Generate recommendation
    recommendation = "Emissions are normal. Great job!"
    if predicted_co2 > 0.01:
        high_power_appliances = {k: v for k, v in live_data.items() if v > 400}
        if high_power_appliances:
            top_appliance = max(high_power_appliances, key=high_power_appliances.get)
            recommendation = f"High emissions detected! The **{top_appliance.replace('_', ' ')}** is the main cause."
        else:
            recommendation = "High emissions detected! This may be due to heating/cooling needs."
            
    return predicted_co2, recommendation