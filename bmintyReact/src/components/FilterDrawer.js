// src/components/FilterDrawer.js
import React from 'react';
import {
  Drawer,
  Box,
  Typography,
  FormControlLabel,
  Switch,
  TextField,
  Button,
  Divider,
} from '@mui/material';

const drawerWidth = 280;

const FilterDrawer = ({ filters, onFilterChange, onReset }) => (
  <Drawer
    variant="permanent"
    anchor="left"
    sx={{
      width: drawerWidth,
      flexShrink: 0,
      '& .MuiDrawer-paper': {
        width: drawerWidth,
        boxSizing: 'border-box',
        p: 2,
      },
    }}
  >
    <Box>
      <Typography variant="h6" gutterBottom>
        Filters
      </Typography>

      <FormControlLabel
        control={
          <Switch
            checked={filters.availability}
            onChange={(e) => onFilterChange('availability', e.target.checked)}
          />
        }
        label="Only Available"
      />

      <Box mt={2}>
        <TextField
          label="Search Title"
          value={filters.search}
          onChange={(e) => onFilterChange('search', e.target.value)}
          fullWidth
          size="small"
        />
      </Box>

      <Box mt={2}>
        <TextField
          label="Date From"
          type="date"
          value={filters.dateFrom}
          onChange={(e) => onFilterChange('dateFrom', e.target.value)}
          InputLabelProps={{ shrink: true }}
          fullWidth
          size="small"
        />
      </Box>

      <Box mt={2}>
        <TextField
          label="Date To"
          type="date"
          value={filters.dateTo}
          onChange={(e) => onFilterChange('dateTo', e.target.value)}
          InputLabelProps={{ shrink: true }}
          fullWidth
          size="small"
        />
      </Box>

      <Divider sx={{ my: 3 }} />

      <Button variant="outlined" onClick={onReset} fullWidth>
        Reset Filters
      </Button>
    </Box>
  </Drawer>
);

export default FilterDrawer;
