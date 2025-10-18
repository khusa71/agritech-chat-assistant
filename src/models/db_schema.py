"""Database schema using SQLAlchemy ORM."""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Location(Base):
    """Location table for storing queried locations."""
    
    __tablename__ = 'locations'
    
    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    region = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    elevation_m = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    soil_data = relationship("SoilData", back_populates="location", cascade="all, delete-orphan")
    weather_data = relationship("WeatherData", back_populates="location", cascade="all, delete-orphan")
    rainfall_data = relationship("RainfallData", back_populates="location", cascade="all, delete-orphan")
    market_prices = relationship("MarketPrices", back_populates="location", cascade="all, delete-orphan")
    crop_recommendations = relationship("CropRecommendation", back_populates="location", cascade="all, delete-orphan")
    
    # Spatial index for lat/lon queries
    __table_args__ = (
        Index('idx_lat_lon', 'latitude', 'longitude'),
    )


class SoilData(Base):
    """Soil data table for caching soil information."""
    
    __tablename__ = 'soil_data'
    
    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=False, index=True)
    
    # Soil properties
    ph_h2o = Column(Float, nullable=True)
    organic_carbon = Column(Float, nullable=True)
    bulk_density = Column(Float, nullable=True)
    clay_content = Column(Float, nullable=True)
    sand_content = Column(Float, nullable=True)
    silt_content = Column(Float, nullable=True)
    texture = Column(String(50), nullable=True)
    depth_cm = Column(Integer, nullable=True)
    fertility_index = Column(Float, nullable=True)
    
    # Metadata
    data_source = Column(String(100), nullable=True)
    raw_data = Column(JSONB, nullable=True)  # Store raw API response
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    location = relationship("Location", back_populates="soil_data")


class WeatherData(Base):
    """Weather data table for storing weather information."""
    
    __tablename__ = 'weather_data'
    
    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=False, index=True)
    
    # Current weather
    temperature_c = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    pressure_hpa = Column(Float, nullable=True)
    wind_speed_ms = Column(Float, nullable=True)
    wind_direction_deg = Column(Float, nullable=True)
    visibility_km = Column(Float, nullable=True)
    uv_index = Column(Float, nullable=True)
    
    # Forecast data (stored as JSON)
    forecast_data = Column(JSONB, nullable=True)
    
    # Metadata
    location_name = Column(String(100), nullable=True)
    data_source = Column(String(100), nullable=True)
    raw_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    location = relationship("Location", back_populates="weather_data")


class RainfallData(Base):
    """Rainfall data table for storing precipitation records."""
    
    __tablename__ = 'rainfall_data'
    
    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=False, index=True)
    
    # Rainfall records (stored as JSON array)
    records = Column(JSONB, nullable=True)
    
    # Aggregated data
    total_precipitation_30d = Column(Float, nullable=True)
    total_precipitation_90d = Column(Float, nullable=True)
    average_daily_precipitation = Column(Float, nullable=True)
    precipitation_trend = Column(String(20), nullable=True)
    
    # Metadata
    location_name = Column(String(100), nullable=True)
    data_period_days = Column(Integer, nullable=True)
    data_source = Column(String(100), nullable=True)
    raw_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    location = relationship("Location", back_populates="rainfall_data")


class MarketPrices(Base):
    """Market prices table for storing crop price data."""
    
    __tablename__ = 'market_prices'
    
    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=False, index=True)
    
    # Price data (stored as JSON)
    prices = Column(JSONB, nullable=True)
    analyses = Column(JSONB, nullable=True)
    
    # Metadata
    market_location = Column(String(100), nullable=True)
    data_source = Column(String(100), nullable=True)
    raw_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    location = relationship("Location", back_populates="market_prices")


class CropRecommendation(Base):
    """Crop recommendations table for storing generated recommendations."""
    
    __tablename__ = 'crop_recommendations'
    
    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=False, index=True)
    
    # Recommendation data
    recommendations = Column(JSONB, nullable=False)  # Array of crop recommendations
    
    # Metadata
    total_crops_analyzed = Column(Integer, nullable=True)
    min_suitability_threshold = Column(Float, nullable=True)
    data_sources_used = Column(JSONB, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    location = relationship("Location", back_populates="crop_recommendations")


class CropRequirements(Base):
    """Crop requirements reference table."""
    
    __tablename__ = 'crop_requirements'
    
    id = Column(Integer, primary_key=True, index=True)
    crop_name = Column(String(100), nullable=False, unique=True, index=True)
    
    # Growing requirements
    ph_min = Column(Float, nullable=False)
    ph_max = Column(Float, nullable=False)
    ph_optimal = Column(Float, nullable=False)
    temp_min_c = Column(Float, nullable=False)
    temp_max_c = Column(Float, nullable=False)
    temp_optimal_c = Column(Float, nullable=False)
    rainfall_min_mm = Column(Float, nullable=False)
    rainfall_max_mm = Column(Float, nullable=True)
    growing_season_months = Column(JSONB, nullable=False)  # Array of months
    soil_types = Column(JSONB, nullable=True)  # Array of preferred soil types
    water_requirement = Column(String(20), nullable=False)
    growth_duration_days = Column(Integer, nullable=False)
    typical_yield_per_acre = Column(Float, nullable=False)
    base_market_price_per_kg = Column(Float, nullable=False)
    
    # Metadata
    data_source = Column(String(100), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_crop_name', 'crop_name'),
    )
