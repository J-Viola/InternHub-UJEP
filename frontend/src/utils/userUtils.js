export const isStudent = (user) => user?.role?.toLowerCase() === 'st';
export const isAdmin = (user) => user?.role?.toLowerCase() === 'admin';
export const isOwner = (user) => user?.role?.toUpperCase() === 'OWNER';
export const isInserter = (user) => user?.role?.toUpperCase() === 'INSERTER';
export const isDepartmentMg = (user) => user?.role?.toLowerCase() === 'vk';
export const isProfessor = (user) => user?.role?.toLowerCase() === 'vy';

export const isOrganizationUser = (user) => {
    const role = user?.role?.toUpperCase();
    return ['OWNER', 'INSERTER'].includes(role);
};

export const isDepartmentUser = (user) => {
    const role = user?.role?.toLowerCase();
    return ['vk', 'vy'].includes(role);
};

export const hasData = (user) => user && user.email;