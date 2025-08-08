'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// Define the possible login types
export type LoginType = 'google' | 'github';

interface AuthSectionProps {
  authStatus: string;
  isSignedIn: boolean;
  onSignIn: (type: LoginType) => void;
  onSignOut: () => void;
  selectedLoginType: LoginType;
  onLoginTypeChange: (value: LoginType) => void;
}

export const AuthSection: React.FC<AuthSectionProps> = ({
  authStatus,
  isSignedIn,
  onSignIn,
  onSignOut,
  selectedLoginType,
  onLoginTypeChange,
}) => {
  const handleSignInClick = () => {
    onSignIn(selectedLoginType);
  };

  return (
    <div style={{ marginBottom: '10px', border: '1px dashed #ccc', padding: '10px' }}>
      <h2 style={{ marginTop: 0 }}>Authentication</h2>
      <p>
        Status: <span style={{ fontWeight: 'bold' }}>{authStatus}</span>
      </p>
      {!isSignedIn ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Select
            value={selectedLoginType}
            onValueChange={(value) => onLoginTypeChange(value as LoginType)}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select sign-in method" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="google">Google</SelectItem>
              <SelectItem value="github">GitHub</SelectItem>
            </SelectContent>
          </Select>

          <Button onClick={handleSignInClick}>Sign In</Button>
        </div>
      ) : (
        <Button onClick={onSignOut} variant="destructive">
          Sign Out
        </Button>
      )}
    </div>
  );
};

export default AuthSection;
