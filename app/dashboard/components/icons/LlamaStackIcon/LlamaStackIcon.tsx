import Image from 'next/image';
import { IconProps } from '@/components/icons/types';
import llamastackIcon from './llamastack.webp';

export default function LlamaStackIcon({ className }: IconProps) {
  return (
    <div className={className}>
      <Image
        src={llamastackIcon}
        alt="LlamaStack Icon"
        width={24}
        height={24}
        className="object-contain dark:invert"
      />
    </div>
  );
}
