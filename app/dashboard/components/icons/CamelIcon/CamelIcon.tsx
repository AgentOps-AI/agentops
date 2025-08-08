import Image from 'next/image';
import { IconProps } from '@/components/icons/types';
import camelIcon from './CamelIcon.png';

export default function CamelIcon({ className, ...props }: IconProps) {
  return (
    <div className={className} {...props}>
      <Image src={camelIcon} alt="Camel Icon" width={24} height={24} className="object-contain" />
    </div>
  );
}
