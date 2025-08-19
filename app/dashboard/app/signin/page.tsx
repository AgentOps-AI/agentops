import { AuthTemplate } from '@/components/ui/auth-template';
import { AuthForm } from './auth-form';
import { Suspense } from 'react';

export default async function SignIn() {
  return (
    <Suspense fallback={<div>Loading account form...</div>}>
      <AuthTemplate data-testid="signin-page-container">
        <AuthForm />
      </AuthTemplate>
    </Suspense>
  );
}
