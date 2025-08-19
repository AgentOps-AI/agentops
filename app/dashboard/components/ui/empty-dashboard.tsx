import { cn } from '@/lib/utils';
import { DashboardSquare01Icon as EmptyDashboardIcon } from 'hugeicons-react';
import Image from 'next/image';

export default function EmptyDashboard({
  showIcon,
  className,
  subTitle = 'Try adjusting your filter.',
  horizontal,
}: {
  showIcon: boolean;
  className?: string;
  subTitle?: string;
  horizontal?: boolean;
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center', className)}>
      {showIcon && (
        <div className="mb-3 flex justify-center">
          <EmptyDashboardIcon />
        </div>
      )}
      <div
        className={cn('flex flex-col items-center justify-center gap-10', {
          'sm:flex-row': !!horizontal,
        })}
      >
        <Image
          src="/image/dots.png"
          alt="dots"
          height={48}
          width={100}
          style={{ height: 'auto' }}
        />
        <div>
          <div className="text-center font-medium text-primary">No results found</div>
          <div className="text-center font-medium text-secondary dark:text-white">{subTitle}</div>
        </div>
        <Image
          src="/image/dots.png"
          alt="dots"
          height={48}
          width={100}
          className="scale-x-[-1] transform"
          style={{ height: 'auto' }}
        />
      </div>
    </div>
  );
}
