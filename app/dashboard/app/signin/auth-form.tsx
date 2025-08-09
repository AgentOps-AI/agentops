'use client';

import { Button } from '@/components/ui/button';
import { Container } from '@/components/ui/container';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from '@/components/ui/use-toast';
import { containerStyles, headingStyle, labelStyle } from '@/constants/styles';
import { deleteCache } from '@/lib/idb';
import { signInMethods } from '@/lib/signin';
import { cn } from '@/lib/utils';
import { EyeIcon as Eye, ViewOffIcon } from 'hugeicons-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState, FormEvent, useEffect } from 'react';
import { CheckEmail, ContinueWith, MagicEmailForm, TOS, handleSignIn } from './components';
import { Loader2 } from 'lucide-react';

type formTypes = 'signin' | 'magiclink' | 'recovery' | 'checkemail';

export function AuthForm() {
  const [formType, setFormType] = useState<formTypes>('signin');
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.location.hash) {
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      if (hashParams.get('access_token')) {
        const queryString = window.location.search;
        window.location.href = `/auth/callback${queryString}${window.location.hash}`;
        return;
      }
    }

    const invite = searchParams.get('invite');
    if (invite) {
      console.log('Detected invite parameter:', invite);
      sessionStorage.setItem('pendingInvite', invite);
    }

    const checkAuth = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/opsboard/users/me`, {
          method: 'GET',
          credentials: 'include',
        });

        if (response.ok) {
          const nextPath = searchParams.get('next') || '/projects';
          router.push(nextPath.startsWith('/') ? nextPath : `/${nextPath}`);
          return;
        }
      } catch (_error) {
        console.error('Error checking authentication');
      }

      // Only run cleanup if user is not authenticated
      if (typeof window !== 'undefined') {
        deleteCache();
        localStorage.removeItem('theme');
        localStorage.removeItem('projects');
        localStorage.removeItem('selectedProject');
      }

      setIsCheckingAuth(false);
    };

    checkAuth();
  }, []);

  if (isCheckingAuth) {
    return (
      <Container className={containerStyles}>
        <div className="flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </Container>
    );
  }

  if (formType === 'checkemail') return <CheckEmail setFormType={setFormType} />;
  if (formType === 'magiclink') return <MagicEmailForm setFormType={setFormType} />;
  if (formType === 'recovery') return <RecoveryForm setFormType={setFormType} />;
  if (signInMethods.length === 1 && signInMethods[0] === 'anonymous')
    return <AnonymousSignInForm setFormType={setFormType} />;
  return <SignInForm setFormType={setFormType} />;
}

function SignInForm(props: { setFormType: CallableFunction }) {
  const [loading, setLoading] = useState<boolean>(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const [viewPassword, setViewPassword] = useState(false);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);

    const formData = new FormData(event.currentTarget);
    const email = formData.get('email') as string;
    const password = formData.get('password') as string;
    const authBaseUrl = `${process.env.NEXT_PUBLIC_API_URL || ''}/auth`;

    if (!email || !password) {
      toast({
        title: 'Error',
        description: 'Email and password are required.',
        variant: 'destructive',
      });
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${authBaseUrl}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'include',
      });

      if (!response.ok) {
        let errorBody = 'Login failed.';
        try {
          const body = await response.json();
          errorBody = body.detail || JSON.stringify(body);
        } catch (e) {
          /* Ignore */
        }
        throw new Error(errorBody);
      }

      const nextPath = searchParams.get('next') || '/projects';
      router.push(nextPath.startsWith('/') ? nextPath : `/${nextPath}`);
    } catch (error) {
      console.error('Login Error');
      setLoading(false);
      toast({
        title: '❌ Login Error',
        description:
          'Oops, something is preventing Agent YOU 🫵 from logging in, please try again or contact support',
        variant: 'destructive',
        duration: 8000,
      });
    }
  };

  return (
    <>
      <Container className={containerStyles}>
        <h1 className={headingStyle}>Welcome</h1>
        {signInMethods.includes('email') && (
          <form className="grid gap-2" onSubmit={handleLogin}>
            <Label className={cn(labelStyle, 'mt-5')} htmlFor="email">
              Username
            </Label>
            <Input
              name="email"
              disabled={loading}
              required
              id="email"
              placeholder="name@example.com"
              type="email"
              autoCapitalize="none"
              autoComplete="email"
              autoCorrect="off"
              className="h-12 pl-3"
              data-testid="login-form-input-email"
            />
            <Label className={cn(labelStyle, 'mt-4')} htmlFor="password">
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
                data-testid="login-form-input-password"
              />
              <div
                className="absolute right-3 top-1/2 mt-0.5 hidden -translate-y-1/2 transform cursor-pointer peer-valid:flex"
                onClick={() => setViewPassword((prev) => !prev)}
                data-testid="login-form-button-togglePasswordView"
              >
                {viewPassword ? <Eye size={20} /> : <ViewOffIcon size={20} />}
              </div>
            </div>
            <Button
              type="submit"
              className="mt-4 py-[22px]"
              disabled={loading}
              data-testid="login-form-button-submit"
            >
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Login
            </Button>
            <div className="mb-2 flex items-center gap-1 text-sm font-medium text-secondary dark:text-white">
              {`Can't remember your password?`}
              <Button
                variant="link"
                className="p-0 font-semibold text-black dark:text-white"
                onClick={() => props.setFormType('recovery')}
                onMouseDown={() => props.setFormType('recovery')}
                data-testid="login-form-link-resetPassword"
              >
                Reset now
              </Button>
            </div>
          </form>
        )}

        <ContinueWith setFormType={props.setFormType} />
        <span className="mb-1 mt-4 w-full border-t border-[#DEE0F4]" />

        {signInMethods.includes('email') && (
          <div className="mt-2 flex items-center gap-1 text-sm font-medium text-secondary dark:text-white">
            {"Don't have an account?"}
            <Button
              variant="link"
              className="p-0 font-semibold text-black dark:text-white"
              onClick={() => router.push('/signup')}
              data-testid="login-form-link-signUp"
            >
              Sign Up
            </Button>
          </div>
        )}
      </Container>
      <div className="mt-12 pr-3">
        <TOS />
      </div>
    </>
  );
}

function AnonymousSignInForm(_: { setFormType: CallableFunction }) {
  const [loading, setLoading] = useState<boolean>(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const authBaseUrl = `${process.env.NEXT_PUBLIC_API_URL || ''}/auth`;

  const handleAnonymousLogin = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${authBaseUrl}/anonymous`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) {
        let errorBody = 'Anonymous sign-in failed.';
        try {
          const body = await response.json();
          errorBody = body.detail || JSON.stringify(body);
        } catch (_e) {
          /* Ignore */
        }
        throw new Error(errorBody);
      }

      const nextPath = searchParams.get('next') || '/projects';
      router.push(nextPath.startsWith('/') ? nextPath : `/${nextPath}`);
    } catch (error: unknown) {
      setLoading(false);
      console.error('Anonymous Sign-In Error:', error);
      toast({
        title: '❌ Anonymous Sign-In Error',
        description: (error as Error).message || 'An unexpected error occurred.',
        variant: 'destructive',
        duration: 8000,
      });
    }
  };

  return (
    <>
      <Container className={containerStyles}>
        <h1 className={headingStyle}>Welcome to the Playground</h1>
        <p className="py-2 text-sm text-muted-foreground">
          NOTE: In the Playground, session data will be lost as soon as you log out.
        </p>
        <Button className="w-full py-[22px]" disabled={loading} onClick={handleAnonymousLogin}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          Get Started
        </Button>
      </Container>
      <div className="mt-12 pr-3">
        <TOS />
      </div>
    </>
  );
}

function RecoveryForm(props: { setFormType: CallableFunction }) {
  const [loading, setLoading] = useState<boolean>(false);
  const authBaseUrl = `${process.env.NEXT_PUBLIC_API_URL || ''}/auth`;

  const handleRecovery = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    const formData = new FormData(event.currentTarget);
    const email = formData.get('email') as string;

    if (!email) {
      toast({ title: 'Error', description: 'Email is required.', variant: 'destructive' });
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${authBaseUrl}/password_reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        let errorBody = 'Password reset request failed.';
        try {
          const body = await response.json();
          errorBody = body.detail || JSON.stringify(body);
        } catch (e) {
          /* Ignore */
        }
        throw new Error(errorBody);
      }

      toast({ title: 'Check Your Email', description: 'Password reset instructions sent.' });
      handleSignIn(props.setFormType);
    } catch (error: unknown) {
      console.error('Recovery Error');
      setLoading(false);
      toast({
        title: '❌ Recovery Error',
        description: (error as Error).message || 'An unexpected error occurred.',
        variant: 'destructive',
        duration: 8000,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Container className={containerStyles}>
        <div className="grid gap-6">
          <h1 className={headingStyle}>Account Recovery</h1>
          <form className="grid gap-2" onSubmit={handleRecovery}>
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
            <Button type="submit" className="mt-2" disabled={loading}>
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Send reset password instructions
            </Button>
          </form>
          <p className="text-sm text-muted-foreground">
            {'Remember your password? '}{' '}
            <Button variant="link" className="p-0" onClick={() => props.setFormType('signin')}>
              Go Back
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
