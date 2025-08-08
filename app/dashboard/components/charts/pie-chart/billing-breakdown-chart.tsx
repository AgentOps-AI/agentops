'use client';

import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { useMemo } from 'react';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

interface CostBreakdownItem {
  name: string;
  value: number;
  color: string;
}

interface BillingBreakdownChartProps {
  costBreakdown: CostBreakdownItem[];
  className?: string;
}

export function BillingBreakdownChart({
  costBreakdown,
  className = '',
}: BillingBreakdownChartProps) {
  const paddingAngle = useMemo(() => {
    return costBreakdown.length > 1 ? 2 : 0;
  }, [costBreakdown.length]);

  if (!costBreakdown.length) {
    return null;
  }

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={costBreakdown}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={80}
            paddingAngle={paddingAngle}
            dataKey="value"
            animationBegin={0}
            animationDuration={300}
            isAnimationActive={true}
          >
            {costBreakdown.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>

      <div className="flex flex-wrap items-center justify-center gap-4">
        {costBreakdown.map((item) => (
          <div key={item.name} className="flex items-center space-x-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="text-sm">{item.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
