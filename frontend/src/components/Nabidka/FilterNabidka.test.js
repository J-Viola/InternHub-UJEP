import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FilterNabidka from './FilterNabidka';
import { EMPLOYMENT_TYPE_OPTIONS } from './employmentTypes';
import { useTranslation } from 'react-i18next';

jest.mock('react-i18next', () => ({
    useTranslation: jest.fn(),
}));

describe('FilterNabidka — BL-05 / RF-02a filtr typu úvazku', () => {
    const handleFilterChange = jest.fn();
    const onSearchClear = jest.fn();
    const onSearchSubmit = jest.fn();
    const onClearAll = jest.fn();

    const renderFilter = (filterValue = {}) =>
        render(
            <FilterNabidka
                filterValue={filterValue}
                handleFilterChange={handleFilterChange}
                onSearchClear={onSearchClear}
                onSearchSubmit={onSearchSubmit}
                onClearAll={onClearAll}
                hasActiveFilters={Object.keys(filterValue).length > 0}
                locations={['Praha']}
                subjects={[{ value: '1', label: 'Java' }]}
            />
        );

    beforeEach(() => {
        useTranslation.mockReturnValue({ t: (key) => key });
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('renders employment type filter with placeholder code-list options', () => {
        renderFilter();

        const select = screen.getByLabelText(/offers\.filter\.employment_type/);
        expect(select).toBeInTheDocument();

        const optionValues = Array.from(select.options).map((opt) => opt.value);
        expect(optionValues).toEqual(['', ...EMPLOYMENT_TYPE_OPTIONS.map((o) => o.value)]);
        // Závazné kódy dle guarantor-values.md §1 (2026-10-11); stažené
        // placeholder_* kódy už v číselníku NENÍ.
        expect(optionValues).toContain('uvazek_0_5');
        expect(optionValues).toContain('uvazek_1_0');
        expect(optionValues).not.toContain('placeholder_part_time');
        expect(optionValues).not.toContain('placeholder_full_time');
        expect(screen.getByText('offers.filter.employment_type_part_time')).toBeInTheDocument();
        expect(screen.getByText('offers.filter.employment_type_full_time')).toBeInTheDocument();
    });

    test('selecting a value passes employment_type to the generic filter state', () => {
        renderFilter();

        const select = screen.getByLabelText(/offers\.filter\.employment_type/);
        fireEvent.change(select, { target: { value: 'uvazek_0_5' } });

        expect(handleFilterChange).toHaveBeenCalledWith(null, 'employment_type', 'uvazek_0_5', true);
        expect(onSearchClear).not.toHaveBeenCalled();
    });

    test('resetting to "all" clears employment_type from the filter state', () => {
        renderFilter({ employment_type: 'uvazek_1_0' });

        const select = screen.getByLabelText(/offers\.filter\.employment_type/);
        expect(select.value).toBe('uvazek_1_0');

        fireEvent.change(select, { target: { value: '' } });
        expect(onSearchClear).toHaveBeenCalledWith('employment_type');
        expect(handleFilterChange).not.toHaveBeenCalled();
    });

    test('keeps employment_type from the URL/filter state in sync with the select', () => {
        renderFilter({ employment_type: 'uvazek_0_5' });

        const select = screen.getByLabelText(/offers\.filter\.employment_type/);
        expect(select.value).toBe('uvazek_0_5');
    });
});
