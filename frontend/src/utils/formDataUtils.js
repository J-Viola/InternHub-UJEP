/**
 * Utility to convert an object to FormData for multipart/form-data requests.
 * Handles nested objects and files.
 */
export const buildFormData = (data) => {
    const formData = new FormData();

    Object.keys(data).forEach(key => {
        const value = data[key];

        if (value === null || value === undefined) {
            return;
        }

        if (value instanceof File) {
            formData.append(key, value);
        } else if (Array.isArray(value)) {
            // For arrays, if they contain files, we must append individually.
            // If they are pure data, we JSON.stringify to send as a single field value.
            const hasFile = value.some(item => item instanceof File);
            if (hasFile) {
                value.forEach(item => {
                    formData.append(key, item);
                });
            } else {
                formData.append(key, JSON.stringify(value));
            }
        } else if (typeof value === 'object') {
            // If it's a date, format it? No, usually keep it as string if it's already formatted.
            // If it's a generic object, stringify it.
            formData.append(key, JSON.stringify(value));
        } else {
            formData.append(key, value);
        }
    });

    return formData;
};
