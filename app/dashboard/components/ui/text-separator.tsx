import { cn } from '@/lib/utils';

export default function TextSeparator({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cn('relative', className)}>
      <div className="absolute inset-0 flex items-center">
        <span className="w-full border-t border-[#DEE0F4]" />
      </div>
      <div className="relative flex justify-center">
        <span className="relative bg-[#F7F8FF] px-2 text-sm font-semibold text-primary-foreground dark:bg-background dark:text-white">
          {text}
          <span
            style={{
              opacity: 0.28,
              background: 'url(image/grainy.png)',
            }}
            className="absolute bottom-0 left-0 right-0 top-0 z-0 dark:hidden"
          />
        </span>
      </div>
    </div>
  );
}
