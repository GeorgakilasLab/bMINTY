
// src/components/AddStudyRow.jsx
import React from 'react';
import { TableRow, TableCell, Button } from '@mui/material';
import { IoMdAddCircleOutline } from 'react-icons/io';

export default function AddStudyRow({ onAdd }) {
  return (
    <TableRow>
      <TableCell colSpan={6} align="center">
        <Button 
          variant="contained" 
          startIcon={<IoMdAddCircleOutline />} 
          onClick={onAdd}
        >
          Add Study
        </Button>
      </TableCell>
      <TableCell />
    </TableRow>
)};