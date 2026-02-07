// src/components/ToggleAvailabilityButton.jsx
import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import { FaToggleOn, FaToggleOff } from 'react-icons/fa';

export default function ToggleAvailabilityButton({ studyId, study_availability, onToggle }) {
    const handleClick = () => onToggle(studyId, !study_availability);

    return (
        <Tooltip title={study_availability ? 'Deactivate study' : 'Activate study'}>
            <IconButton size="small" onClick={handleClick}>
                {study_availability ? <FaToggleOn size={24} className="text-green-500" /> : <FaToggleOff size={24} className="text-gray-500" />}
            </IconButton>
        </Tooltip>
    );
}
