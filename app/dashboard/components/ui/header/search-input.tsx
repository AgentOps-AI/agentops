'use client';
import { Search01Icon as SearchIcon } from 'hugeicons-react';
import { Input } from '@/components/ui/input';
import { DivideSignIcon as Slash } from 'hugeicons-react';
import { ChangeEvent, useEffect, useRef, useState } from 'react';

export const SearchInput = () => {
  const [value, setValue] = useState<string>();
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  };

  useEffect(() => {
    const handleShortcut = (e: KeyboardEvent) => {
      if (e.key === '/') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    document.addEventListener('keydown', handleShortcut);

    return () => {
      document.removeEventListener('keydown', handleShortcut);
    };
  }, []);

  return (
    <div className="relative w-[273px]">
      <SearchIcon className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 transform text-muted-foreground" />
      <Input
        ref={inputRef}
        className="peer w-full max-w-[516px] pl-9"
        onChange={handleChange}
        value={value}
      />
      {!value && (
        <div className="absolute right-3 top-1/2 flex h-6 w-6 -translate-y-1/2 transform items-center justify-center rounded-md border-4 border-[#F7F8FF] bg-[#F7F8FF] peer-hover:hidden peer-focus:hidden dark:border-slate-800 dark:bg-slate-800">
          <Slash className="h-2.5 w-3" />
        </div>
      )}
    </div>
  );
};
