'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { ViewIcon as Eye, ViewOffIcon as EyeOff } from 'hugeicons-react';

export function ApiKeyBox(props: { apiKey: string }) {
  const [show, setShow] = useState<boolean>(false);
  return (
    <>
      <Input
        className="h-8 w-full px-0 py-0 text-center font-mono text-xs md:w-[320px] md:text-sm"
        data-testid="apikey-box-input"
        value={show ? props.apiKey : `${'•'.repeat(28)}${props.apiKey.slice(-8)}`}
        type="text"
        readOnly
      />
      {show ? (
        <div className="flex w-5 items-center">
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <EyeOff
                data-testid="apikey-box-button-toggle-visibility"
                className="w-5 cursor-pointer"
                onClick={() => setShow((prev) => !prev)}
              />
            </TooltipTrigger>
            <TooltipContent>Hide API Key</TooltipContent>
          </Tooltip>
        </div>
      ) : (
        <div className="flex w-5 items-center">
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <Eye
                data-testid="apikey-box-button-toggle-visibility"
                className="w-5 cursor-pointer"
                onClick={() => setShow((prev) => !prev)}
              />
            </TooltipTrigger>
            <TooltipContent>Show API Key</TooltipContent>
          </Tooltip>
        </div>
      )}
    </>
  );
}
