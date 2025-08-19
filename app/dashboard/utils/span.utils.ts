import { ISpan } from '@/types/ISpan';

export const isRootSpan = (span: ISpan) => {
  // Supabase returns NULL as a string I guess -.-
  return (
    span.parent_span_id === 'NULL' ||
    span.parent_span_id === null ||
    span.parent_span_id === undefined
  );
};

// Function to transform the array - works with both simple and complex structures
export const transformPromptArray = (arr: any[]) => {
  const result: any[] = [];

  // Process each item in the array
  arr.forEach((item) => {
    // Get all keys in the current object
    const keys = Object.keys(item);

    // For each key, extract the inner object and add it to the result
    keys.forEach((key) => {
      if (typeof item[key] === 'object' && item[key] !== null) {
        result.push(item[key]);
      }
    });
  });

  return result;
};
