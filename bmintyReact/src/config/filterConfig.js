import {
    assayTypeOptions,
    tissueOptions,
    cellTypeOptions,
    treatmentOptions,
    platformOptions,
    intervalTypeOptions,
    biotypeOptions,
    speciesOptions,
  } from './options';
  
  export const filterConfigs = {
    Assay: {
      filters: [
        { key: 'type',      label: 'Type',      component: 'Select',       options: assayTypeOptions,   multiple: true },
        { key: 'tissue',    label: 'Tissue',    component: 'Autocomplete', options: tissueOptions,      multiple: true },
        { key: 'cell_type', label: 'Cell Type', component: 'Autocomplete', options: cellTypeOptions,   multiple: true },
        { key: 'treatment', label: 'Treatment', component: 'Autocomplete', options: treatmentOptions, multiple: true },
        { key: 'platform',  label: 'Platform',  component: 'Select',       options: platformOptions,   multiple: true },
      ],
      ordering: [
        { key: 'date',     label: 'Date'     },
        { key: 'type',     label: 'Type'     },
        { key: 'platform', label: 'Platform' },
      ],
    },
  
    Interval: {
      filters: [
        { key: 'type',    label: 'Type',    component: 'Select', options: intervalTypeOptions, multiple: true },
        { key: 'biotype', label: 'Biotype', component: 'Select', options: biotypeOptions,     multiple: true },
      ],
      ordering: [
        { key: 'chromosome', label: 'Chromosome' },
        { key: 'start',      label: 'Start'      },
      ],
    },
  
    Assembly: {
      filters: [
        { key: 'species', label: 'Species', component: 'Autocomplete', options: speciesOptions, multiple: false },
        { key: 'name',    label: 'Name',    component: 'TextField' },
      ],
      ordering: [],
    },
  
    Signal: {
      filters: [
        { key: 'assay__type', label: 'Assay Type', component: 'Select', options: assayTypeOptions, multiple: true },
      ],
      ordering: [],
    },
  
    Study: {
      filters: [
        { key: 'available', label: 'Only Available', component: 'Switch' },
        { key: 'search',    label: 'Search Title',   component: 'TextField' },
        // add dateFrom/dateTo if desired
      ],
      ordering: [
        // e.g. { key: 'name', label: 'Name' }, etc.
      ],
    },
  };
  