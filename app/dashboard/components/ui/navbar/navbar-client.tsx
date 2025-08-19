'use client';

import * as Sentry from '@sentry/nextjs';
import {
  Bug01Icon as BugIcon,
  Doc01Icon as DocsIcon,
  TableIcon as DrilldownIcon,
  Comment01Icon as FeedbackIcon,
  FileSearchIcon,
  DashboardBrowsingIcon as OverviewIcon,
  DashboardSquare01Icon as ProjectsIcon,
  PackageMovingIcon as DeployIcon,
  FileAddIcon,
} from 'hugeicons-react';
import MCPLogo from '@/components/icons/MCPLogo';
import { usePathname } from 'next/navigation';
import { memo, useMemo } from 'react';
import { ILink } from './components/navlinks';
import { SideNavbar } from './components/side-navbar';
import { TopNavbar } from './components/top-navbar';
import { usePatchNotes } from '@/app/providers/patch-notes-provider';

export type NavItemVariant = 'default' | 'ghost';

const getIconStyles = (variant: NavItemVariant) => {
  return `h-4 w-4 flex-shrink-0 ${variant === 'default' ? 'stroke-white' : 'stroke-primary'}`;
};

interface NavLinkConfig {
  title: string;
  href: string;
  IconComponent: React.FC<any>;
  onclick?: CallableFunction;
  disabled?: boolean;
  badge?: string;
}

const staticHelpLinks: Omit<ILink, 'icon' | 'variant'>[] = [
  {
    title: 'Patch Notes',
    href: '#',
    onclick: undefined, // Will be set in the component
  },
  {
    title: 'Docs',
    href: '#',
    onclick: () => window.open('https://docs.agentops.ai', '_blank'),
  },
  {
    title: 'Chat with Docs',
    href: '#',
    onclick: () => window.open('https://entelligence.ai/AgentOps-AI&agentops', '_blank'),
  },
];

const dataLinksConfig: NavLinkConfig[] = [
  { title: 'Projects', href: '/projects', IconComponent: ProjectsIcon },
  { title: 'Traces', href: '/traces', IconComponent: DrilldownIcon },
  { title: 'Metrics', href: '/overview', IconComponent: OverviewIcon },
  // { title: 'Logs', href: '/logs', IconComponent: LogsIcon },
  {
    title: 'MCP',
    href: '/mcp',
    IconComponent: MCPLogo,
  },
  {
    title: 'Deploy',
    href: '/deploy',
    IconComponent: DeployIcon,
    badge: 'Alpha'
  },
  // {
  //   title: 'Evals (Enterprise)',
  //   href: '#',
  //   IconComponent: EvalsIcon,
  //   disabled: true,
  // },
];

function NavbarClientComponent(props: { mobile: boolean }) {
  const pathname = usePathname();
  const { openPatchNotes } = usePatchNotes();

  const feedback = useMemo(() => {
    if (typeof window !== 'undefined') {
      return Sentry.getFeedback();
    }
    return null;
  }, []);

  const dataLinks: ILink[] = useMemo(() => {
    return dataLinksConfig.map((config) => {
      const isActive = pathname?.startsWith(config.href);
      const variant = isActive ? 'default' : 'ghost';
      return {
        title: config.title,
        href: config.href,
        icon: <config.IconComponent className={getIconStyles(variant)} />,
        variant,
        onclick: config.onclick,
        disabled: config.disabled,
        badge: config.badge,
      };
    });
  }, [pathname]);

  const helpLinks = useMemo(() => {
    const helpLinksWithIcons: ILink[] = [];

    // First add Patch Notes
    helpLinksWithIcons.push({
      title: 'Patch Notes',
      href: '#',
      icon: <FileAddIcon className={getIconStyles('ghost')} />,
      variant: 'ghost' as const,
      onclick: openPatchNotes,
    });

    // Then add Support
    helpLinksWithIcons.push({
      title: 'Support',
      href: '#',
      onclick: () => {
        if (feedback) {
          feedback.createForm().then((form) => {
            form.appendToDom();
            form.open();
          });
        }
      },
      icon: <BugIcon className={getIconStyles('ghost')} />,
      variant: 'ghost' as const,
    });

    // Then add the rest of staticHelpLinks (Docs and Chat with Docs)
    const remainingLinks = staticHelpLinks
      .filter((link) => link.title !== 'Patch Notes')
      .map((link) => ({
        ...link,
        icon:
          link.title === 'Docs' ? (
            <DocsIcon className={getIconStyles('ghost')} />
          ) : link.title === 'Chat with Docs' ? (
            <FileSearchIcon className={getIconStyles('ghost')} />
          ) : (
            <FeedbackIcon className={getIconStyles('ghost')} />
          ),
        variant: 'ghost' as const,
        onclick: link.onclick,
      }));

    helpLinksWithIcons.push(...remainingLinks);

    return helpLinksWithIcons;
  }, [feedback, openPatchNotes]);

  return props.mobile ? (
    <TopNavbar helpLinks={helpLinks} dataLinks={dataLinks} />
  ) : (
    <SideNavbar helpLinks={helpLinks} dataLinks={dataLinks} />
  );
}

export const NavbarClient = memo(NavbarClientComponent);
