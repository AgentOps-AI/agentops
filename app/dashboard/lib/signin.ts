const defaultMethods = 'email,magic,google,github';
export const signInMethods = (process.env.NEXT_PUBLIC_SIGNIN_METHODS || defaultMethods).split(',');
