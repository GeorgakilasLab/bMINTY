import React, { useState, useMemo, useEffect } from 'react';
import axios from 'axios';
import debounce from 'lodash.debounce';
import { Autocomplete, TextField, CircularProgress, Chip, Box } from '@mui/material';

/**
 * MultiSelectAutocomplete
 * An enhanced autocomplete that allows multiple selections with OR logic.
 * Multiple selections are sent as comma-separated values to the backend.
 *
 * Props:
 * - name: string               // field name for API path
 * - label: string              // TextField label
 * - values: array of strings   // currently selected values
 * - onChange: function         // called with new array of values
 * - apiBase: string            // base URL
 * - debounceMs: number         // delay in ms, default 300
 * - limit: number              // max suggestions, default 10
 * - currentFilters: object     // all current filter values for context-aware suggestions
 */

// Simple in-memory cache
const AsyncAutocompleteCache = {
  _store: new Map(),
  get(key) {
    return this._store.get(key);
  },
  set(key, data) {
    this._store.set(key, data);
  },
  clear() {
    this._store.clear();
  },
};

export { AsyncAutocompleteCache };

export default function MultiSelectAutocomplete({
  name,
  label,
  values = [],
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
  const [inputValue, setInputValue] = useState('');

  const fetchSuggestions = useMemo(
    () => {
      const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
      const cache = AsyncAutocompleteCache;
      
      const getCacheKey = (input) => {
        const endpoint = `${apiBase}/filters/${name}/`;
        const relevantFilters = {};
        if (currentFilters) {
          Object.keys(currentFilters).forEach(key => {
            // For multi-select fields, don't exclude values array
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

        if (cached && (now - cached.timestamp < CACHE_TTL_MS)) {
          setOptions(cached.data || []);
          setLoading(false);
          return;
        }

        try {
          const url = `${apiBase}/filters/${name}/`;
          const headers = {};
          if (cached?.etag) headers['If-None-Match'] = cached.etag;

          const params = { q: input, limit };
          
          // Add all current filters as query params (excluding the current field)
          if (currentFilters) {
            Object.keys(currentFilters).forEach(key => {
              const val = currentFilters[key];
              // Skip the multi-select field itself (value is array)
              if (key !== name && val && val !== '' && val !== 'All' && !Array.isArray(val)) {
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
            setOptions(cached.data || []);
          } else {
            const etag = resp.headers?.etag;
            const data = resp.data || [];
            cache.set(key, { data, etag, timestamp: now });
            setOptions(data);
          }
        } catch (err) {
          console.error('MultiSelectAutocomplete error', err);
        } finally {
          setLoading(false);
        }
      });
    },
    [apiBase, name, limit, currentFilters]
  );

  // Fetch when input changes
  useEffect(() => {
    if (inputValue) {
      setLoading(true);
      fetchSuggestions.cancel();
      const debouncedFetch = debounce(() => fetchSuggestions(inputValue), debounceMs);
      debouncedFetch();
      return () => debouncedFetch.cancel();
    }
  }, [inputValue, fetchSuggestions, debounceMs]);

  // Cancel debounce on unmount
  useEffect(() => {
    return () => {
      fetchSuggestions.cancel();
    };
  }, [fetchSuggestions]);

  const handleAddValue = (newVal) => {
    if (newVal && !values.includes(newVal)) {
      onChange([...values, newVal]);
      setInputValue('');
    }
  };

  const handleRemoveValue = (valToRemove) => {
    onChange(values.filter(v => v !== valToRemove));
    // Keep the autocomplete open so user can continue selecting
    setInputValue('');
    // Don't close - let user continue selecting if desired
  };

  return (
    <Box>
      <Autocomplete
        freeSolo
        open={open}
        options={options}
        inputValue={inputValue || ''}
        onInputChange={(e, newVal, reason) => {
          if (reason === 'input' || reason === 'clear') {
            setInputValue(newVal);
          }
        }}
        onChange={(e, newVal) => {
          if (newVal) {
            handleAddValue(newVal);
          }
        }}
        onOpen={() => {
          setOpen(true);
          setLoading(true);
          fetchSuggestions('');
        }}
        onClose={() => {
          // Only close if input is empty
          if (!inputValue) {
            setOpen(false);
          }
        }}
        filterOptions={(opts) => opts}
        getOptionLabel={(option) => (option && typeof option === 'string' ? option : '')}
        loading={loading}
        renderInput={(params) => (
          <TextField
            {...params}
            label={label}
            placeholder={values.length > 0 ? '' : `Add ${label}...`}
            InputProps={{
              ...params.InputProps,
              endAdornment: (
                <>
                  {loading ? <CircularProgress color="inherit" size={20} /> : null}
                  {params.InputProps.endAdornment}
                </>
              ),
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                '&:hover fieldset': {
                  borderColor: '#4caf50',
                },
                '&.Mui-focused fieldset': {
                  borderColor: '#4caf50',
                },
              },
              '& .MuiInputLabel-root.Mui-focused': {
                color: '#4caf50',
              },
            }}
          />
        )}
        sx={sx}
      />
      
      {/* Render selected values as chips */}
      {values.length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
          {values.map((val) => (
            <Chip
              key={val}
              label={val}
              onDelete={() => handleRemoveValue(val)}
              sx={{ backgroundColor: '#4caf50', color: '#fff', fontWeight: 500 }}
              variant="filled"
            />
          ))}
        </Box>
      )}
    </Box>
  );
}
