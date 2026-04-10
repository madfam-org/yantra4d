import { Text, Line } from '@react-three/drei'

const AXIS_LENGTH = 100
const TICK_INTERVAL = 10
const TICK_SIZE = 1.5

interface AxisLineProps {
  direction: number
  color: string
  label: string
}

const AxisLine = ({ direction, color, label }: AxisLineProps) => {
  const end: [number, number, number] = [0, 0, 0]
  end[direction] = AXIS_LENGTH

  const ticks: { pos: [number, number, number]; tickStart: [number, number, number]; tickEnd: [number, number, number]; value: number }[] = []
  for (let i = TICK_INTERVAL; i <= AXIS_LENGTH; i += TICK_INTERVAL) {
    const pos: [number, number, number] = [0, 0, 0]
    pos[direction] = i
    const perp = (direction + 1) % 3
    const tickStart: [number, number, number] = [...pos]
    const tickEnd: [number, number, number] = [...pos]
    tickStart[perp] = -TICK_SIZE
    tickEnd[perp] = TICK_SIZE
    ticks.push({ pos, tickStart, tickEnd, value: i })
  }

  const labelPos: [number, number, number] = [0, 0, 0]
  labelPos[direction] = AXIS_LENGTH + 6

  return (
    <group>
      <Line points={[[0, 0, 0] as [number, number, number], end]} color={color} lineWidth={2} />
      {ticks.map(({ pos, tickStart, tickEnd, value }) => (
        <group key={value}>
          <Line points={[tickStart, tickEnd] as [number, number, number][]} color={color} lineWidth={1} />
          <Text
            position={pos}
            fontSize={3}
            color={color}
            anchorX="center"
            anchorY="bottom"
          >
            {String(value)}
          </Text>
        </group>
      ))}
      <Text position={labelPos} fontSize={5} color={color} anchorX="center" anchorY="middle" fontWeight="bold">
        {label}
      </Text>
    </group>
  )
}

const DEFAULT_AXIS_COLORS = ['#ef4444', '#22c55e', '#3b82f6']

interface NumberedAxesProps {
  axisColors?: string[]
}

const NumberedAxes = ({ axisColors = DEFAULT_AXIS_COLORS }: NumberedAxesProps) => (
  <group>
    <AxisLine direction={0} color={axisColors[0]} label="X" />
    <AxisLine direction={1} color={axisColors[1]} label="Y" />
    <AxisLine direction={2} color={axisColors[2]} label="Z" />
  </group>
)

export default NumberedAxes
