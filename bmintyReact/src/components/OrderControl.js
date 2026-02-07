// src/components/OrderControl.jsx
import React from 'react';
import { Box, FormControl, InputLabel, Select, MenuItem, IconButton } from '@mui/material';
import { KeyboardArrowUp, KeyboardArrowDown } from '@mui/icons-material';

export default function OrderControl({
  label = 'Order',
  value,
  direction,
  options = [],
  onChange,
  onToggle,
}) {
  return (
    <Box display="flex" alignItems="center" mt={1}>
      <FormControl size="small" fullWidth>
        <InputLabel>{label}</InputLabel>
        <Select
          value={value}
          label={label}
          onChange={(e) => onChange(e.target.value)}
          size="small"
        >
          {options.map((opt) => (
            <MenuItem key={opt.value} value={opt.value}>
              {opt.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <IconButton size="small" onClick={onToggle}>
        {direction === 'asc' ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
      </IconButton>
    </Box>
  );
}
