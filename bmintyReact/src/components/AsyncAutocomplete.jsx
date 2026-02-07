import React, { useState, useMemo, useEffect } from 'react';
import axios from 'axios';
import debounce from 'lodash.debounce';
import { Autocomplete, TextField, CircularProgress } from '@mui/material';

/**
 * AsyncAutocomplete
 * A reusable freeSolo Autocomplete that fetches suggestions via axios and shows all options on click.
 *
 * Props:
 * - name: string            // field name for API path
 * - label: string           // TextField label
 * - value: string           // current input value
 * - onChange: function      // called with new input value
 * - apiBase: string         // base URL, default API_BASE
 * - debounceMs: number      // delay in ms, default 300
 * - limit: number           // max suggestions, default 10
 * - currentFilters: object  // all current filter values for context-aware suggestions
 */
export default function AsyncAutocomplete({
  name,
  label,
  value,
  onChange,
  apiBase = process.env.REACT_APP_API_BASE || '',
  debounceMs = 300,
  limit = 10,
  currentFilters = {},
  sx = {},
}) {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  // debounced fetch via axios
  const fetchSuggestions = useMemo(
    () => {
      // Simple in-memory cache with ETag + TTL to avoid unnecessary refetches
      // Cache invalidates automatically when backend changes ETag or when TTL expires
      const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
      const cache = AsyncAutocompleteCache;
      
      const getCacheKey = (input) => {
        const endpoint = `${apiBase}/filters/${name}/`;
        // Include filter context in cache key so different filter combinations are cached separately
        // Only include non-empty, meaningful filter values
        const relevantFilters = {};
        if (currentFilters) {
          Object.keys(currentFilters).forEach(key => {
            const val = currentFilters[key];
            if (key !== name && val && val !== '' && val !== 'All') {
              relevantFilters[key] = val;
            }
          });
        }
        const filterStr = JSON.stringify(relevantFilters);
        return `${endpoint}|${input || ''}|limit=${limit}|filters=${filterStr}`;
      };
      
      return debounce(async (input) => {
        const key = getCacheKey(input);
        const cached = cache.get(key);
        const now = Date.now();

        // Use fresh cache immediately
        if (cached && (now - cached.timestamp < CACHE_TTL_MS)) {
          setOptions(cached.data || []);
          setLoading(false);
          return;
        }

        try {
          const url = `${apiBase}/filters/${name}/`;
          const headers = {};
          if (cached?.etag) headers['If-None-Match'] = cached.etag;

          // Build params including current filters for context-aware suggestions
          const params = { q: input, limit };
          
          // Add all current filters as query params (excluding the current field)
          // Only include non-empty values and skip default/neutral values
          if (currentFilters) {
            Object.keys(currentFilters).forEach(key => {
              const val = currentFilters[key];
              // Skip current field, empty values, and neutral availability values
              if (key !== name && val && val !== '' && val !== 'All') {
                params[key] = val;
              }
            });
          }

          const resp = await axios.get(url, {
            params,
            headers,
            validateStatus: (status) => (status >= 200 && status < 300) || status === 304,
          });

          if (resp.status === 304 && cached) {
            // Not modified -> use cached
            setOptions(cached.data || []);
          } else {
            const etag = resp.headers?.etag;
            const data = resp.data || [];
            cache.set(key, { data, etag, timestamp: now });
            setOptions(data);
          }
        } catch (err) {
          console.error('AsyncAutocomplete error', err);
        } finally {
          setLoading(false);
        }
      });
    },
    [apiBase, name, limit, currentFilters]
  );

  // fetch when input changes
  useEffect(() => {
    if (value) {
      setLoading(true);
      fetchSuggestions.cancel();
      const debouncedFetch = debounce(() => fetchSuggestions(value), debounceMs);
      debouncedFetch();
      return () => debouncedFetch.cancel();
    }
  }, [value, fetchSuggestions, debounceMs]);

  // cancel debounce on unmount
  useEffect(() => {
    return () => {
      fetchSuggestions.cancel();
    };
  }, [fetchSuggestions]);

  return (
    <Autocomplete
      freeSolo
      open={open}
      options={options}
      inputValue={value || ''}
      onInputChange={(e, newVal) => onChange(newVal)}
      onOpen={() => {
        setOpen(true);
        setLoading(true);
        fetchSuggestions('');
      }}
      onClose={() => setOpen(false)}
      filterOptions={(opts) => opts}
      getOptionLabel={(option) => (option && typeof option === 'string' ? option : '')}
      loading={loading}
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          size="small"
          fullWidth
          sx={sx}
          InputProps={{
            ...params.InputProps,
            endAdornment: (
              <>
                {loading ? <CircularProgress size={16} /> : null}
                {params.InputProps.endAdornment}
              </>
            ),
          }}
        />
      )}
    />
  );
}

// Global in-memory cache shared by all AsyncAutocomplete instances
const AsyncAutocompleteCache = new Map();

// Allow external cache busting when database changes are known (e.g., after import)
export function clearAsyncAutocompleteCache() {
  AsyncAutocompleteCache.clear();
}
