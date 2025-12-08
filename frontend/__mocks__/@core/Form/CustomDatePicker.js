import React from 'react';

const CustomDatePicker = ({ label, value, onChange, id, error, locked, required }) => (
  <input
    data-testid={`datepicker-${id}`}
    id={id}
    aria-label={label}
    value={value || ''}
    onChange={(e) => onChange({ [id]: e.target.value })}
    readOnly={locked}
    disabled={locked}
    data-error={error ? 'true' : 'false'}
    aria-required={required}
  />
);

export default CustomDatePicker;
