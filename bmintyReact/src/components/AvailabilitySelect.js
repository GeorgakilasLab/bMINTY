// src/components/AvailabilitySelect.jsx
import React from 'react';
import { FormControl, InputLabel, Select, MenuItem } from '@mui/material';

export default function AvailabilitySelect({ label = 'Availability', name, value, onChange }) {
  return (
    <FormControl size="small" fullWidth>
      <InputLabel>{label}</InputLabel>
      <Select
        name={name}
        value={value}
        label={label}
        onChange={onChange}
        size="small"
      >
        <MenuItem value="all">All</MenuItem>
        <MenuItem value="available">Available only</MenuItem>
        <MenuItem value="unavailable">Unavailable only</MenuItem>
      </Select>
    </FormControl>
  );
}
