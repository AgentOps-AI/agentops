import { cn } from '@/lib/utils';

const XpanderIcon = ({ className = '', ...props }) => (
    <svg
        role="img"
        viewBox="0 0 38 38"
        xmlns="http://www.w3.org/2000/svg"
        className={cn('fill-current', className)}
        {...props}
    >
        <g mask="url(#mask0_4237_328)" fill="currentColor">
            <path d="M11.8661 18.9922H17.3887V24.5138L8.96337 31.0815H5.29939V27.4175L11.8661 18.9922Z" fill="currentColor" />
            <path d="M5.29939 6.91602H8.96337L17.3887 13.4837V19.0063H11.8661L5.29939 10.58V6.91602Z" fill="currentColor" />
            <path d="M26.1354 18.9961L32.7031 27.4214V31.0854H29.0391L20.6128 24.5177V18.9961H26.1354Z" fill="currentColor" />
            <path d="M26.1374 19.0044H20.6148V13.4818L29.0411 6.91406H32.7051V10.578L26.1374 19.0044Z" fill="currentColor" />
        </g>
    </svg >
);

export default XpanderIcon;
