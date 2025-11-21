# Roblox Expense Tracker

## Overview

A comprehensive Streamlit-based web application that tracks and visualizes Roblox transaction data with advanced analytics features. The application connects to the Roblox API to fetch user transaction history and presents expense analytics through interactive charts, metrics, budget tracking, forecasting, and comparison tools. Users can monitor their Roblox spending patterns, view transaction breakdowns, analyze purchase behavior over time, set budgets, compare periods, and predict future spending trends.

## Recent Changes

**November 21, 2025** - Added Phase 2 Features:
- CSV and JSON export functionality for transaction data
- Time-based filtering with custom date range selection and preset buttons (Last 7/30/90 Days, All Time)
- Spending budget tracking with customizable overall and monthly limits, progress bars, and color-coded alerts
- Period comparison views (Month vs Month, Week vs Week, Custom Period) with side-by-side metrics and trend indicators
- Data caching system with 30-minute expiry to reduce API calls and improve performance
- Spending trend forecasting using linear regression to predict next 3-6 months with confidence indicators

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit (Python web framework)
- **Rationale**: Streamlit provides rapid development of data-focused web applications with minimal frontend code, ideal for analytics dashboards
- **UI Components**: 
  - Custom CSS styling for dark theme (matches Roblox aesthetic)
  - Plotly for interactive data visualizations
  - Metric cards for key statistics display
- **Layout**: Wide layout with collapsed sidebar for maximum chart visibility

### Backend Architecture
- **Language**: Python
- **Structure**: Modular separation of concerns
  - `app.py`: Main Streamlit application and UI logic
  - `roblox_api.py`: Roblox API client implementation
  - `main.py`: Entry point (minimal, likely development artifact)
- **Data Processing**: Pandas for transaction data manipulation and analysis
- **API Client Pattern**: Session-based requests with cookie authentication

### Authentication & Authorization
- **Method**: Cookie-based authentication using `.ROBLOSECURITY` token
- **Rationale**: Roblox uses cookie-based sessions; users provide their authentication cookie to access their transaction data
- **Security Consideration**: Cookie storage handled client-side; application acts as authenticated proxy

### Data Visualization
- **Libraries**: 
  - Plotly Graph Objects and Plotly Express for interactive charts
  - NumPy for numerical computations
- **Chart Types**: Designed to support multiple visualization formats (specific implementations not shown in provided code)
- **Interactivity**: Client-side chart interactions via Plotly's built-in features

## External Dependencies

### Third-Party APIs
- **Roblox API**:
  - **Users API** (`users.roblox.com/v1`): Fetches authenticated user information
  - **Economy API** (`economy.roblox.com/v2`): Retrieves user transaction history
  - **Authentication**: Cookie-based via `.ROBLOSECURITY` token
  - **Rate Limiting**: Implements pagination with cursor-based navigation (100 transactions per request, configurable max up to 500)
  - **Transaction Types**: Filters for 'Purchase' transactions specifically

### Python Packages
- **streamlit**: Web application framework
- **pandas**: Data manipulation and analysis
- **plotly**: Interactive data visualization (both graph_objects and express modules)
- **requests**: HTTP library for API communication
- **numpy**: Numerical computing support

### Data Storage
- **Current Implementation**: No persistent database; data fetched on-demand from Roblox API
- **Session Management**: In-memory storage during application runtime via Streamlit's session state (implied)
- **Potential Enhancement**: Could integrate database for caching transaction history and reducing API calls