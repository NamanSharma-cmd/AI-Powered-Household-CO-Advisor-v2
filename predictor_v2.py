import joblib
import pandas as pd
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CO2Predictor:
    """
    Handles loading the LightGBM model and making predictions for CO2 emissions.
    """
    
    # Feature order expected by the model (CRITICAL: Must match training data exactly)
    FEATURE_ORDER = [
        'House_ID', 'Occupancy', 'Blender', 'Bread-maker', 'Chest_Freezer', 'Computer', 
        'Computer_Site', 'Dehumidifier', 'Desktop_Computer', 'Dishwasher', 'Electric_Heater', 
        'Electric_Heater_1', 'Electric_Heater_2', 'Food_Mixer', 'Freezer', 'Freezer_1', 
        'Freezer_2', 'Freezer_Garage', 'Fridge', 'Fridge-Freezer', 'Fridge-Freezer_1', 
        'Fridge-Freezer_2', 'Fridge_Freezer', 'Fridge_Garage', 'Games_Console', 'Hi-Fi', 
        'K_Mix', 'Kettle', 'MJY_Computer', 'Microwave', 'Microwave_2', 'Network_Site', 
        'Overhead_Fan', 'PGM_Computer', 'Pond_Pump', 'Router', 'TV_Satellite', 
        'TV_Site_Bedroom', 'Television', 'Television_Site', 'Toaster', 'Tumble_Dryer', 
        'Vivarium', 'Washer_Dryer', 'Washer_Dryer_Garage', 'Washing_Machine', 
        'Washing_Machine_1', 'Washing_Machine_2', 'max_temp_°c', 'humidity_%', 'rain_mm', 
        'Hour_of_Day', 'Day_of_Week', 'Is_Weekend', 'Type_Detached', 'Type_Mid-terrace', 
        'Type_Semi-detached', 'Type_nan', 'Size_2_bed', 'Size_3_bed', 'Size_4_bed', 
        'Size_5_bed', 'Size_nan', 'Construction_Year_1850-1899', 'Construction_Year_1878', 
        'Construction_Year_1919-1944', 'Construction_Year_1945-1964', 
        'Construction_Year_1965-1974', 'Construction_Year_1966', 
        'Construction_Year_1975-1980', 'Construction_Year_1981-1990', 
        'Construction_Year_1988', 'Construction_Year_1991-1995', 'Construction_Year_2005', 
        'Construction_Year_Unknown', 'Construction_Year_mid_60s', 
        'Construction_Year_post_2002', 'Construction_Year_nan'
    ]

    def __init__(self, model_path='co_model_v2.joblib'):
        self.model_path = model_path
        self.model = self._load_model()

    def _load_model(self):
        """Loads the model from disk."""
        if not os.path.exists(self.model_path):
            logging.error(f"Model file not found at {self.model_path}")
            return None
        try:
            model = joblib.load(self.model_path)
            logging.info(f"Model loaded successfully from {self.model_path}")
            return model
        except Exception as e:
            logging.error(f"Failed to load model: {e}")
            return None

    def predict(self, live_data: dict, weather_data: dict, house_id: int) -> tuple[float, str]:
        """
        Takes live appliance data, weather data, and house ID to predict CO2 emissions.
        Returns: (predicted_co2, recommendation_string)
        """
        if self.model is None:
            return 0.0, "Error: Model not loaded. Please check model file."

        # Combine inputs
        all_data = live_data.copy()
        all_data.update(weather_data)
        all_data['House_ID'] = house_id
        
        # Create DataFrame for prediction
        live_df = pd.DataFrame([all_data])
        
        # Add time-based features
        now = datetime.now()
        live_df['Hour_of_Day'] = now.hour
        live_df['Day_of_Week'] = now.weekday()
        live_df['Is_Weekend'] = 1 if live_df['Day_of_Week'].iloc[0] >= 5 else 0
        
        # Ensure all required features exist (fill missing with 0)
        for col in self.FEATURE_ORDER:
            if col not in live_df.columns:
                live_df[col] = 0
                
        # Reorder columns to match training data exactly
        live_df = live_df[self.FEATURE_ORDER]
        
        try:
            # Make prediction
            predicted_co2 = self.model.predict(live_df)[0]
        except Exception as e:
            logging.error(f"Prediction failed: {e}")
            return 0.0, "Error during prediction."
        
        # Generate recommendation logic
        recommendation = self._generate_recommendation(predicted_co2, live_data)
            
        return float(predicted_co2), recommendation

    def _generate_recommendation(self, predicted_co2: float, live_data: dict) -> str:
        """Generates a user-friendly recommendation based on prediction."""
        if predicted_co2 <= 0.05:
            return "✅ Emissions are normal. Great job maintaining efficiency!"
        
        # Identify high-power consumers (>400W is arbitrary threshold for 'high')
        high_power_appliances = {k: v for k, v in live_data.items() if v > 400}
        
        if high_power_appliances:
            # Find the biggest consumer
            top_appliance = max(high_power_appliances, key=high_power_appliances.get)
            appliance_name = top_appliance.replace('_', ' ').title()
            return f"⚠️ High emissions detected! The **{appliance_name}** is a major contributor. Consider optimizing its usage."
        
        return "⚠️ High emissions detected! This may be due to background heating/cooling loads or weather conditions."

    def calculate_scrubber_runtime(self, co2_kg: float) -> int:
        """
        Calculates the estimated runtime (in minutes) required to scrub the predicted CO2.
        Based on a hypothetical removal rate of 0.05 kg/hour.
        """
        SCRUBBER_RATE_KG_PER_HOUR = 0.05  # Adjust based on hardware calibration
        
        if co2_kg <= 0:
            return 0
            
        hours_needed = co2_kg / SCRUBBER_RATE_KG_PER_HOUR
        minutes_needed = int(hours_needed * 60)
        
        # Minimum runtime of 5 minutes if any CO2 is detected
        return max(5, minutes_needed) if minutes_needed > 0 else 0

# Singleton instance for easy import
predictor = CO2Predictor()

def get_prediction_and_recommendation(live_data, weather_data, house_id):
    """Wrapper function for backward compatibility with existing code."""
    co2, rec = predictor.predict(live_data, weather_data, house_id)
    runtime = predictor.calculate_scrubber_runtime(co2)
    return co2, rec, runtime
