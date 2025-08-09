import { ReactNode } from 'react';
import { YoutubeIcon as Youtube, Link01Icon as ExternalLink } from 'hugeicons-react';

interface ResourceBoxProps {
  title: string;
  youtubeLink: string;
  docsLink: string;
  icon: ReactNode;
}

export function ResourceBox({ title, youtubeLink, docsLink, icon }: ResourceBoxProps) {
  return (
    <div className="flex items-center gap-4 rounded-xl border-2 border-gray-100 p-4 dark:border-gray-800">
      <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-purple-100 dark:bg-purple-900/30">
        <div className="flex h-6 w-6 items-center justify-center">{icon}</div>
      </div>
      <div className="flex-1">
        <h3 className="mb-2 text-lg font-semibold">{title}</h3>
        <div className="flex gap-4">
          <a
            href={youtubeLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-sm text-gray-500 transition-colors hover:text-black dark:text-gray-400 dark:hover:text-white"
          >
            <Youtube className="h-4 w-4" />
            Tutorial
          </a>
          <a
            href={docsLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-sm text-gray-500 transition-colors hover:text-black dark:text-gray-400 dark:hover:text-white"
          >
            <ExternalLink className="h-4 w-4" />
            Docs
          </a>
        </div>
      </div>
    </div>
  );
}
