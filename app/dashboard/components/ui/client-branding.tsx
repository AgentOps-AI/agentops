import FoxySingle from '@/components/icons/FoxyAI/foxy_single.png';
import Logo from '@/components/icons/Logo';
import Image from 'next/image';
import type { StaticImageData } from 'next/image';

export interface ClientBranding {
  logo: StaticImageData;
  name: string;
  color: string;
  versionRow: JSX.Element;
  tooltip: JSX.Element;
}

// this can be further extended to include more clients
// and be more dry for future things.
const CLIENT_BRANDING: Record<string, ClientBranding> = {
  'foxyai.com': {
    logo: FoxySingle,
    name: 'FoxyAI',
    color: 'text-orange-500',
    versionRow: (
      <>
        <Logo className="h-5 w-5" style={{ color: 'rgba(20, 27, 52, 1)' }} />
        <span>❤️</span>
        <Image
          src={FoxySingle}
          alt="FoxyAI"
          width={20}
          height={20}
          className="h-5 w-5 object-contain"
        />
      </>
    ),
    tooltip: (
      <span className="flex items-center gap-1">
        <Logo className="h-5 w-5" style={{ color: 'rgba(20, 27, 52, 1)' }} />
        <span>❤️</span>
        <Image
          src={FoxySingle}
          alt="FoxyAI"
          width={16}
          height={16}
          className="inline-block object-contain align-middle"
        />
      </span>
    ),
  },
  'adubatl@gmail.com': {
    logo: FoxySingle,
    name: 'FoxyAI',
    color: 'text-orange-500',
    versionRow: (
      <>
        <Logo className="h-5 w-5" style={{ color: 'rgba(20, 27, 52, 1)' }} />
        <span>❤️</span>
        <Image
          src={FoxySingle}
          alt="FoxyAI"
          width={20}
          height={20}
          className="h-5 w-5 object-contain"
        />
      </>
    ),
    tooltip: (
      <span className="flex items-center gap-1">
        <Logo className="h-5 w-5" style={{ color: 'rgba(20, 27, 52, 1)' }} />
        <span>❤️</span>
        <Image
          src={FoxySingle}
          alt="FoxyAI"
          width={16}
          height={16}
          className="inline-block object-contain align-middle"
        />
      </span>
    ),
  },
};

/**
 * Get the client branding for a given email
 * fallback to domain if email is not found
 *
 * No impact for non-foxy users, in the future we can add more clients
 * think: Enterprise subscription, etc.
 * @param email - The email of the user
 * @returns The client branding for the user
 */
export function getClientBranding(email: string | undefined): ClientBranding | null {
  if (!email) return null;

  // Check full email first (case-sensitive for specific emails like adubatl@gmail.com)
  if (CLIENT_BRANDING[email as keyof typeof CLIENT_BRANDING])
    return CLIENT_BRANDING[email as keyof typeof CLIENT_BRANDING];

  // Extract domain and check case-insensitively
  const domain = email.split('@')[1]?.toLowerCase();
  if (domain && CLIENT_BRANDING[domain as keyof typeof CLIENT_BRANDING])
    return CLIENT_BRANDING[domain as keyof typeof CLIENT_BRANDING];

  return null;
}
