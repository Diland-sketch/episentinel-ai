import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { EvaluationRow } from '../../lib/api-types'

export default function ForecastChart({ rows }: { rows: EvaluationRow[] }) {
  const data = rows.map(row => ({ ...row, band: row.lo !== null && row.hi !== null ? [row.lo, row.hi] : undefined }))
  return <div className="historical-chart" role="img" aria-label="Comparación retrospectiva de ocho estimaciones y observaciones. Tabla accesible debajo."><ResponsiveContainer width="100%" height="100%" minWidth={0}>
    <ComposedChart data={data} margin={{ top: 15, right: 10, bottom: 5, left: -10 }} accessibilityLayer><CartesianGrid stroke="#e7edf3" vertical={false} />
      <XAxis dataKey="position" tick={{ fill: '#526a7a', fontSize: 12 }} tickLine={false} axisLine={false} /><YAxis tick={{ fill: '#526a7a', fontSize: 12 }} tickLine={false} axisLine={false} />
      <Tooltip labelFormatter={value => `Posición ${value}`} contentStyle={{ border: '1px solid #d5e2ea', borderRadius: 8, fontSize: 13 }} /><Legend />
      {data.some(p => p.band) && <Area dataKey="band" name="Intervalo nominal" fill="#087f8c18" stroke="none" isAnimationActive={false} />}
      <Line dataKey="observed" name="Observado" stroke="#102B38" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />
      <Line dataKey="yhat" name="Estimación" stroke="#087F8C" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} isAnimationActive={false} />
    </ComposedChart>
  </ResponsiveContainer></div>
}
