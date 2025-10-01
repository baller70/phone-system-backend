
"""
Phase 7: Demand Forecasting with Prophet
Predicts future booking demand for optimal resource planning
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class DemandForecaster:
    """
    ML-based demand forecasting using time series analysis
    Predicts booking demand for better resource allocation
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.model_cache = {}
        self.enabled = os.getenv('DEMAND_FORECAST_ENABLED', 'true').lower() == 'true'
    
    def get_historical_bookings(self, facility_id: Optional[int] = None, days: int = 365) -> pd.DataFrame:
        """
        Fetch historical booking data for analysis
        
        Args:
            facility_id: Optional facility ID to filter by
            days: Number of days of historical data to fetch
            
        Returns:
            DataFrame with date and booking count
        """
        try:
            query = """
                SELECT 
                    DATE(start_time) as date,
                    EXTRACT(HOUR FROM start_time) as hour,
                    COUNT(*) as bookings
                FROM bookings
                WHERE created_at >= NOW() - INTERVAL %s DAY
            """
            
            params = [days]
            
            if facility_id:
                query += " AND facility_id = %s"
                params.append(facility_id)
            
            query += " GROUP BY DATE(start_time), EXTRACT(HOUR FROM start_time) ORDER BY date, hour"
            
            cursor = self.db.cursor(dictionary=True)
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            
            df = pd.DataFrame(results)
            
            if df.empty:
                logger.warning("No historical booking data found")
                return pd.DataFrame(columns=['date', 'hour', 'bookings'])
            
            df['date'] = pd.to_datetime(df['date'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical bookings: {e}")
            return pd.DataFrame(columns=['date', 'hour', 'bookings'])
    
    def prepare_forecast_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for Prophet forecasting
        
        Args:
            df: Historical bookings DataFrame
            
        Returns:
            DataFrame in Prophet format (ds, y columns)
        """
        if df.empty:
            return pd.DataFrame(columns=['ds', 'y'])
        
        # Aggregate by date for daily forecasts
        daily_df = df.groupby('date')['bookings'].sum().reset_index()
        daily_df.columns = ['ds', 'y']
        
        return daily_df
    
    def forecast_demand(self, facility_id: Optional[int] = None, days_ahead: int = 30) -> Dict:
        """
        Forecast booking demand for the next N days
        
        Args:
            facility_id: Optional facility ID to forecast for
            days_ahead: Number of days to forecast
            
        Returns:
            Dictionary with forecast data and metadata
        """
        if not self.enabled:
            logger.info("Demand forecasting is disabled")
            return {'status': 'disabled', 'forecast': []}
        
        try:
            # Check if Prophet is available (optional dependency)
            try:
                from prophet import Prophet
            except ImportError:
                logger.warning("Prophet not installed. Falling back to simple moving average.")
                return self._simple_forecast(facility_id, days_ahead)
            
            # Fetch historical data
            historical_df = self.get_historical_bookings(facility_id=facility_id, days=365)
            
            if historical_df.empty or len(historical_df) < 30:
                logger.warning(f"Insufficient data for forecasting (only {len(historical_df)} records)")
                return {'status': 'insufficient_data', 'forecast': [], 'message': 'Need at least 30 days of data'}
            
            # Prepare data for Prophet
            prophet_df = self.prepare_forecast_data(historical_df)
            
            # Train Prophet model
            model = Prophet(
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=True if len(prophet_df) > 365 else False,
                changepoint_prior_scale=0.05  # Flexibility of trend changes
            )
            
            # Add holidays if available
            # model.add_country_holidays(country_name='US')
            
            model.fit(prophet_df)
            
            # Make future predictions
            future = model.make_future_dataframe(periods=days_ahead)
            forecast = model.predict(future)
            
            # Extract relevant forecast data
            forecast_data = []
            for idx, row in forecast.tail(days_ahead).iterrows():
                forecast_data.append({
                    'date': row['ds'].strftime('%Y-%m-%d'),
                    'predicted_bookings': max(0, round(row['yhat'], 2)),
                    'lower_bound': max(0, round(row['yhat_lower'], 2)),
                    'upper_bound': max(0, round(row['yhat_upper'], 2)),
                    'confidence': 'high' if abs(row['yhat'] - row['yhat_lower']) < row['yhat'] * 0.2 else 'medium'
                })
            
            # Store forecast in database
            self._store_forecast(forecast_data, facility_id)
            
            return {
                'status': 'success',
                'facility_id': facility_id,
                'forecast_days': days_ahead,
                'forecast': forecast_data,
                'model_type': 'prophet',
                'historical_data_points': len(prophet_df)
            }
            
        except Exception as e:
            logger.error(f"Error forecasting demand: {e}")
            return {'status': 'error', 'message': str(e), 'forecast': []}
    
    def _simple_forecast(self, facility_id: Optional[int], days_ahead: int) -> Dict:
        """
        Simple moving average forecast as fallback
        
        Args:
            facility_id: Optional facility ID
            days_ahead: Days to forecast
            
        Returns:
            Forecast dictionary
        """
        try:
            historical_df = self.get_historical_bookings(facility_id=facility_id, days=90)
            
            if historical_df.empty:
                return {'status': 'insufficient_data', 'forecast': []}
            
            # Calculate simple moving average
            daily_avg = historical_df.groupby('date')['bookings'].sum().mean()
            
            forecast_data = []
            today = datetime.now().date()
            
            for i in range(1, days_ahead + 1):
                forecast_date = today + timedelta(days=i)
                # Simple forecast with some randomness
                predicted = daily_avg * (0.9 + np.random.random() * 0.2)
                
                forecast_data.append({
                    'date': forecast_date.strftime('%Y-%m-%d'),
                    'predicted_bookings': round(predicted, 2),
                    'lower_bound': round(predicted * 0.8, 2),
                    'upper_bound': round(predicted * 1.2, 2),
                    'confidence': 'low'
                })
            
            return {
                'status': 'success',
                'facility_id': facility_id,
                'forecast_days': days_ahead,
                'forecast': forecast_data,
                'model_type': 'simple_moving_average'
            }
            
        except Exception as e:
            logger.error(f"Error in simple forecast: {e}")
            return {'status': 'error', 'message': str(e), 'forecast': []}
    
    def _store_forecast(self, forecast_data: List[Dict], facility_id: Optional[int]):
        """
        Store forecast data in database
        
        Args:
            forecast_data: List of forecast dictionaries
            facility_id: Optional facility ID
        """
        try:
            cursor = self.db.cursor()
            
            for forecast in forecast_data:
                query = """
                    INSERT INTO demand_forecasts 
                    (id, facility_id, forecast_date, predicted_bookings, confidence_lower, confidence_upper, created_at)
                    VALUES (UUID(), %s, %s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        predicted_bookings = VALUES(predicted_bookings),
                        confidence_lower = VALUES(confidence_lower),
                        confidence_upper = VALUES(confidence_upper),
                        created_at = NOW()
                """
                
                cursor.execute(query, (
                    facility_id,
                    forecast['date'],
                    forecast['predicted_bookings'],
                    forecast['lower_bound'],
                    forecast['upper_bound']
                ))
            
            self.db.commit()
            cursor.close()
            
            logger.info(f"Stored {len(forecast_data)} forecast records")
            
        except Exception as e:
            logger.error(f"Error storing forecast: {e}")
            self.db.rollback()
    
    def get_demand_level(self, facility_id: int, date: str, hour: int) -> str:
        """
        Get demand level for a specific date and time
        
        Args:
            facility_id: Facility ID
            date: Date string (YYYY-MM-DD)
            hour: Hour of day (0-23)
            
        Returns:
            Demand level: 'low', 'medium', 'high', 'surge'
        """
        try:
            # Fetch forecast for the date
            cursor = self.db.cursor(dictionary=True)
            query = """
                SELECT predicted_bookings, confidence_lower, confidence_upper
                FROM demand_forecasts
                WHERE facility_id = %s AND forecast_date = %s
                ORDER BY created_at DESC LIMIT 1
            """
            cursor.execute(query, (facility_id, date))
            forecast = cursor.fetchone()
            cursor.close()
            
            if not forecast:
                return 'medium'  # Default
            
            predicted = forecast['predicted_bookings']
            
            # Classify demand level
            if predicted < 3:
                return 'low'
            elif predicted < 6:
                return 'medium'
            elif predicted < 10:
                return 'high'
            else:
                return 'surge'
                
        except Exception as e:
            logger.error(f"Error getting demand level: {e}")
            return 'medium'


def get_demand_forecaster(db_connection):
    """Get DemandForecaster instance"""
    return DemandForecaster(db_connection)
