import React from 'react';

const DropDown = ({ label, value, onChange, id, options, error, required }) => (
  <select
    data-testid={`dropdown-${id}`}
    id={id}
    aria-label={label}
    value={value || ''}
    onChange={(e) => onChange({ [id]: e.target.value })}
    data-error={error ? 'true' : 'false'}
    aria-required={required}
  >
    {options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
  </select>
);

export default DropDown;
