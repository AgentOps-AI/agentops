import { cn } from '@/lib/utils';
import React from 'react';

export const BackgroundCircuit = ({
  className,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  animate = true,
  ...props
}: {
  className?: string;
  animate?: boolean;
}) => {
  // TODO: Implement animation variants
  // const variants = {
  //   initial: {
  //     backgroundPosition: "0 50%",
  //   },
  //   animate: {
  //     backgroundPosition: ["0, 50%", "100% 50%", "0 50%"],
  //   },
  // };
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="1395"
      height="975"
      xmlnsXlink="http://www.w3.org/1999/xlink"
      className={cn('h-full w-full object-cover', className)}
      viewBox="0 0 1395 975"
      {...props}
    >
      <defs>
        <radialGradient
          id="radial-gradient"
          cx="-260.15"
          cy="1025.6"
          fx="-260.15"
          fy="1025.6"
          r="1"
          gradientTransform="translate(43755.51 35943.63) rotate(-10.84) scale(133.81 -41.8)"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#7a4dee" />
          <stop offset="1" stopColor="#7a4dee" stopOpacity="0" />
        </radialGradient>
        <radialGradient
          id="radial-gradient-2"
          cx="-262.4"
          cy="1031.44"
          fx="-262.4"
          fy="1031.44"
          r="1"
          gradientTransform="translate(-92771.59 10600.66) rotate(119.45) scale(209.94 -73.79)"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#7a4dee" />
          <stop offset="1" stopColor="#7a4dee" stopOpacity="0" />
        </radialGradient>
        <radialGradient
          id="radial-gradient-3"
          cx="-260.6"
          cy="1023.21"
          fx="-260.6"
          fy="1023.21"
          r="1"
          gradientTransform="translate(54019.06 14755.12) rotate(-39.81) scale(120.12 -43.32)"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#7a4dee" />
          <stop offset="1" stopColor="#7a4dee" stopOpacity="0" />
        </radialGradient>
        <radialGradient
          id="radial-gradient-4"
          cx="-264.23"
          cy="1023.07"
          fx="-264.23"
          fy="1023.07"
          r="1"
          gradientTransform="translate(16097.25 -40313.26) rotate(-126.69) scale(88.92 -36.33)"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#7a4dee" />
          <stop offset="1" stopColor="#7a4dee" stopOpacity="0" />
        </radialGradient>
        <radialGradient
          id="radial-gradient-5"
          cx="-259.98"
          cy="1025.99"
          fx="-259.98"
          fy="1025.99"
          r="1"
          gradientTransform="translate(43823.73 47418.04) rotate(-12.35) scale(120.94 -53.08)"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#7a4dee" />
          <stop offset="1" stopColor="#7a4dee" stopOpacity="0" />
        </radialGradient>
        <radialGradient
          id="radial-gradient-6"
          cx="-264.17"
          cy="1030.1"
          fx="-264.17"
          fy="1030.1"
          r="1"
          gradientTransform="translate(-39192.21 -43163.42) rotate(168.26) scale(113.31 -49.73)"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#7a4dee" />
          <stop offset="1" stopColor="#7a4dee" stopOpacity="0" />
        </radialGradient>
      </defs>
      <g /*isolation="isolate"*/>
        <g id="Layer_1">
          <g>
            <path
              d="M982.77,807.97h147.38c7.69,0,15.07-3.05,20.5-8.49l122.13-122.12c5.44-5.44,12.81-8.49,20.5-8.49h75.74c16.01,0,29-12.98,29-29v-137.25c0-7.69,3.05-15.07,8.49-20.51l147.29-147.29c5.44-5.44,12.82-8.49,20.51-8.49h159.83c7.69,0,15.06-3.06,20.5-8.49l235.83-235.83"
              fill="none"
              stroke="#d5d7e9"
            />
            <path
              d="M982.77,807.97h147.38c7.69,0,15.07-3.05,20.5-8.49l122.13-122.12c5.44-5.44,12.81-8.49,20.5-8.49h75.74c16.01,0,29-12.98,29-29v-137.25c0-7.69,3.05-15.07,8.49-20.51l147.29-147.29c5.44-5.44,12.82-8.49,20.51-8.49h159.83c7.69,0,15.06-3.06,20.5-8.49l235.83-235.83"
              fill="none"
              stroke="url(#radial-gradient)"
              strokeWidth="2"
            />
            <path
              d="M1153.98,441.97h-147.38c-7.69,0-15.06-3.05-20.5-8.49l-122.12-122.12c-5.44-5.44-12.82-8.49-20.51-8.49h-75.73c-16.02,0-29-12.98-29-29v-137.25c0-7.69-3.06-15.07-8.49-20.51L582.95-31.18c-5.44-5.44-12.82-8.49-20.51-8.49h-159.83c-7.69,0-15.07-3.06-20.51-8.49l-235.83-235.83"
              fill="none"
              stroke="#d5d7e9"
            />
            <path
              d="M1153.98,441.97h-147.38c-7.69,0-15.06-3.05-20.5-8.49l-122.12-122.12c-5.44-5.44-12.82-8.49-20.51-8.49h-75.73c-16.02,0-29-12.98-29-29v-137.25c0-7.69-3.06-15.07-8.49-20.51L582.95-31.18c-5.44-5.44-12.82-8.49-20.51-8.49h-159.83c-7.69,0-15.07-3.06-20.51-8.49l-235.83-235.83"
              fill="none"
              stroke="url(#radial-gradient-2)"
              strokeWidth="2"
            />
            <path
              d="M981.38,807.97h278.79c7.69,0,15.07-3.05,20.51-8.49l34.74-34.74c5.44-5.44,12.82-8.49,20.51-8.49h269.58c7.69,0,15.07-3.05,20.5-8.49l413.74-413.74"
              fill="none"
              stroke="#d5d7e9"
            />
            <path
              d="M981.38,807.97h278.79c7.69,0,15.07-3.05,20.51-8.49l34.74-34.74c5.44-5.44,12.82-8.49,20.51-8.49h269.58c7.69,0,15.07-3.05,20.5-8.49l413.74-413.74"
              fill="none"
              stroke="url(#radial-gradient-3)"
              strokeWidth="2"
            />
            <path
              d="M981.38,807.97h-278.8c-7.69,0-15.07-3.05-20.51-8.49l-34.74-34.74c-5.44-5.44-12.82-8.49-20.51-8.49h-269.58c-7.69,0-15.07-3.05-20.51-8.49L-77,334.01"
              fill="none"
              stroke="#d5d7e9"
            />
            <path
              d="M981.38,807.97h-278.8c-7.69,0-15.07-3.05-20.51-8.49l-34.74-34.74c-5.44-5.44-12.82-8.49-20.51-8.49h-269.58c-7.69,0-15.07-3.05-20.51-8.49L-77,334.01"
              fill="none"
              stroke="url(#radial-gradient-4)"
              strokeWidth="2"
            />
            <path
              d="M984.17,807.97h208.89c7.69,0,15.07,3.06,20.51,8.49l24.26,24.26c5.43,5.44,12.81,8.49,20.5,8.49h94.12c7.69,0,15.07,3.05,20.5,8.49l107.8,107.79c5.44,5.44,12.81,8.49,20.51,8.49h276.22c7.69,0,15.06-3.05,20.5-8.49l60.44-60.43c5.43-5.44,12.81-8.49,20.5-8.49h156.64"
              fill="none"
              stroke="#d5d7e9"
            />
            <path
              d="M984.17,807.97h208.89c7.69,0,15.07,3.06,20.51,8.49l24.26,24.26c5.43,5.44,12.81,8.49,20.5,8.49h94.12c7.69,0,15.07,3.05,20.5,8.49l107.8,107.79c5.44,5.44,12.81,8.49,20.51,8.49h276.22c7.69,0,15.06-3.05,20.5-8.49l60.44-60.43c5.43-5.44,12.81-8.49,20.5-8.49h156.64"
              fill="none"
              stroke="url(#radial-gradient-5)"
              strokeWidth="2"
            />
            <path
              d="M978.58,807.97h-208.89c-7.69,0-15.07,3.06-20.51,8.49l-24.26,24.26c-5.44,5.44-12.81,8.49-20.51,8.49h-94.12c-7.69,0-15.07,3.05-20.51,8.49l-107.79,107.79c-5.44,5.44-12.82,8.49-20.51,8.49H185.28c-7.69,0-15.07-3.05-20.51-8.49l-60.43-60.43c-5.44-5.44-12.81-8.49-20.51-8.49H-72.81"
              fill="none"
              stroke="#d5d7e9"
            />
            <path
              d="M978.58,807.97h-208.89c-7.69,0-15.07,3.06-20.51,8.49l-24.26,24.26c-5.44,5.44-12.81,8.49-20.51,8.49h-94.12c-7.69,0-15.07,3.05-20.51,8.49l-107.79,107.79c-5.44,5.44-12.82,8.49-20.51,8.49H185.28c-7.69,0-15.07-3.05-20.51-8.49l-60.43-60.43c-5.44-5.44-12.81-8.49-20.51-8.49H-72.81"
              fill="none"
              stroke="url(#radial-gradient-6)"
              strokeWidth="2"
            />
            <g>
              <g mix-blend-mode="multiply">
                <path
                  d="M706.12,859.25h.76c1.66,0,3,1.34,3,3v10c0,1.66-1.34,3-3,3h-.76c-.06.84-.77,1.5-1.62,1.5s-1.56-.66-1.62-1.5h-5.01c-.06.84-.77,1.5-1.62,1.5s-1.56-.66-1.62-1.5h-5.01c-.06.84-.77,1.5-1.62,1.5s-1.56-.66-1.62-1.5h-.76c-1.66,0-3-1.34-3-3v-10c0-1.66,1.34-3,3-3h.76c.06-.84.77-1.5,1.62-1.5s1.56.66,1.62,1.5h5.01c.06-.84.77-1.5,1.62-1.5s1.56.66,1.62,1.5h5.01c.06-.84.77-1.5,1.62-1.5s1.56.66,1.62,1.5Z"
                  fill="#e7e9fb"
                  fillRule="evenodd"
                />
              </g>
              <g mix-blend-mode="multiply">
                <path
                  d="M612.12,703.25h.76c1.66,0,3,1.34,3,3v10c0,1.66-1.34,3-3,3h-.76c-.06.84-.77,1.5-1.62,1.5s-1.56-.66-1.62-1.5h-5.01c-.06.84-.77,1.5-1.62,1.5s-1.56-.66-1.62-1.5h-5.01c-.06.84-.77,1.5-1.62,1.5s-1.56-.66-1.62-1.5h-.76c-1.66,0-3-1.34-3-3v-10c0-1.66,1.34-3,3-3h.76c.06-.84.77-1.5,1.62-1.5s1.56.66,1.62,1.5h5.01c.06-.84.77-1.5,1.62-1.5s1.56.66,1.62,1.5h5.01c.06-.84.77-1.5,1.62-1.5s1.56.66,1.62,1.5Z"
                  fill="#e7e9fb"
                  fillRule="evenodd"
                />
              </g>
              <rect
                x="801.25"
                y="544.75"
                width="7.62"
                height="20.12"
                rx="3"
                ry="3"
                fill="#e7e9fb"
              />
              <rect x="793" y="424" width="20.12" height="7.62" rx="3" ry="3" fill="#e7e9fb" />
              <rect
                x="400.25"
                y="891.75"
                width="7.62"
                height="20.12"
                rx="3"
                ry="3"
                fill="#e7e9fb"
              />
              <path
                d="M114.88,766.06v16.5c0,1.28-1.04,2.31-2.31,2.31h0c-1.28,0-2.31-1.04-2.31-2.31v-16.5c0-1.28,1.04-2.31,2.31-2.31h0c1.28,0,2.31,1.04,2.31,2.31Z"
                fill="#e7e9fb"
              />
              <rect x="104.88" y="943.75" width="10" height="10" rx="3" ry="3" fill="#e7e9fb" />
              <rect x="133.88" y="732.75" width="10" height="10" rx="3" ry="3" fill="#e7e9fb" />
              <rect x="330.88" y="768.75" width="10" height="10" rx="3" ry="3" fill="#e7e9fb" />
              <rect x="494.88" y="716.75" width="10" height="10" rx="3" ry="3" fill="#e7e9fb" />
              <rect x="734.88" y="911.75" width="10" height="10" rx="3" ry="3" fill="#e7e9fb" />
              <rect x="38.88" y="930.75" width="10" height="10" rx="3" ry="3" fill="#e7e9fb" />
              <rect x="468.88" y="966.75" width="10" height="10" rx="3" ry="3" fill="#e7e9fb" />
              <rect
                x="622.25"
                y="633.25"
                width="7.62"
                height="20.12"
                rx="3"
                ry="3"
                fill="#e7e9fb"
              />
            </g>
          </g>
        </g>
      </g>
    </svg>
  );
};
