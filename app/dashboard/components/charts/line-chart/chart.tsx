'use client';

import { Card, CardContent } from '@/components/ui/card';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

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

const CustomTooltip = ({ active, payload }: { active: boolean; payload: Payload[] }) => {
  if (active && payload && payload.length) {
    return (
      <Card>
        <CardContent>
          <br />
          <p>
            <strong>{payload[0].payload.name}</strong>
          </p>
          <p>{`count: ${payload[0].payload.count}`}</p>
        </CardContent>
      </Card>
    );
  }
  return null;
};

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

export function Chart({ data }: { data: DataPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" domain={['dataMin', 'dataMax']} hide />
        <YAxis />
        <Legend />
        <Tooltip content={<CustomTooltip active={false} payload={[]} />} />
        <Line type="monotone" dataKey="count" dot={false} stroke={COLORS[0]} />
      </LineChart>
    </ResponsiveContainer>
  );
}
