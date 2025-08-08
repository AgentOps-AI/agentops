'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { truncateString } from '@/lib/utils';

export type DataPoint = {
  name: string;
  count: number;
};

type Payload = {
  fill: string;
  dataKey: string;
  name: string;
  color: string;
  value: number;
  payload: DataPoint;
};

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

const CustomTooltip = ({ active, payload }: { active: boolean; payload: Payload[] }) => {
  if (active && payload && payload.length) {
    return (
      <Card>
        <CardContent>
          <br />
          <p>
            <strong>{truncateString(payload[0].payload.name, 200)}</strong>
          </p>
          <p>{`count: ${payload[0].payload.count}`}</p>
        </CardContent>
      </Card>
    );
  }
  return null;
};

export function Chart({
  data,
  className,
  hideXAxisLabels,
  height,
}: {
  data: DataPoint[];
  className?: string;
  hideXAxisLabels?: boolean;
  height: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height} className={className}>
      <BarChart data={data}>
        <XAxis
          dataKey="name"
          stroke="#888888"
          fontSize={12}
          hide={hideXAxisLabels ? true : false}
          tickLine={false}
          axisLine={false}
          domain={['dataMin', 'dataMax']}
        />
        <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
        {/* <Tooltip /> */}
        <Tooltip content={<CustomTooltip active={false} payload={[]} />} />
        <Bar dataKey="count" fill={COLORS[0]} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
