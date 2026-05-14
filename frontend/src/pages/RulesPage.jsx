import { useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
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
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const machineTypes = ['moteur', 'pompe', 'convoyeur', 'compresseur', 'ventilateur', 'generateur', 'broyeur', 'four']
const metrics = ['temperature', 'vibration_x', 'vibration_y', 'vibration_z', 'pressure', 'rpm', 'current']
const severities = ['low', 'medium', 'high', 'critical']
const operators = ['>', '>=', '<', '<=', '==']

const initialForm = {
  name: '',
  machine_type: 'moteur',
  metric: 'temperature',
  operator: '>',
  threshold: 85,
  duration_seconds: 0,
  severity: 'medium',
  confidence: 0.8,
  is_active: true,
}

export default function RulesPage() {
  const { user } = useAuth()
  const [rules, setRules] = useState([])
  const [form, setForm] = useState(initialForm)
  const [editingId, setEditingId] = useState(null)
  const [simulation, setSimulation] = useState(null)
  const [versions, setVersions] = useState([])
  const [versionsTitle, setVersionsTitle] = useState('')
  const [error, setError] = useState('')

  const canManageRules = ['admin', 'expert'].includes(user?.role)

  const loadRules = async () => {
    try {
      const response = await api.get('/api/rules/')
      setRules(response.data)
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement des regles impossible')
    }
  }

  useEffect(() => {
    loadRules()
  }, [])

  const handleSubmit = async (event) => {
    event.preventDefault()
    try {
      if (editingId) {
        await api.put(`/api/rules/${editingId}`, form)
      } else {
        await api.post('/api/rules/', form)
      }
      setForm(initialForm)
      setEditingId(null)
      loadRules()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Enregistrement de la regle impossible')
    }
  }

  const handleEdit = (rule) => {
    setEditingId(rule.id)
    setForm({
      name: rule.name,
      machine_type: rule.machine_type,
      metric: rule.metric,
      operator: rule.operator,
      threshold: rule.threshold,
      duration_seconds: rule.duration_seconds,
      severity: rule.severity,
      confidence: rule.confidence,
      is_active: rule.is_active,
    })
  }

  const handleToggle = async (ruleId) => {
    try {
      await api.post(`/api/rules/${ruleId}/toggle`)
      loadRules()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Activation impossible')
    }
  }

  const handleSimulation = async (ruleId) => {
    try {
      const response = await api.get(`/api/rules/${ruleId}/simulate`)
      setSimulation(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Simulation impossible')
    }
  }

  const handleVersions = async (rule) => {
    try {
      const response = await api.get(`/api/rules/${rule.id}/versions`)
      setVersions(response.data)
      setVersionsTitle(rule.name)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement des versions impossible')
    }
  }

  return (
    <Stack spacing={3}>
      {error && <Alert severity="error">{error}</Alert>}

      <Paper sx={{ p: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>
          Regles metier
        </Typography>
        <Box component="form" onSubmit={handleSubmit} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(4, 1fr)' }, gap: 2 }}>
          <TextField label="Nom" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          <TextField select label="Type machine" value={form.machine_type} onChange={(event) => setForm({ ...form, machine_type: event.target.value })}>
            {machineTypes.map((type) => (
              <MenuItem key={type} value={type}>{type}</MenuItem>
            ))}
          </TextField>
          <TextField select label="Metrique" value={form.metric} onChange={(event) => setForm({ ...form, metric: event.target.value })}>
            {metrics.map((metric) => (
              <MenuItem key={metric} value={metric}>{metric}</MenuItem>
            ))}
          </TextField>
          <TextField select label="Operateur" value={form.operator} onChange={(event) => setForm({ ...form, operator: event.target.value })}>
            {operators.map((operator) => (
              <MenuItem key={operator} value={operator}>{operator}</MenuItem>
            ))}
          </TextField>
          <TextField label="Seuil" type="number" value={form.threshold} onChange={(event) => setForm({ ...form, threshold: Number(event.target.value) })} />
          <TextField
            label="Duree (s)"
            type="number"
            value={form.duration_seconds}
            onChange={(event) => setForm({ ...form, duration_seconds: Number(event.target.value) })}
          />
          <TextField select label="Severite" value={form.severity} onChange={(event) => setForm({ ...form, severity: event.target.value })}>
            {severities.map((severity) => (
              <MenuItem key={severity} value={severity}>{severity}</MenuItem>
            ))}
          </TextField>
          <TextField
            label="Confiance"
            type="number"
            inputProps={{ min: 0, max: 1, step: 0.05 }}
            value={form.confidence}
            onChange={(event) => setForm({ ...form, confidence: Number(event.target.value) })}
          />
          <Stack direction="row" spacing={1} sx={{ gridColumn: { xs: '1 / -1', md: 'span 4' } }}>
            <Button type="submit" variant="contained" disabled={!canManageRules}>
              {editingId ? 'Mettre a jour' : 'Ajouter'}
            </Button>
            {editingId && (
              <Button variant="outlined" onClick={() => { setEditingId(null); setForm(initialForm) }}>
                Annuler
              </Button>
            )}
          </Stack>
        </Box>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Catalogue des regles</Typography>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Nom</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Condition</TableCell>
              <TableCell>Severite</TableCell>
              <TableCell>Version</TableCell>
              <TableCell>Etat</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rules.map((rule) => (
              <TableRow key={rule.id}>
                <TableCell>{rule.name}</TableCell>
                <TableCell>{rule.machine_type}</TableCell>
                <TableCell>{rule.metric} {rule.operator} {rule.threshold}</TableCell>
                <TableCell>{rule.severity}</TableCell>
                <TableCell>{rule.version}</TableCell>
                <TableCell>{rule.is_active ? 'Active' : 'Inactive'}</TableCell>
                <TableCell align="right">
                  <Stack direction="row" spacing={1} justifyContent="flex-end" flexWrap="wrap">
                    <Button size="small" variant="outlined" onClick={() => handleSimulation(rule.id)}>
                      Tester
                    </Button>
                    <Button size="small" variant="outlined" onClick={() => handleVersions(rule)}>
                      Versions
                    </Button>
                    {canManageRules && (
                      <>
                        <Button size="small" variant="outlined" onClick={() => handleEdit(rule)}>
                          Editer
                        </Button>
                        <Button size="small" variant="outlined" onClick={() => handleToggle(rule.id)}>
                          {rule.is_active ? 'Desactiver' : 'Activer'}
                        </Button>
                      </>
                    )}
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Dialog open={Boolean(simulation)} onClose={() => setSimulation(null)} fullWidth maxWidth="md">
        <DialogTitle>Simulation de regle</DialogTitle>
        <DialogContent>
          {simulation && (
            <Stack spacing={2}>
              <Typography>
                Enregistrements analyses: {simulation.total_records} • Correspondances: {simulation.matched_records} • Taux: {Math.round(simulation.match_rate * 100)}%
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Capteur</TableCell>
                    <TableCell>Machine</TableCell>
                    <TableCell>Date</TableCell>
                    <TableCell>Valeur</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {simulation.latest_matches.map((match) => (
                    <TableRow key={match.sensor_id}>
                      <TableCell>{match.sensor_id}</TableCell>
                      <TableCell>{match.machine_id}</TableCell>
                      <TableCell>{new Date(match.timestamp).toLocaleString()}</TableCell>
                      <TableCell>{match.metric_value}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Stack>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={versions.length > 0} onClose={() => setVersions([])} fullWidth maxWidth="md">
        <DialogTitle>Historique des versions • {versionsTitle}</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            {versions.map((version) => (
              <Paper key={version.id} variant="outlined" sx={{ p: 2 }}>
                <Typography sx={{ fontWeight: 700 }}>
                  Version {version.version} • {new Date(version.changed_at).toLocaleString()}
                </Typography>
                <Typography component="pre" sx={{ whiteSpace: 'pre-wrap', fontSize: 13, mb: 0 }}>
                  {version.snapshot}
                </Typography>
              </Paper>
            ))}
          </Stack>
        </DialogContent>
      </Dialog>
    </Stack>
  )
}
