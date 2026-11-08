export const SKILL_CATEGORIES = ['technologies', 'tools', 'methodologies'];

export const SKILL_LABELS = {
  technologies: "Technologie",
  tools: "Nástroje",
  methodologies: "Metodiky",
};

export function normalizeSkills(value) {
    const source = Array.isArray(value) ? { technologies: value } : (value && typeof value === 'object' ? value : {});
    return Object.fromEntries(SKILL_CATEGORIES.map(category => [
        category,
        Array.isArray(source[category]) ? source[category].filter(item => typeof item === 'string' && item.trim()).map(item => item.trim()) : [],
    ]));
}

export function flattenSkills(value) {
    return SKILL_CATEGORIES.flatMap(category => normalizeSkills(value)[category]);
}
