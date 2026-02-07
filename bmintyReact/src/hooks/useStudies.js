// src/hooks/useStudies.js
import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import useDebounce from './useDebounce';
import { API_BASE } from '../config';

export function useStudies(initialFilters = {}, initialPageSize = 10) {
  const [studies, setStudies] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(initialPageSize);
  const [filters, setFilters] = useState(initialFilters);
  const debouncedFilters = useDebounce(filters, 300);
  const [orderBy, setOrderBy] = useState('');
  const [orderDir, setOrderDir] = useState('asc');
  const [loading, setLoading] = useState(false);
  const cancelTokenRef = useRef(null);
  const lastSuccessfulFiltersRef = useRef(initialFilters);

  // Function to cancel the current request
  const cancelRequest = useCallback(() => {
    if (cancelTokenRef.current) {
      cancelTokenRef.current.cancel('Request cancelled by user');
      cancelTokenRef.current = null;
      setLoading(false);
      // Revert to last successful filters
      setFilters(lastSuccessfulFiltersRef.current);
    }
  }, []);

  // 1) Define fetchStudies as a stable callback:
  const fetchStudies = useCallback(async (pg = page, pgSize = rowsPerPage) => {
    // Cancel any existing request
    if (cancelTokenRef.current) {
      cancelTokenRef.current.cancel('New request initiated');
    }

    // Create new cancel token
    cancelTokenRef.current = axios.CancelToken.source();
    
    setLoading(true);
    
    try {
      const params = {
        page: pg + 1,
        page_size: pgSize,
        order_by: orderBy,
        order_dir: orderDir,
      };

      // Process filters: convert arrays to param[] format for Django
      Object.keys(debouncedFilters).forEach((key) => {
        const value = debouncedFilters[key];
        
        // Skip empty values
        if (value === '' || value == null) {
          return;
        }
        
        // Handle arrays - Django expects param_name[] format
        if (Array.isArray(value)) {
          if (value.length > 0) {
            // Use the [] suffix for Django's getlist()
            params[`${key}[]`] = value;
          }
        } else {
          params[key] = value;
        }
      });

      // Map study_availability: 'all' → remove, 'available' → true, 'unavailable' → false
      if (params.study_availability === 'all') {
        delete params.study_availability;
      } else if (params.study_availability === 'available') {
        params.study_availability = true;
      } else if (params.study_availability === 'unavailable') {
        params.study_availability = false;
      }

      // Map assay_availability similarly
      if (params.assay_availability === 'all') {
        delete params.assay_availability;
      } else if (params.assay_availability === 'available') {
        params.assay_availability = true;
      } else if (params.assay_availability === 'unavailable') {
        params.assay_availability = false;
      }

      // Log the parameters for debugging
      console.log('Fetching studies with params:', params);

      const resp = await axios.get(`${API_BASE}/studies/`, { 
        params,
        cancelToken: cancelTokenRef.current.token,
        paramsSerializer: {
          indexes: null, // This tells axios to use format: key[]=value1&key[]=value2
        }
      });
      setStudies(resp.data.results);
      setTotalCount(resp.data.count);
      // Store the successful filters for potential cancellation
      lastSuccessfulFiltersRef.current = debouncedFilters;
      cancelTokenRef.current = null;
    } catch (err) {
      if (!axios.isCancel(err)) {
        console.error('Error fetching studies:', err);
      }
      cancelTokenRef.current = null;
    } finally {
      setLoading(false);
    }
  }, [
    page,
    rowsPerPage,
    orderBy,
    orderDir,
    debouncedFilters,
  ]);

  // 2) Call it whenever its inputs change:
  useEffect(() => {
    fetchStudies(page, rowsPerPage);
  }, [fetchStudies, page, rowsPerPage]);

  return {
    studies,
    totalCount,
    page,
    rowsPerPage,
    filters,
    orderBy,
    orderDir,
    loading,
    setPage,
    setRowsPerPage,
    setFilters,
    setOrderBy,
    setOrderDir,
    setStudies,
    fetchStudies,    // ← now properly defined
    cancelRequest,   // ← new: cancel current request
  };
}
