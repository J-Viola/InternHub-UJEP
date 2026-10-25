import { flattenSkills, normalizeSkills } from './skills';

test('normalizes categorized and legacy skills', () => {
    expect(normalizeSkills({ technologies: [' React '], tools: ['Jest'] })).toEqual({
        technologies: ['React'], tools: ['Jest'], methodologies: [],
    });
    expect(normalizeSkills(['React'])).toEqual({ technologies: ['React'], tools: [], methodologies: [] });
    expect(flattenSkills(['React'])).toEqual(['React']);
});
