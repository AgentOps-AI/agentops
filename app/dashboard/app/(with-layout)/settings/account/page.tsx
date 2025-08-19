import AccountForm from './components/account-form';
import { Suspense } from 'react';

export default async function SettingsAccountPage() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium" data-testid="account-settings-header">
          Account Details
        </h3>
        <p className="text-sm text-muted-foreground">
          Update your account settings. Set your preferred language and timezone.
        </p>
      </div>
      <Suspense fallback={<div>Loading account form...</div>}>
        <AccountForm />
      </Suspense>
    </div>
  );
}
