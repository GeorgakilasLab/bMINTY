// Centralized API configuration for the frontend
// Environment variables:
// - REACT_APP_API_BASE: full base URL (e.g., http://127.0.0.1:8000/api)
// - REACT_APP_API_PROTOCOL: protocol (default 'http')
// - REACT_APP_API_HOST: host (default '127.0.0.1')
// - REACT_APP_API_PORT: port (default '8000')

export const API_PROTOCOL = process.env.REACT_APP_API_PROTOCOL || 'http';
export const API_HOST = process.env.REACT_APP_API_HOST || '127.0.0.1';
export const API_PORT = process.env.REACT_APP_API_PORT || '8000';
export const API_BASE = process.env.REACT_APP_API_BASE || `${API_PROTOCOL}://${API_HOST}:${API_PORT}/api`;
