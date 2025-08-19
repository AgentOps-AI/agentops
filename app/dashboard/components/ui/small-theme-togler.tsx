import { Sun01Icon as SunIcon } from 'hugeicons-react';
import { cn } from '@/lib/utils';
import React, { useEffect, useState } from 'react';
import { buttonVariants } from './button';
import { Moon02Icon as MoonIcon } from 'hugeicons-react';

export const SmallThemeTogler = ({
  withTitle,
  alignLeft,
}: {
  withTitle?: boolean;
  alignLeft?: boolean;
}) => {
  const [theme, setTheme] = useState('light');

  const toggleTheme = () => {
    const currentTheme = localStorage?.getItem('theme') || 'light';
    document.documentElement.classList.remove('dark', 'light');
    const updatedTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.classList.add(updatedTheme);
    setTheme(updatedTheme);
    localStorage.setItem('theme', updatedTheme);
  };

  useEffect(() => {
    setTheme(localStorage.getItem('theme') || 'light');
  }, []);

  // Determine the text to display based on current theme
  const themeToggleText = theme === 'light' ? 'Dark Mode' : 'Light Mode';

  return (
    <>
      <div
        className={cn(
          buttonVariants({
            variant: 'ghost',
            size: 'sm',
          }),
          'justify-start overflow-hidden rounded-lg border-4 border-transparent px-1.5 dark:border-none dark:px-2.5',
          'flex cursor-pointer items-center hover:bg-[#E4E6F4] dark:hover:bg-slate-800',
          alignLeft ? 'justify-start' : withTitle ? 'justify-start' : 'justify-center',
          withTitle && 'w-full',
          'dark:text-white',
        )}
        onClick={toggleTheme}
      >
        <div className="flex items-center">
          {theme === 'light' ? <MoonIcon className="h-4 w-4" /> : <SunIcon className="h-4 w-4" />}
          {withTitle && (
            <span className="ml-3 whitespace-nowrap dark:text-white">{themeToggleText}</span>
          )}
        </div>
      </div>
    </>
  );
};
