import { Text, Line } from '@react-three/drei'

const AXIS_LENGTH = 100
const TICK_INTERVAL = 10
const TICK_SIZE = 1.5

const AxisLine = ({ direction, color, label }) => {
  const end = [0, 0, 0]
  end[direction] = AXIS_LENGTH

  const ticks = []
  for (let i = TICK_INTERVAL; i <= AXIS_LENGTH; i += TICK_INTERVAL) {
    const pos = [0, 0, 0]
    pos[direction] = i
    const perp = (direction + 1) % 3
    const tickStart = [...pos]
    const tickEnd = [...pos]
    tickStart[perp] = -TICK_SIZE
    tickEnd[perp] = TICK_SIZE
    ticks.push({ pos, tickStart, tickEnd, value: i })
  }

  const labelPos = [0, 0, 0]
  labelPos[direction] = AXIS_LENGTH + 6

  return (
    <group>
      <Line points={[[0, 0, 0], end]} color={color} lineWidth={2} />
      {ticks.map(({ pos, tickStart, tickEnd, value }) => (
        <group key={value}>
          <Line points={[tickStart, tickEnd]} color={color} lineWidth={1} />
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

const NumberedAxes = () => (
  <group>
    <AxisLine direction={0} color="#ef4444" label="X" />
    <AxisLine direction={1} color="#22c55e" label="Y" />
    <AxisLine direction={2} color="#3b82f6" label="Z" />
  </group>
)

export default NumberedAxes
