// src/components/FilterSection.jsx
import React from 'react';
import { Box, IconButton, Typography, Collapse, Stack } from '@mui/material';
import { ExpandLess, ExpandMore } from '@mui/icons-material';

export default function FilterSection({ title, open, onToggle, children }) {
  return (
    <>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: open ? 'linear-gradient(90deg, rgba(59,130,246,0.06), rgba(59,130,246,0.02))' : 'transparent',
          p: 1,
          borderRadius: 1,
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: 400, color: '#0f172a' }}>{title}</Typography>
        <IconButton size="small" onClick={onToggle} sx={{ color: '#0d7634ff' }}>
          {open ? <ExpandLess /> : <ExpandMore />}
        </IconButton>
      </Box>
      <Collapse in={open} timeout="auto" unmountOnExit>
        <Box sx={{ mt: 1, mb: 1, pl: 1.5, borderLeft: '3px solid rgba(59,130,246,0.08)' }}>
          <Stack spacing={1}>
            {children}
          </Stack>
        </Box>
      </Collapse>
    </>
  );
}
