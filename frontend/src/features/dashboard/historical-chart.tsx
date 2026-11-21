import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { HistoricalPoint } from '../../lib/api-types'

export default function HistoricalChart({ points, code }: { points: HistoricalPoint[]; code: string }) {
  const yearTicks = points.filter((point, index) => index === 0 || point.technical_date.slice(0, 4) !== points[index - 1]?.technical_date.slice(0, 4)).map(point => point.technical_date)
  return <div className="historical-chart" role="img" aria-label={`Serie histórica real del código ${code}, ${points.length} posiciones. Valores disponibles en la tabla inferior.`}>
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <AreaChart data={points} margin={{ top: 12, right: 8, bottom: 5, left: -18 }} accessibilityLayer>
        <CartesianGrid stroke="#e7edf3" vertical={false} strokeDasharray="3 4" />
        <XAxis dataKey="technical_date" ticks={yearTicks} tickFormatter={(value: string) => value.slice(0, 4)} minTickGap={50} tick={{ fontSize: 12, fill: '#526a7a' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: '#526a7a' }} axisLine={false} tickLine={false} width={65} domain={[0, 'auto']} />
        <Tooltip labelFormatter={label => `Fecha técnica: ${String(label).slice(0, 10)}`} formatter={value => [Number(value).toLocaleString('es-CO'), 'Conteo observado']} contentStyle={{ borderRadius: 8, border: '1px solid #d5e2ea', fontSize: 13, boxShadow: '0 4px 16px #102b3810' }} />
        <Area type="linear" dataKey="observed" stroke="#087F8C" fill="#087f8c12" strokeWidth={1.7} isAnimationActive={false} connectNulls={false} />
      </AreaChart>
    </ResponsiveContainer>
  </div>
}
