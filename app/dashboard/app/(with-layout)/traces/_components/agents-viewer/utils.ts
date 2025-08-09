// Parse string or array data that might be in JSON format
export const parseJsonData = (data: any, fallback: any[] = []): any[] => {
    if (!data) return fallback;

    try {
        if (typeof data === 'string') {
            return JSON.parse(data);
        }
        return Array.isArray(data) ? data : [data];
    } catch (e) {
        return Array.isArray(data) ? data : [data];
    }
}; 