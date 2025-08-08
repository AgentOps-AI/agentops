import { FC } from 'react';
import { truncateString } from '@/lib/utils';

interface Props {
  x: number;
  y: number;
  payload: {
    value: string;
  };
  maxLength?: number;
}

export const CustomizedAxisTick: FC<Props> = ({ x, y, payload, maxLength }) => {
  let truncatedText = payload.value;
  if (payload.value.includes('-')) {
    truncatedText = payload.value.split('-')[1];
  }

  if (maxLength) {
    truncatedText = truncateString(truncatedText, maxLength);
  }

  return (
    <g transform={`translate(${x},${y})`}>
      <text x={0} y={0} dy={16} textAnchor="end" fill="#666" fontSize={12} transform="rotate(-35)">
        {truncatedText}
      </text>
    </g>
  );
};
