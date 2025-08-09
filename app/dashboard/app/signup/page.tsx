import { AuthTemplate } from '@/components/ui/auth-template';
import { SignupForm } from './_components/signup-form';
import { Suspense } from 'react';

export default async function SignUp() {
  return (
    <Suspense fallback={<div>Loading signup form...</div>}>
      <AuthTemplate>
        <SignupForm />
      </AuthTemplate>
    </Suspense>
  );
}
