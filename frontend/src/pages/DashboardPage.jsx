import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded'
import SensorsRoundedIcon from '@mui/icons-material/SensorsRounded'
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded'
import { Alert, Box, Card, CardContent, Chip, Grid2 as Grid, LinearProgress, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import { buildLiveSocketUrl } from '../services/runtimeConfig'

const sensorMetrics = [
  { key: 'temperature', label: 'Temperature', unit: '°C', color: '#c2410c' },
  { key: 'vibration_total', label: 'Vibration', unit: 'g', color: '#0f766e' },
  { key: 'pressure', label: 'Pression', unit: 'bar', color: '#2563eb' },
  { key: 'rpm', label: 'RPM', unit: 'tr/min', color: '#059669' },
  { key: 'current', label: 'Courant', unit: 'A', color: '#dc2626' },
]

const emptySummary = {
  total_machines: 0,
  active_alerts: 0,
  machines_at_risk: 0,
  status_distribution: {},
  risk_distribution: {},
  prediction_trend: [],
  machine_health: [],
  available_types: [],
  available_sites: [],
  last_updated_at: null,
}

function clampPercent(value) {
  return Math.max(0, Math.min(100, Math.round((value || 0) * 100)))
}

function linePath(points, width, height, accessor) {
  if (!points?.length) {
    return ''
  }
  const values = points.map((point) => Number(accessor(point) || 0))
  const max = Math.max(...values, 1)
  const min = Math.min(...values, 0)
  const range = max - min || 1
  return points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width
      const y = height - ((Number(accessor(point) || 0) - min) / range) * height
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
}

function areaPath(points, width, height, accessor) {
  if (!points?.length) {
    return ''
  }
  const line = linePath(points, width, height, accessor)
  return `${line} L ${width} ${height} L 0 ${height} Z`
}

function riskPalette(level) {
  if (level === 'critical') {
    return { label: 'Panne probable', color: '#b91c1c', soft: 'rgba(185, 28, 28, 0.10)' }
  }
  if (level === 'high') {
    return { label: 'Risque eleve', color: '#ea580c', soft: 'rgba(234, 88, 12, 0.10)' }
  }
  if (level === 'medium' || level === 'low') {
    return { label: 'Sous surveillance', color: '#2563eb', soft: 'rgba(37, 99, 235, 0.10)' }
  }
  return { label: 'Pas de panne probable', color: '#0f766e', soft: 'rgba(15, 118, 110, 0.10)' }
}

function formatMetric(value, unit, digits = 1) {
  if (value === null || value === undefined) {
    return '-'
  }
  return `${Number(value).toFixed(digits)} ${unit}`.trim()
}

function formatDate(value) {
  if (!value) {
    return '-'
  }
  return new Date(value).toLocaleString()
}

function MiniSparkline({ points, accessor, color = '#2563eb', fill = 'rgba(37, 99, 235, 0.10)', height = 64 }) {
  if (!points?.length) {
    return (
      <Box
        sx={{
          height,
          borderRadius: 2,
          bgcolor: 'rgba(148, 163, 184, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Typography variant="caption" color="text.secondary">
          Pas d'historique
        </Typography>
      </Box>
    )
  }

  const width = 240
  return (
    <Box sx={{ width: '100%', height }}>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" width="100%" height="100%">
        <path d={areaPath(points, width, height - 6, accessor)} fill={fill} transform="translate(0 3)" />
        <path
          d={linePath(points, width, height - 6, accessor)}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          transform="translate(0 3)"
        />
      </svg>
    </Box>
  )
}

function FleetTrendChart({ points }) {
  if (!points?.length) {
    return (
      <Box
        sx={{
          minHeight: 260,
          borderRadius: 3,
          bgcolor: 'rgba(148, 163, 184, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Typography color="text.secondary">Aucune prediction historisee pour le moment.</Typography>
      </Box>
    )
  }

  const width = 820
  const height = 260
  const lineAverage = linePath(points, width, height - 24, (point) => point.average_probability)
  const lineMax = linePath(points, width, height - 24, (point) => point.max_probability)
  const areaAverage = areaPath(points, width, height - 24, (point) => point.average_probability)

  return (
    <Stack spacing={1.5}>
      <Box
        sx={{
          p: 2,
          borderRadius: 3,
          background: 'linear-gradient(180deg, rgba(15, 118, 110, 0.08) 0%, rgba(255,255,255,0.92) 100%)',
          border: '1px solid rgba(15, 118, 110, 0.12)',
        }}
      >
        <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" width="100%" height={height}>
          {[0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = (height - 24) * (1 - ratio) + 12
            return (
              <line
                key={ratio}
                x1="0"
                x2={width}
                y1={y}
                y2={y}
                stroke="rgba(148, 163, 184, 0.22)"
                strokeDasharray="4 6"
              />
            )
          })}
          <path d={areaAverage} fill="rgba(37, 99, 235, 0.12)" transform="translate(0 12)" />
          <path d={lineAverage} fill="none" stroke="#2563eb" strokeWidth="4" strokeLinecap="round" transform="translate(0 12)" />
          <path d={lineMax} fill="none" stroke="#dc2626" strokeWidth="4" strokeLinecap="round" transform="translate(0 12)" />
        </svg>
      </Box>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} flexWrap="wrap">
        <Chip label="Ligne bleue: risque moyen du parc" sx={{ bgcolor: 'rgba(37, 99, 235, 0.10)', color: '#1d4ed8' }} />
        <Chip label="Ligne rouge: risque maximum observe" sx={{ bgcolor: 'rgba(220, 38, 38, 0.10)', color: '#b91c1c' }} />
      </Stack>
    </Stack>
  )
}

function DistributionBar({ label, count, total, color }) {
  const percent = total ? Math.round((count / total) * 100) : 0
  return (
    <Stack spacing={0.8}>
      <Stack direction="row" justifyContent="space-between">
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {label}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {count} • {percent}%
        </Typography>
      </Stack>
      <LinearProgress
        variant="determinate"
        value={percent}
        sx={{
          height: 10,
          borderRadius: 999,
          bgcolor: 'rgba(148, 163, 184, 0.14)',
          '& .MuiLinearProgress-bar': {
            borderRadius: 999,
            bgcolor: color,
          },
        }}
      />
    </Stack>
  )
}

function RiskHeatmap({ machines }) {
  const cells = useMemo(() => {
    const grouped = new Map()
    machines.forEach((machine) => {
      const key = `${machine.site || 'Sans site'} • ${machine.machine_type}`
      const current = grouped.get(key) || { count: 0, maxRisk: 0, site: machine.site || 'Sans site', type: machine.machine_type }
      current.count += 1
      current.maxRisk = Math.max(current.maxRisk, machine.failure_probability || 0)
      grouped.set(key, current)
    })
    return Array.from(grouped.values()).sort((a, b) => b.maxRisk - a.maxRisk)
  }, [machines])

  if (cells.length === 0) {
    return <Typography color="text.secondary">Aucune donnee pour construire la carte thermique.</Typography>
  }

  return (
    <Grid container spacing={1.5}>
      {cells.map((cell) => {
        const palette = riskPalette(cell.maxRisk >= 0.8 ? 'critical' : cell.maxRisk >= 0.55 ? 'high' : cell.maxRisk >= 0.3 ? 'medium' : 'normal')
        return (
          <Grid size={{ xs: 12, sm: 6, lg: 3 }} key={`${cell.site}-${cell.type}`}>
            <Paper
              variant="outlined"
              sx={{
                p: 1.5,
                borderRadius: 3,
                bgcolor: palette.soft,
                borderColor: `${palette.color}40`,
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 800, color: palette.color }}>
                {Math.round(cell.maxRisk * 100)}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {cell.site} • {cell.type} • {cell.count} machine(s)
              </Typography>
            </Paper>
          </Grid>
        )
      })}
    </Grid>
  )
}

function SensorMetricCard({ label, value, unit, color, points, accessor }) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        borderRadius: 3,
        borderColor: 'rgba(148, 163, 184, 0.16)',
        background: 'rgba(255, 255, 255, 0.90)',
      }}
    >
      <Stack spacing={1}>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h5" sx={{ fontWeight: 800, color }}>
          {formatMetric(value, unit)}
        </Typography>
        <MiniSparkline points={points} accessor={accessor} color={color} fill={`${color}1A`} height={58} />
      </Stack>
    </Paper>
  )
}

export default function DashboardPage() {
  const { token } = useAuth()
  const [summary, setSummary] = useState(emptySummary)
  const [filters, setFilters] = useState({ machine_type: '', risk_level: '', site: '' })
  const [selectedMachineId, setSelectedMachineId] = useState(null)
  const [error, setError] = useState('')
  const [liveStatus, setLiveStatus] = useState('disconnected')
  const [lastLiveEvent, setLastLiveEvent] = useState(null)

  useEffect(() => {
    let isMounted = true

    const load = async () => {
      try {
        const response = await api.get('/api/dashboard/summary', { params: filters })
        if (isMounted) {
          setSummary(response.data)
          setError('')
        }
      } catch (requestError) {
        if (isMounted) {
          setError(requestError.response?.data?.detail || 'Chargement impossible du dashboard')
        }
      }
    }

    load()
    const interval = window.setInterval(load, 30000)
    return () => {
      isMounted = false
      window.clearInterval(interval)
    }
  }, [filters])

  useEffect(() => {
    if (!token) {
      return undefined
    }
    const socket = new WebSocket(buildLiveSocketUrl(token))
    const heartbeat = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send('ping')
      }
    }, 20000)

    socket.onopen = () => setLiveStatus('connected')
    socket.onclose = () => setLiveStatus('disconnected')
    socket.onerror = () => setLiveStatus('error')
    socket.onmessage = async (event) => {
      try {
        const payload = JSON.parse(event.data)
        setLastLiveEvent(payload.type)
        if (payload.type !== 'live_connected') {
          const response = await api.get('/api/dashboard/summary', { params: filters })
          setSummary(response.data)
        }
      } catch {
        setLiveStatus('error')
      }
    }

    return () => {
      window.clearInterval(heartbeat)
      socket.close()
    }
  }, [token, filters])

  useEffect(() => {
    if (!summary.machine_health.length) {
      setSelectedMachineId(null)
      return
    }
    if (!summary.machine_health.some((machine) => machine.machine_id === selectedMachineId)) {
      setSelectedMachineId(summary.machine_health[0].machine_id)
    }
  }, [summary.machine_health, selectedMachineId])

  const selectedMachine = useMemo(
    () => summary.machine_health.find((machine) => machine.machine_id === selectedMachineId) || summary.machine_health[0] || null,
    [summary.machine_health, selectedMachineId],
  )

  const probableFailuresCount = summary.machine_health.filter((machine) => ['high', 'critical'].includes(machine.alert_level)).length
  const liveChipColor = liveStatus === 'connected' ? 'success' : liveStatus === 'error' ? 'error' : 'default'

  return (
    <Stack spacing={3.5}>
      <Paper
        sx={{
          p: { xs: 2.5, md: 3 },
          borderRadius: 5,
          background: 'linear-gradient(135deg, #0f172a 0%, #0f766e 50%, #0ea5e9 100%)',
          color: '#fff',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            background:
              'radial-gradient(circle at top right, rgba(255,255,255,0.20), transparent 25%), radial-gradient(circle at bottom left, rgba(255,255,255,0.10), transparent 30%)',
            pointerEvents: 'none',
          }}
        />
        <Stack spacing={2.5} sx={{ position: 'relative' }}>
          <Stack direction={{ xs: 'column', lg: 'row' }} justifyContent="space-between" spacing={2}>
            <Stack spacing={1}>
              <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: '-0.04em' }}>
                Vue predictive maintenance
              </Typography>
             
            </Stack>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
              <Chip label={`Live ${liveStatus}`} color={liveChipColor} />
              {lastLiveEvent && <Chip label={`Dernier evenement: ${lastLiveEvent}`} sx={{ bgcolor: 'rgba(255,255,255,0.15)', color: '#fff' }} />}
              {summary.last_updated_at && <Chip label={`Maj ${formatDate(summary.last_updated_at)}`} sx={{ bgcolor: 'rgba(255,255,255,0.15)', color: '#fff' }} />}
            </Stack>
          </Stack>

          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <TextField
              select
              label="Type machine"
              value={filters.machine_type}
              onChange={(event) => setFilters({ ...filters, machine_type: event.target.value })}
              fullWidth
              sx={{ '& .MuiOutlinedInput-root': { bgcolor: 'rgba(255,255,255,0.96)', borderRadius: 3 } }}
            >
              <MenuItem value="">Tous</MenuItem>
              {summary.available_types.map((type) => (
                <MenuItem key={type} value={type}>
                  {type}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Niveau de risque"
              value={filters.risk_level}
              onChange={(event) => setFilters({ ...filters, risk_level: event.target.value })}
              fullWidth
              sx={{ '& .MuiOutlinedInput-root': { bgcolor: 'rgba(255,255,255,0.96)', borderRadius: 3 } }}
            >
              <MenuItem value="">Tous</MenuItem>
              {['normal', 'low', 'medium', 'high', 'critical'].map((level) => (
                <MenuItem key={level} value={level}>
                  {level}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Site"
              value={filters.site}
              onChange={(event) => setFilters({ ...filters, site: event.target.value })}
              fullWidth
              sx={{ '& .MuiOutlinedInput-root': { bgcolor: 'rgba(255,255,255,0.96)', borderRadius: 3 } }}
            >
              <MenuItem value="">Tous</MenuItem>
              {summary.available_sites.map((site) => (
                <MenuItem key={site} value={site}>
                  {site}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        </Stack>
      </Paper>

      {error && <Alert severity="error">{error}</Alert>}

      <Grid container spacing={2}>
        {[
          {
            label: 'Machines surveillees',
            value: summary.total_machines,
            tone: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
            icon: <SensorsRoundedIcon fontSize="small" />,
          },
          {
            label: 'Alertes actives',
            value: summary.active_alerts,
            tone: 'linear-gradient(135deg, #9a3412 0%, #ea580c 100%)',
            icon: <WarningAmberRoundedIcon fontSize="small" />,
          },
          {
            label: 'Machines a risque',
            value: summary.machines_at_risk,
            tone: 'linear-gradient(135deg, #1d4ed8 0%, #0ea5e9 100%)',
            icon: <InsightsRoundedIcon fontSize="small" />,
          },
          {
            label: 'Pannes probables',
            value: probableFailuresCount,
            tone: 'linear-gradient(135deg, #991b1b 0%, #dc2626 100%)',
            icon: <WarningAmberRoundedIcon fontSize="small" />,
          },
        ].map((item) => (
          <Grid size={{ xs: 12, sm: 6, xl: 3 }} key={item.label}>
            <Card
              sx={{
                borderRadius: 4,
                color: '#fff',
                background: item.tone,
                boxShadow: '0 16px 40px rgba(15, 23, 42, 0.12)',
              }}
            >
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Stack spacing={0.8}>
                    <Typography sx={{ color: 'rgba(255,255,255,0.76)' }}>{item.label}</Typography>
                    <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-0.04em' }}>
                      {item.value}
                    </Typography>
                  </Stack>
                  <Box sx={{ p: 1, borderRadius: 3, bgcolor: 'rgba(255,255,255,0.12)' }}>{item.icon}</Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, xl: 8 }}>
          <Paper sx={{ p: 2.5, borderRadius: 4, height: '100%' }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
              <div>
                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                  Courbe de risque du parc
                </Typography>
                
              </div>
            </Stack>
            <FleetTrendChart points={summary.prediction_trend} />
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, xl: 4 }}>
          <Paper sx={{ p: 2.5, borderRadius: 4, height: '100%' }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 0.5 }}>
              Repartition etat et criticite
            </Typography>
            
            <Stack spacing={2.25}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                Etats machine
              </Typography>
              {Object.entries(summary.status_distribution).length === 0 ? (
                <Typography color="text.secondary">Aucune donnee disponible.</Typography>
              ) : (
                Object.entries(summary.status_distribution).map(([status, count]) => (
                  <DistributionBar
                    key={status}
                    label={status}
                    count={count}
                    total={summary.total_machines}
                    color="#0f766e"
                  />
                ))
              )}

              <Typography variant="subtitle2" sx={{ fontWeight: 700, pt: 1 }}>
                Risque de panne
              </Typography>
              {Object.entries(summary.risk_distribution || {}).map(([level, count]) => (
                <DistributionBar
                  key={level}
                  label={level}
                  count={count}
                  total={summary.total_machines}
                  color={riskPalette(level).color}
                />
              ))}
            </Stack>
          </Paper>
        </Grid>
      </Grid>

      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 0.5 }}>
          Carte thermique des risques
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          Vue compacte par site et type de machine pour reperer les zones qui concentrent les probabilites de panne les plus fortes.
        </Typography>
        <RiskHeatmap machines={summary.machine_health} />
      </Paper>

      {selectedMachine && (
        <Paper sx={{ p: 2.5, borderRadius: 4 }}>
          <Grid container spacing={2.5}>
            <Grid size={{ xs: 12, lg: 4 }}>
              <Stack spacing={2}>
                <Stack spacing={1}>
                  <Typography variant="overline" sx={{ letterSpacing: '0.12em', color: '#64748b', fontWeight: 700 }}>
                    Machine en focus
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 900, letterSpacing: '-0.04em' }}>
                    {selectedMachine.machine_name}
                  </Typography>
                  <Typography color="text.secondary">
                    {selectedMachine.machine_type} • {selectedMachine.site || 'Sans site'} • derniere prediction {formatDate(selectedMachine.timestamp)}
                  </Typography>
                </Stack>

                <Stack direction="row" spacing={1} flexWrap="wrap">
                  <Chip
                    label={riskPalette(selectedMachine.alert_level).label}
                    sx={{ bgcolor: riskPalette(selectedMachine.alert_level).soft, color: riskPalette(selectedMachine.alert_level).color, fontWeight: 700 }}
                  />
                  <Chip label={`Statut: ${selectedMachine.status}`} variant="outlined" />
                  <Chip label={`RUL: ${selectedMachine.remaining_useful_life_days ?? '-'} jours`} variant="outlined" />
                </Stack>

                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    borderRadius: 3,
                    bgcolor: riskPalette(selectedMachine.alert_level).soft,
                    borderColor: 'transparent',
                  }}
                >
                  <Stack spacing={1}>
                    <Typography color="text.secondary">Probabilite de panne</Typography>
                    <Typography variant="h3" sx={{ fontWeight: 900, color: riskPalette(selectedMachine.alert_level).color }}>
                      {clampPercent(selectedMachine.failure_probability)}%
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={clampPercent(selectedMachine.failure_probability)}
                      sx={{
                        height: 12,
                        borderRadius: 999,
                        bgcolor: 'rgba(255,255,255,0.4)',
                        '& .MuiLinearProgress-bar': { bgcolor: riskPalette(selectedMachine.alert_level).color, borderRadius: 999 },
                      }}
                    />
                    <Typography variant="body2" color="text.secondary">
                      Derniere mesure capteur: {formatDate(selectedMachine.current_sensor_values?.timestamp)}
                    </Typography>
                  </Stack>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
                    Tendance du risque pour cette machine
                  </Typography>
                  <MiniSparkline
                    points={selectedMachine.probability_trend}
                    accessor={(point) => point.value}
                    color={riskPalette(selectedMachine.alert_level).color}
                    fill={riskPalette(selectedMachine.alert_level).soft}
                    height={90}
                  />
                </Paper>
              </Stack>
            </Grid>

            <Grid size={{ xs: 12, lg: 8 }}>
              <Grid container spacing={2}>
                {sensorMetrics.map((metric) => (
                  <Grid size={{ xs: 12, sm: 6, xl: 4 }} key={metric.key}>
                    <SensorMetricCard
                      label={metric.label}
                      value={selectedMachine.current_sensor_values?.[metric.key]}
                      unit={metric.unit}
                      color={metric.color}
                      points={selectedMachine.sensor_trend}
                      accessor={(point) => point[metric.key]}
                    />
                  </Grid>
                ))}
              </Grid>
            </Grid>
          </Grid>
        </Paper>
      )}

      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={1.5} sx={{ mb: 2 }}>
          <div>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              Etat de sante des machines
            </Typography>
            <Typography color="text.secondary">
              Cliquez sur une machine pour mettre ses courbes et ses mesures actuelles en focus.
            </Typography>
          </div>
          {selectedMachine && (
            <Chip
              label={`Machine focus: ${selectedMachine.machine_name}`}
              sx={{ bgcolor: 'rgba(15, 118, 110, 0.08)', color: '#115e59', fontWeight: 700 }}
            />
          )}
        </Stack>

        <Grid container spacing={2}>
          {summary.machine_health.length === 0 && (
            <Grid size={12}>
              <Typography color="text.secondary">Aucune machine ne correspond aux filtres.</Typography>
            </Grid>
          )}

          {summary.machine_health.map((machine) => (
            <Grid size={{ xs: 12, md: 6, xl: 4 }} key={machine.machine_id}>
              <Paper
                onClick={() => setSelectedMachineId(machine.machine_id)}
                sx={{
                  p: 2,
                  height: '100%',
                  borderRadius: 4,
                  cursor: 'pointer',
                  border: selectedMachine?.machine_id === machine.machine_id ? '2px solid #0f766e' : '1px solid rgba(148, 163, 184, 0.18)',
                  background:
                    selectedMachine?.machine_id === machine.machine_id
                      ? 'linear-gradient(180deg, rgba(15, 118, 110, 0.06) 0%, rgba(255,255,255,0.96) 100%)'
                      : 'rgba(255,255,255,0.96)',
                  transition: 'transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: '0 16px 36px rgba(15, 23, 42, 0.08)',
                  },
                }}
              >
                <Stack spacing={1.5}>
                  <Stack direction="row" justifyContent="space-between" spacing={1}>
                    <div>
                      <Typography variant="h6" sx={{ fontWeight: 800 }}>
                        {machine.machine_name}
                      </Typography>
                      <Typography color="text.secondary">
                        {machine.machine_type} • {machine.site || 'Sans site'}
                      </Typography>
                    </div>
                    <Chip
                      label={riskPalette(machine.alert_level).label}
                      sx={{ bgcolor: riskPalette(machine.alert_level).soft, color: riskPalette(machine.alert_level).color, fontWeight: 700 }}
                    />
                  </Stack>

                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2">Statut: {machine.status}</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      {clampPercent(machine.failure_probability)}%
                    </Typography>
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={clampPercent(machine.failure_probability)}
                    sx={{
                      height: 10,
                      borderRadius: 999,
                      bgcolor: 'rgba(148, 163, 184, 0.14)',
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 999,
                        bgcolor: riskPalette(machine.alert_level).color,
                      },
                    }}
                  />

                  <MiniSparkline
                    points={machine.probability_trend}
                    accessor={(point) => point.value}
                    color={riskPalette(machine.alert_level).color}
                    fill={riskPalette(machine.alert_level).soft}
                    height={72}
                  />

                  <Grid container spacing={1}>
                    {sensorMetrics.map((metric) => (
                      <Grid size={{ xs: 6, sm: 4 }} key={metric.key}>
                        <Paper variant="outlined" sx={{ p: 1.2, borderRadius: 2.5, bgcolor: 'rgba(248,250,252,0.9)' }}>
                          <Typography variant="caption" color="text.secondary">
                            {metric.label}
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {formatMetric(machine.current_sensor_values?.[metric.key], metric.unit)}
                          </Typography>
                        </Paper>
                      </Grid>
                    ))}
                  </Grid>
                </Stack>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Paper>
    </Stack>
  )
}
