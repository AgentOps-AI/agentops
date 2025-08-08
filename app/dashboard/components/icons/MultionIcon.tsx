import { cn } from '@/lib/utils';

const MultionIcon = ({ className = '', ...props }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 16 16"
    className={cn('fill-black dark:fill-white', className)}
    {...props}
  >
    <path d="M12 5.61v-.228C12 3.238 10.21 1.5 8 1.5c-2.209 0-4 1.738-4 3.882v5.71c3.53-2.513 4-6.615 4-6.615v-.005l4 1.138Z" />
    <path d="M12.94 7.455 8 4.529c.525 4.232 3.904 6.641 3.904 6.641h.002l-2.903 2.847.201.112a3.91 3.91 0 0 0 5.316-1.501c1.053-1.88.307-4.136-1.58-5.173Z" />
    <path d="m4.077 11.229-.98-3.671-.213.121C1.022 8.782.442 11.128 1.589 12.917c1.148 1.79 3.476 2.19 5.373 1.12L12 11.226c-4.016-1.568-7.923.002-7.923.002Z" />
  </svg>
);

export default MultionIcon;
