'use client';

import { CheckEmail, ContinueWith, MagicEmailForm, TOS } from '@/app/signin/components';
import { Alert01Icon as AlertIcon } from 'hugeicons-react';
import { Button } from '@/components/ui/button';
import { Container } from '@/components/ui/container';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from '@/components/ui/use-toast';
import { containerStyles, headingStyle, labelStyle } from '@/constants/styles';
import { cn } from '@/lib/utils';
import { EyeIcon as Eye, Mail01Icon as Mail, Tick03Icon, ViewOffIcon as PasswordViewIcon } from 'hugeicons-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

type formTypes = 'signup' | 'magiclink' | 'checkemail';

export function SignupForm() {
  const [formType, setFormType] = useState<formTypes>('signup');

  if (formType === 'checkemail') return <CheckEmail setFormType={setFormType} />;
  if (formType === 'magiclink') return <MagicEmailForm setFormType={setFormType} isSignUp={true} />;
  return <AuthForm setFormType={setFormType} />;
}

function AuthForm(props: { setFormType: CallableFunction }) {
  const [loading, setLoading] = useState<boolean>(false);
  const router = useRouter();
  const [viewPassword, setViewPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const validatePassword = (value: string) => {
    const minLength = 12;
    const hasDigit = /\d/.test(value);
    const hasLowercase = /[a-z]/.test(value);
    const hasUppercase = /[A-Z]/.test(value);
    const hasSymbol = /[!@#$%^&*(),.?":{}|<>]/.test(value);

    if (value.length < minLength) {
      return `Password must be at least ${minLength} characters long.`;
    }
    if (!hasDigit) {
      return 'Password must contain at least one digit.';
    }
    if (!hasLowercase) {
      return 'Password must contain at least one lowercase letter.';
    }
    if (!hasUppercase) {
      return 'Password must contain at least one uppercase letter.';
    }
    if (!hasSymbol) {
      return 'Password must contain at least one symbol.';
    }

    return null;
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setPassword(value);
    setPasswordError(validatePassword(value));
  };

  const handleSignupSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const validationError = validatePassword(password);
    if (validationError) {
      setPasswordError(validationError);
      toast({ title: '❌ Invalid Password', description: validationError, variant: 'destructive' });
      return;
    }
    setPasswordError(null);
    setLoading(true);

    const formData = new FormData(event.currentTarget);
    const email = formData.get('email') as string;
    const fullName = formData.get('fullName') as string;
    const authBaseUrl = `${process.env.NEXT_PUBLIC_API_URL || ''}/auth`;

    try {
      const response = await fetch(`${authBaseUrl}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName }),
      });

      if (!response.ok) {
        let errorBody = 'Signup failed.';
        try {
          const body = await response.json();
          errorBody = body.detail || JSON.stringify(body);
        } catch (e) {
          /* Ignore */
        }
        throw new Error(errorBody);
      }

      toast({
        title: 'Account Created',
        description:
          'Please verify your email to sign in! (check spam, and if it is in spam please mark as not spam <3)',
        icon: <Tick03Icon />,
        duration: 8000,
      });
      router.push('/signin');
    } catch (error: any) {
      console.error('Signup Error:', error);
      setLoading(false);
      toast({
        title: '❌ Signup Error',
        description: error.message || 'An unexpected error occurred.',
        variant: 'destructive',
        duration: 8000,
      });
    }
  };

  return (
    <>
      <Container className={containerStyles}>
        <div className="grid gap-6">
          <h1 className={headingStyle}>Sign Up</h1>
          <form className="grid gap-2" onSubmit={handleSignupSubmit}>
            <Label className={cn(labelStyle)} htmlFor="fullName">
              Full Name
            </Label>
            <Input
              className="mb-2 h-12"
              name="fullName"
              id="fullName"
              placeholder="John Doe"
              type="text"
              autoCapitalize="none"
              autoComplete="fullName"
              autoCorrect="off"
              disabled={loading}
              required
            />
            <Label className={cn(labelStyle)} htmlFor="email">
              Username
            </Label>
            <Input
              name="email"
              id="email"
              placeholder="name@example.com"
              type="email"
              autoCapitalize="none"
              autoComplete="email"
              autoCorrect="off"
              disabled={loading}
              required
              className="h-12"
            />
            <Label
              className="mb-2 mt-4 font-medium text-secondary dark:text-white"
              htmlFor="password"
            >
              Password
            </Label>
            <div className="relative">
              <Input
                disabled={loading}
                id="password"
                name="password"
                type={viewPassword ? 'text' : 'password'}
                placeholder="Your Password"
                required
                className="peer h-12 pl-3"
                value={password}
                onChange={handlePasswordChange}
              />
              <div
                className="absolute right-3 top-1/2 mt-0.5 hidden -translate-y-1/2 transform cursor-pointer peer-valid:flex"
                onClick={() => setViewPassword((prev) => !prev)}
              >
                {viewPassword ? <Eye size={20} /> : <PasswordViewIcon />}
              </div>
            </div>
            {passwordError && (
              <div className="flex items-center gap-1">
                <AlertIcon className="size-4 stroke-error" />
                <div className="mt-1 text-xs text-error">{passwordError}</div>
              </div>
            )}
            <Button type="submit" className="mt-4 py-[22px]" disabled={loading || !!passwordError}>
              <Mail className="mr-2 h-4 w-4" />
              Sign up with Email
            </Button>
            <ContinueWith setFormType={props.setFormType} isSignUp={true} />
          </form>
          <p className="text-sm text-secondary dark:text-white">
            {'Already have an account? '}{' '}
            <Button variant="link" className="p-0" onClick={() => router.push('/signin')}>
              Sign In
            </Button>
          </p>
        </div>
      </Container>
      <div className="mt-12 pr-3">
        <TOS />
      </div>
    </>
  );
}
