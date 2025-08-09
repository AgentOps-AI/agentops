import Image from 'next/image';
import { IconProps } from '@/components/icons/types';
import llamafsIcon from './llamafs.png';


export default function LlamaFSIcon({ className }: IconProps) {
  return (
    <div className={className}>
      <Image
        src={llamafsIcon}
        alt="LlamaFS Icon"
        width={24}
        height={24}
        className="object-contain dark:invert"
      />
    </div>
  );
} 