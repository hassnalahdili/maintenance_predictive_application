import NotificationsActiveRoundedIcon from '@mui/icons-material/NotificationsActiveRounded'
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded'
import PictureAsPdfRoundedIcon from '@mui/icons-material/PictureAsPdfRounded'
import ReportProblemRoundedIcon from '@mui/icons-material/ReportProblemRounded'
import TaskAltRoundedIcon from '@mui/icons-material/TaskAltRounded'
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid2 as Grid,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import { downloadBlob } from '../services/downloads'

function SummaryCard({ label, value, helper, accent, icon }) {
  return (
    <Card sx={{ borderRadius: 4, height: '100%', background: 'rgba(255,255,255,0.96)' }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Stack spacing={1}>
            <Typography color="text.secondary">{label}</Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: '-0.04em', color: accent }}>
              {value}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {helper}
            </Typography>
          </Stack>
          <Chip icon={icon} label="" sx={{ bgcolor: `${accent}14`, color: accent }} />
        </Stack>
      </CardContent>
    </Card>
  )
}

function levelTone(level) {
  if (level === 'critical') {
    return { color: '#b91c1c', soft: 'rgba(185, 28, 28, 0.10)' }
  }
  if (level === 'high') {
    return { color: '#ea580c', soft: 'rgba(234, 88, 12, 0.10)' }
  }
  if (level === 'medium') {
    return { color: '#2563eb', soft: 'rgba(37, 99, 235, 0.10)' }
  }
  return { color: '#0f766e', soft: 'rgba(15, 118, 110, 0.10)' }
}

export default function AlertsPage() {
  const { user } = useAuth()
  const [alerts, setAlerts] = useState([])
  const [filters, setFilters] = useState({ status: '', level: '' })
  const [error, setError] = useState('')
  const [selectedAlert, setSelectedAlert] = useState(null)
  const [comment, setComment] = useState('')

  const loadAlerts = async () => {
    try {
      const response = await api.get('/api/alerts/', { params: filters })
      setAlerts(response.data)
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement des alertes impossible')
    }
  }

  useEffect(() => {
    loadAlerts()
    const interval = window.setInterval(loadAlerts, 30000)
    return () => window.clearInterval(interval)
  }, [filters])

  const handleAcknowledge = async () => {
    try {
      await api.post(`/api/alerts/${selectedAlert.id}/acknowledge`, { comment })
      setSelectedAlert(null)
      setComment('')
      loadAlerts()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Accuse de reception impossible')
    }
  }

  const canAcknowledge = ['admin', 'technicien'].includes(user?.role)
  const activeAlerts = alerts.filter((alert) => alert.status === 'active').length
  const acknowledgedAlerts = alerts.filter((alert) => alert.acknowledged).length
  const criticalAlerts = alerts.filter((alert) => ['high', 'critical'].includes(alert.level)).length
  const levelBreakdown = useMemo(
    () =>
      ['low', 'medium', 'high', 'critical'].map((level) => ({
        level,
        count: alerts.filter((alert) => alert.level === level).length,
      })),
    [alerts],
  )

  return (
    <Stack spacing={3}>
      {error && <Alert severity="error">{error}</Alert>}

      <Paper
        sx={{
          p: 3,
          borderRadius: 5,
          background: 'linear-gradient(135deg, #431407 0%, #b91c1c 48%, #f97316 100%)',
          color: '#fff',
        }}
      >
        <Stack spacing={1.2}>
          <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: '-0.04em' }}>
            Systeme d'alertes
          </Typography>
          
          <Button
            variant="contained"
            startIcon={<DownloadRoundedIcon />}
            onClick={() => downloadBlob('/api/exports/alerts.csv', 'alertes.csv')}
            sx={{ alignSelf: 'flex-start', borderRadius: 999, bgcolor: '#fff', color: '#431407' }}
          >
            Export CSV
          </Button>
        </Stack>
      </Paper>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6, xl: 4 }}>
          <SummaryCard
            label="Alertes actives"
            value={activeAlerts}
            helper="Alertes qui demandent encore une action de prise en charge."
            accent="#dc2626"
            icon={<NotificationsActiveRoundedIcon fontSize="small" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 4 }}>
          <SummaryCard
            label="Alertes critiques"
            value={criticalAlerts}
            helper="Niveaux high et critical, donc les plus urgents."
            accent="#ea580c"
            icon={<ReportProblemRoundedIcon fontSize="small" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 4 }}>
          <SummaryCard
            label="Alertes accusees"
            value={acknowledgedAlerts}
            helper="Alertes deja vues et accusees par un utilisateur autorise."
            accent="#0f766e"
            icon={<TaskAltRoundedIcon fontSize="small" />}
          />
        </Grid>
      </Grid>

      <Stack spacing={2}>
        <Paper sx={{ p: 2.5, borderRadius: 4 }}>
          <Stack spacing={2}>
            <Stack spacing={0.8}>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                Filtres
              </Typography>
              
            </Stack>

            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField
                  select
                  label="Statut"
                  value={filters.status}
                  onChange={(event) => setFilters({ ...filters, status: event.target.value })}
                  fullWidth
                >
                  <MenuItem value="">Tous</MenuItem>
                  <MenuItem value="active">Actives</MenuItem>
                  <MenuItem value="acknowledged">Accusees</MenuItem>
                  <MenuItem value="escalated">Escaladees</MenuItem>
                </TextField>
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField
                  select
                  label="Niveau"
                  value={filters.level}
                  onChange={(event) => setFilters({ ...filters, level: event.target.value })}
                  fullWidth
                >
                  <MenuItem value="">Tous</MenuItem>
                  {['low', 'medium', 'high', 'critical'].map((level) => (
                    <MenuItem key={level} value={level}>
                      {level}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {levelBreakdown.map((item) => (
                    <Chip
                      key={item.level}
                      label={`${item.level}: ${item.count}`}
                      sx={{ bgcolor: levelTone(item.level).soft, color: levelTone(item.level).color }}
                    />
                  ))}
                </Stack>
              </Grid>
            </Grid>
          </Stack>
        </Paper>

        <Paper sx={{ p: 2.5, borderRadius: 4 }}>
          <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
            Alertes
          </Typography>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Machine</TableCell>
                <TableCell>Niveau</TableCell>
                <TableCell>Probabilite</TableCell>
                <TableCell>Statut</TableCell>
                <TableCell>Message</TableCell>
                <TableCell>Date</TableCell>
                <TableCell align="right">Action</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {alerts.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.id}</TableCell>
                  <TableCell>{item.machine_name || `Machine #${item.machine_id}`}</TableCell>
                  <TableCell>
                    <Chip label={item.level} size="small" sx={{ bgcolor: levelTone(item.level).soft, color: levelTone(item.level).color }} />
                  </TableCell>
                  <TableCell>{item.probability ? `${Math.round(item.probability * 100)}%` : '-'}</TableCell>
                  <TableCell>{item.status}</TableCell>
                  <TableCell>{item.message}</TableCell>
                  <TableCell>{new Date(item.created_at).toLocaleString()}</TableCell>
                  <TableCell align="right">
                    {!item.acknowledged && canAcknowledge && (
                      <Button variant="outlined" onClick={() => setSelectedAlert(item)} sx={{ borderRadius: 999 }}>
                        Accuser
                      </Button>
                    )}
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<PictureAsPdfRoundedIcon fontSize="small" />}
                      onClick={() => downloadBlob(`/api/exports/alerts/${item.id}.pdf`, `alerte_${item.id}.pdf`)}
                      sx={{ borderRadius: 999, ml: 1 }}
                    >
                      PDF
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {alerts.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8}>
                    <Typography color="text.secondary">Aucune alerte ne correspond aux filtres.</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Paper>
      </Stack>

      <Dialog open={Boolean(selectedAlert)} onClose={() => setSelectedAlert(null)} fullWidth maxWidth="sm">
        <DialogTitle>Accuser reception de l'alerte</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography>{selectedAlert?.message}</Typography>
            <TextField label="Commentaire" multiline minRows={3} value={comment} onChange={(event) => setComment(event.target.value)} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedAlert(null)}>Annuler</Button>
          <Button variant="contained" onClick={handleAcknowledge} sx={{ borderRadius: 999 }}>
            Valider
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
