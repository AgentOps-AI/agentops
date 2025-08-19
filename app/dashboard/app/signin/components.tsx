'use client';

import GoogleIcon from '@/components/icons/GoogleIcon';

import { Button } from '@/components/ui/button';
import { Container } from '@/components/ui/container';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import TextSeparator from '@/components/ui/text-separator';
import { containerStyles, headingStyle, labelStyle } from '@/constants/styles';
import { signInMethods } from '@/lib/signin';
import { cn } from '@/lib/utils';
import { GithubIcon as Github, Loading03Icon as Loader } from 'hugeicons-react';

import { MagicWand01Icon as WandSparkles } from 'hugeicons-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import posthog from 'posthog-js';
import { useState, useEffect } from 'react';
import { toast } from '@/components/ui/use-toast';

export type LastUsedType = 'google' | 'github' | 'magiclink';

const handleSetLastUsed = (type: LastUsedType, isSignUp: boolean) => {
  if (isSignUp || typeof window === 'undefined') {
    return;
  }
  localStorage.setItem('lastUsed', type);
};

export function TOS() {
  return (
    <p className="text-center text-sm font-medium text-secondary dark:text-white">
      By creating an account, you acknowledge and agree to our{' '}
      <Link
        href="https://docs.google.com/document/d/1C-2VCAEiNxOCaOIEn60MAbtKo7bq654f_r1MdDtlX-s/edit?usp=sharing"
        target="_blank"
        rel="noopener noreferrer"
        className="text-black underline underline-offset-2 dark:text-white"
      >
        Terms of Service
      </Link>{' '}
      and{' '}
      <Link
        href="/privacy-policy"
        className="text-black underline underline-offset-2 dark:text-white"
      >
        Privacy Policy
      </Link>
      .
    </p>
  );
}

const LastUsedText = ({ type, isSignUp }: { type: LastUsedType; isSignUp: boolean }) => {
  const [lastUsed, setLastUsed] = useState<LastUsedType | null>(null);

  useEffect(() => {
    setLastUsed(localStorage.getItem('lastUsed') as LastUsedType);
  }, []);

  if (isSignUp || !lastUsed || lastUsed !== type) {
    return null;
  }

  return (
    <span className="relative -mt-[1px] ml-2 inline-flex items-center rounded-md bg-blue-400 p-1 text-xs font-normal text-white sm:absolute">
      Last used
    </span>
  );
};

const signInPageButtonStyles =
  'rounded-lg border border-[#DEE0F4] bg-transparent py-6 font-semibold text-[#1E293B] dark:text-white text-base';

const continueWithOptions = ['google', 'github', 'magic', 'anonymous'];

function SignInIntro() {
  if (continueWithOptions.some((item) => signInMethods.includes(item))) {
    if (signInMethods.includes('email'))
      return <TextSeparator className="mb-3 mt-3" text="Or, with one of the below" />;
    else return <div className="mt-2"></div>;
  }
}

export function ContinueWith(props: { setFormType: CallableFunction; isSignUp?: boolean }) {
  const { setFormType, isSignUp = false } = props;
  const router = useRouter();
  const [isLoading, setIsLoading] = useState<'google' | 'github' | 'anonymous' | null>(null);

  const authBaseUrl = `${process.env.NEXT_PUBLIC_API_URL || ''}/auth`;

  const handleOAuthSignIn = async (provider: 'google' | 'github') => {
    if (!process.env.NEXT_PUBLIC_API_URL) {
      console.error('NEXT_PUBLIC_API_URL is not set');
      toast({
        title: 'Configuration Error',
        description: 'Unable to initiate sign-in.',
        variant: 'destructive',
      });
      return;
    }
    setIsLoading(provider);
    try {
      const response = await fetch(`${authBaseUrl}/oauth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      });

      if (!response.ok) {
        let errorBody = `OAuth initiation failed: ${response.status}`;
        try {
          const body = await response.json();
          errorBody = body.detail || JSON.stringify(body);
        } catch (e) {
          /* ignore */
        }
        throw new Error(errorBody);
      }

      const responseData = await response.json();

      if (responseData.url) {
        window.location.href = responseData.url;
      } else {
        throw new Error('Backend did not return a valid redirect URL.');
      }
    } catch (error: any) {
      console.error(`${provider} Sign-In Initiation Error:`, error);
      toast({ title: 'Sign-In Error', description: error.message, variant: 'destructive' });
      setIsLoading(null);
    }
  };

  const handleAnonymousSignIn = async () => {
    if (!process.env.NEXT_PUBLIC_API_URL) {
      console.error('NEXT_PUBLIC_API_URL is not set');
      toast({
        title: 'Configuration Error',
        description: 'Unable to initiate sign-in.',
        variant: 'destructive',
      });
      return;
    }
    setIsLoading('anonymous');
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
        } catch (e) {
          /* Ignore */
        }
        throw new Error(errorBody);
      }

      router.push('/');
    } catch (error: any) {
      console.error('Anonymous Sign-In Error:', error);
      toast({
        title: '❌ Anonymous Sign-In Error',
        description: error.message || 'An unexpected error occurred.',
        variant: 'destructive',
        duration: 8000,
      });
      setIsLoading(null);
    }
  };

  return (
    <>
      <SignInIntro />
      <div className="flex flex-col gap-2">
        {signInMethods.includes('google') && (
          <Button
            variant="outline"
            type="button"
            disabled={!!isLoading}
            className={signInPageButtonStyles}
            onClick={() => handleOAuthSignIn('google')}
          >
            {isLoading === 'google' ? (
              <Loader className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <GoogleIcon className="mr-4" />
            )}
            <span>
              {isSignUp ? 'Sign up with Google' : 'Sign in with Google'}
              <LastUsedText type="google" isSignUp={isSignUp} />
            </span>
          </Button>
        )}
        {signInMethods.includes('github') && (
          <Button
            variant="outline"
            type="button"
            disabled={!!isLoading}
            className={signInPageButtonStyles}
            onClick={() => handleOAuthSignIn('github')}
          >
            {isLoading === 'github' ? (
              <Loader className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Github className="mr-4" />
            )}
            <span>
              {isSignUp ? 'Sign up with GitHub' : 'Sign in with GitHub'}
              <LastUsedText type="github" isSignUp={isSignUp} />
            </span>
          </Button>
        )}
        {signInMethods.includes('magic') && (
          <Button
            variant="outline"
            type="button"
            disabled={!!isLoading}
            className={signInPageButtonStyles}
            onClick={() => setFormType('magiclink')}
          >
            <WandSparkles className="mr-4" />
            <span>
              {isSignUp ? 'Sign up with Magic' : 'Sign in with Magic'}
              <LastUsedText type="magiclink" isSignUp={isSignUp} />
            </span>
          </Button>
        )}
        {signInMethods.includes('anonymous') && (
          <Button
            variant="outline"
            type="button"
            disabled={!!isLoading}
            className={signInPageButtonStyles}
            onClick={handleAnonymousSignIn}
          >
            {isLoading === 'anonymous' ? <Loader className="mr-2 h-4 w-4 animate-spin" /> : null}
            Sign in Anonymously
          </Button>
        )}
      </div>
    </>
  );
}

export function CheckEmail(props: { setFormType: CallableFunction; isSignUp?: boolean }) {
  const { setFormType, isSignUp = false } = props;

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Email Sent!</h1>
        <p className="text-sm text-muted-foreground">Check your email for the confirmation link</p>
      </div>

      <p className="text-sm text-muted-foreground">
        {'Want to use another authentication method? '}
        <Button
          variant="link"
          className="p-0"
          onClick={() => setFormType(isSignUp ? 'signup' : 'signin')}
          onMouseDown={() => setFormType(isSignUp ? 'signup' : 'signin')}
        >
          Go Back
        </Button>
      </p>
    </div>
  );
}

export function MagicEmailForm(props: { setFormType: CallableFunction; isSignUp?: boolean }) {
  const { setFormType, isSignUp = false } = props;
  const [loading, setLoading] = useState<boolean>(false);

  const authBaseUrl = `${process.env.NEXT_PUBLIC_API_URL || ''}/auth`;

  return (
    <>
      <Container className={containerStyles}>
        <div className="grid gap-6">
          <h1 className={headingStyle}>{isSignUp ? 'Create Account' : 'Welcome Back'}</h1>
          <form className="grid gap-2">
            <Label className={cn(labelStyle)} htmlFor="email">
              Email
            </Label>
            <Input
              name="email"
              disabled={loading}
              id="email"
              placeholder="name@example.com"
              type="email"
              autoCapitalize="none"
              autoComplete="email"
              autoCorrect="off"
              required
              className="h-12"
            />
            <Button
              className="mt-2"
              disabled={loading}
              onClick={async (event) => {
                event.preventDefault();
                const form = (event.target as HTMLButtonElement).form;
                if (!form) return;
                const formData = new FormData(form);
                const email = formData.get('email') as string;

                if (!email || !process.env.NEXT_PUBLIC_API_URL) {
                  toast({
                    title: 'Error',
                    description: 'Please enter a valid email.',
                    variant: 'destructive',
                  });
                  if (!process.env.NEXT_PUBLIC_API_URL)
                    console.error('NEXT_PUBLIC_API_URL is not set');
                  return;
                }

                setLoading(true);
                try {
                  const response = await fetch(`${authBaseUrl}/otp`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email }),
                  });

                  if (!response.ok) {
                    let errorBody = 'Failed to send magic link.';
                    try {
                      const body = await response.json();
                      errorBody = body.detail || JSON.stringify(body);
                    } catch (e) {
                      /* Ignore */
                    }
                    throw new Error(errorBody);
                  }

                  handleSetLastUsed('magiclink', isSignUp);
                  handleSignIn(setFormType);
                } catch (error: any) {
                  console.error('Magic Link API Error:', error);
                  setLoading(false);
                  toast({
                    title: '❌ Magic Link Error',
                    description: error.message || 'Failed to send magic link.',
                    variant: 'destructive',
                    duration: 8000,
                  });
                }
              }}
            >
              {loading ? (
                <Loader className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <WandSparkles className="mr-2 h-4 w-4 dark:invert" />
              )}
              Send Magic Link
            </Button>
          </form>
          <p className="flex flex-col items-center text-sm text-muted-foreground">
            {'Want to use another authentication method? '}{' '}
            <Button
              variant="link"
              className="p-0"
              onClick={() => setFormType(isSignUp ? 'signup' : 'signin')}
              onMouseDown={() => setFormType(isSignUp ? 'signup' : 'signin')}
            >
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

export function handleSignIn(setFormType?: CallableFunction) {
  if (setFormType) setFormType('checkemail');
}
