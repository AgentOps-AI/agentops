import { cn } from '@/lib/utils';

const XAIIcon = ({ className = '', ...props }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 466.04 516.93"
    className={cn(className)}
    {...props}
  >
    <polygon points="0.12 182.71 234.14 516.92 338.15 516.92 104.13 182.71 0.12 182.71" />
    <polygon points="0 516.92 104.08 516.92 156.08 442.67 104.04 368.34 0 516.92" />
    <polygon points="466.04 0 361.96 0 182.1 256.86 234.15 331.18 466.04 0" />
    <polygon points="380.78 516.92 466.04 516.92 466.04 37.16 380.78 158.92 380.78 516.92" />
  </svg>
);

export default XAIIcon;
