'use client';

import Link from 'next/link';
import Logo from '@/components/icons/Logo';
import { GithubIcon as Github } from 'hugeicons-react';
import { usePatchNotes } from '@/app/providers/patch-notes-provider';

export default function Footer() {
  const { openPatchNotes } = usePatchNotes();

  return (
    <footer className="px-8 py-6 md:py-0">
      <div className="grid grid-cols-1 gap-8 border-b py-8 transition-colors duration-150 lg:grid-cols-12">
        <div className="col-span-1 lg:col-span-2">
          <Link href="/" className="flex flex-initial items-center font-bold md:mr-24">
            <span className="mr-2">
              <Logo />
            </span>
            <span>AgentOps</span>
          </Link>
        </div>
        <div className="col-span-1 lg:col-span-2">
          <ul className="flex flex-initial flex-col md:flex-1">
            <li className="py-3 md:py-0 md:pb-4">
              <p className="font-bold transition duration-150 ease-in-out">Contact Us</p>
            </li>
            <li className="py-3 md:py-0 md:pb-4">
              <Link href="mailto:alex@agentops.ai" className="transition duration-150 ease-in-out">
                Email
              </Link>
            </li>
            <li className="py-3 md:py-0 md:pb-4">
              <button
                onClick={openPatchNotes}
                className="transition duration-150 ease-in-out hover:opacity-80"
              >
                Patch Notes
              </button>
            </li>
          </ul>
        </div>
        <div className="col-span-1 lg:col-span-2">
          <ul className="flex flex-initial flex-col md:flex-1">
            <li className="py-3 md:py-0 md:pb-4">
              <p className="font-bold transition duration-150 ease-in-out">LEGAL</p>
            </li>
            <li className="py-3 md:py-0 md:pb-4">
              <Link href="/privacy-policy" className="transition duration-150 ease-in-out">
                Privacy Policy
              </Link>
            </li>
            <li className="py-3 md:py-0 md:pb-4">
              <Link
                href="/tos.pdf"
                prefetch={false}
                className="transition duration-150 ease-in-out"
              >
                Terms of Use
              </Link>
            </li>
          </ul>
        </div>
        <div className="col-span-1 flex items-start lg:col-span-6 lg:justify-end">
          <div className="flex h-10 items-center space-x-6">
            <a aria-label="Github" href="https://github.com/AgentOps-AI">
              <Github />
            </a>
          </div>
        </div>
      </div>
      <div className="flex flex-col items-center justify-between space-y-4 py-8 md:flex-row">
        <div>
          <span>&copy; {new Date().getFullYear()} Staf Inc. All rights reserved.</span>
        </div>
      </div>
    </footer>
  );
}
