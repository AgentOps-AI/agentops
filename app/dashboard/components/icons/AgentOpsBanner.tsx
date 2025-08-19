'use client';
import Image from 'next/image';
import FoxySingle from '@/components/icons/FoxyAI/foxy_single.png';
import { useState } from 'react';

const AgentOpsBanner = ({ foxyUser = false }: { foxyUser?: boolean }) => {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      className="relative flex items-center"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ width: 140, height: 34 }}
    >
      <Image
        src="/logo-banner.svg"
        alt="AgentOps Logo"
        width={140}
        height={34}
        priority
        style={{ height: 'auto' }}
        className="dark:invert"
      />
      {foxyUser && (
        <Image
          src={FoxySingle}
          alt="FoxyAI"
          width={32}
          height={32}
          className={`duration-2000 absolute left-[-20px] top-1/2 -translate-y-1/2 rotate-45
            opacity-100 transition-all ease-in-out
            ${hovered ? 'translate-x-[1px]' : '-translate-x-10 opacity-0'}
            pointer-events-none
          `}
          style={{ zIndex: 2 }}
        />
      )}
    </div>
  );
};

export default AgentOpsBanner;
export { FoxySingle };
