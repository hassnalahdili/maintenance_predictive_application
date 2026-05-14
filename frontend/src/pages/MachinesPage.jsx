import EngineeringRoundedIcon from '@mui/icons-material/EngineeringRounded'
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded'
import PictureAsPdfRoundedIcon from '@mui/icons-material/PictureAsPdfRounded'
import PrecisionManufacturingRoundedIcon from '@mui/icons-material/PrecisionManufacturingRounded'
import SensorsRoundedIcon from '@mui/icons-material/SensorsRounded'
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
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
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import { downloadBlob } from '../services/downloads'

const machineTypes = ['moteur', 'pompe', 'convoyeur', 'compresseur', 'ventilateur', 'generateur', 'broyeur', 'four']

const initialForm = {
  name: '',
  machine_type: 'moteur',
  asset_node_id: '',
  site: '',
  zone: '',
  line: '',
  component: '',
  status: 'healthy',
  notes: '',
}

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

export default function MachinesPage() {
  const { user } = useAuth()
  const [machines, setMachines] = useState([])
  const [assetNodes, setAssetNodes] = useState([])
  const [form, setForm] = useState(initialForm)
  const [editingId, setEditingId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(6)

  const loadPage = async () => {
    try {
      const [machinesResponse, assetsResponse] = await Promise.all([
        api.get('/api/machines/'),
        api.get('/api/assets/nodes'),
      ])
      setMachines(machinesResponse.data)
      setAssetNodes(assetsResponse.data)
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement des machines impossible')
    }
  }

  useEffect(() => {
    loadPage()
  }, [])

  const resetForm = () => {
    setForm(initialForm)
    setEditingId(null)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const payload = {
      ...form,
      asset_node_id: form.asset_node_id ? Number(form.asset_node_id) : null,
    }
    try {
      if (editingId) {
        await api.put(`/api/machines/${editingId}`, payload)
      } else {
        await api.post('/api/machines/', payload)
      }
      resetForm()
      loadPage()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Enregistrement impossible')
    }
  }

  const handleEdit = (machine) => {
    setEditingId(machine.id)
    setForm({
      name: machine.name,
      machine_type: machine.machine_type,
      asset_node_id: machine.asset_node_id || '',
      site: machine.site || '',
      zone: machine.zone || '',
      line: machine.line || '',
      component: machine.component || '',
      status: machine.status,
      notes: machine.notes || '',
    })
  }

  const handleDelete = async (machineId) => {
    if (!window.confirm('Supprimer logiquement cette machine ?')) {
      return
    }
    try {
      await api.delete(`/api/machines/${machineId}`)
      loadPage()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Suppression impossible')
    }
  }

  const handleDetails = async (machineId) => {
    try {
      const response = await api.get(`/api/machines/${machineId}`)
      setDetail(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement du detail impossible')
    }
  }

  const handleSimulate = async (machineId) => {
    try {
      await api.post(`/api/predictions/simulate/${machineId}?drift=true&persist=true`)
      if (detail?.id === machineId) {
        handleDetails(machineId)
      }
      loadPage()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Simulation impossible')
    }
  }

  const handleExportMachineReport = async (machineId) => {
    await downloadBlob(`/api/exports/machines/${machineId}.pdf`, `machine_${machineId}.pdf`)
  }

  const paginatedMachines = machines.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
  const canManageMachines = ['admin', 'technicien', 'expert'].includes(user?.role)
  const healthyMachines = machines.filter((machine) => machine.status === 'healthy').length
  const criticalMachines = machines.filter((machine) => ['critical', 'high'].includes(machine.status)).length
  const assignedMachines = machines.filter((machine) => machine.asset_path).length

  const selectedAssetHelper = useMemo(
    () => assetNodes.find((node) => node.id === Number(form.asset_node_id))?.path || null,
    [assetNodes, form.asset_node_id],
  )

  return (
    <Stack spacing={3}>
      {error && <Alert severity="error">{error}</Alert>}

      <Paper
        sx={{
          p: 3,
          borderRadius: 5,
          background: 'linear-gradient(135deg, #0f172a 0%, #1d4ed8 45%, #0ea5e9 100%)',
          color: '#fff',
        }}
      >
        <Stack spacing={1.2}>
          <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: '-0.04em' }}>
            Gestion des machines
          </Typography>
          
          <Button
            variant="contained"
            startIcon={<DownloadRoundedIcon />}
            onClick={() => downloadBlob('/api/exports/machines.csv', 'machines.csv')}
            sx={{ alignSelf: 'flex-start', borderRadius: 999, bgcolor: '#fff', color: '#0f172a' }}
          >
            Export CSV
          </Button>
        </Stack>
      </Paper>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
          <SummaryCard
            label="Parc total"
            value={machines.length}
            helper="Nombre total de machines actives visibles dans l'application."
            accent="#1d4ed8"
            icon={<PrecisionManufacturingRoundedIcon fontSize="small" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
          <SummaryCard
            label="Machines rattachees"
            value={assignedMachines}
            helper="Machines deja reliees a un noeud hiérarchique."
            accent="#0f766e"
            icon={<EngineeringRoundedIcon fontSize="small" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
          <SummaryCard
            label="Etat sain"
            value={healthyMachines}
            helper="Machines declarees en etat healthy."
            accent="#059669"
            icon={<SensorsRoundedIcon fontSize="small" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
          <SummaryCard
            label="Sous attention"
            value={criticalMachines}
            helper="Machines marquees high ou critical au niveau du statut."
            accent="#ea580c"
            icon={<WarningAmberRoundedIcon fontSize="small" />}
          />
        </Grid>
      </Grid>

      <Stack spacing={2}>
        <Paper sx={{ p: 2.5, borderRadius: 4 }}>
          <Stack spacing={2}>
            <Stack spacing={0.8}>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                {editingId ? 'Mettre a jour une machine' : 'Ajouter une machine'}
              </Typography>
              
            </Stack>

            <Box component="form" onSubmit={handleSubmit}>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6, xl: 3 }}>
                  <TextField
                    label="Nom"
                    value={form.name}
                    onChange={(event) => setForm({ ...form, name: event.target.value })}
                    fullWidth
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6, xl: 3 }}>
                  <TextField
                    select
                    label="Type"
                    value={form.machine_type}
                    onChange={(event) => setForm({ ...form, machine_type: event.target.value })}
                    fullWidth
                  >
                    {machineTypes.map((type) => (
                      <MenuItem key={type} value={type}>
                        {type}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid size={{ xs: 12, xl: 6 }}>
                  <TextField
                    select
                    label="Noeud hierarchique"
                    value={form.asset_node_id}
                    onChange={(event) => setForm({ ...form, asset_node_id: event.target.value })}
                    helperText={
                      selectedAssetHelper || "Choisissez un noeud de hiérarchie. Les champs site/zone/ligne restent en mode compatibilite."
                    }
                    fullWidth
                  >
                    <MenuItem value="">Aucun rattachement</MenuItem>
                    {assetNodes.map((node) => (
                      <MenuItem key={node.id} value={node.id}>
                        {node.path || node.name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid size={{ xs: 12, md: 6, xl: 3 }}>
                  <TextField label="Site" value={form.site} onChange={(event) => setForm({ ...form, site: event.target.value })} fullWidth />
                </Grid>
                <Grid size={{ xs: 12, md: 6, xl: 3 }}>
                  <TextField label="Zone" value={form.zone} onChange={(event) => setForm({ ...form, zone: event.target.value })} fullWidth />
                </Grid>
                <Grid size={{ xs: 12, md: 6, xl: 3 }}>
                  <TextField label="Ligne" value={form.line} onChange={(event) => setForm({ ...form, line: event.target.value })} fullWidth />
                </Grid>
                <Grid size={{ xs: 12, md: 6, xl: 3 }}>
                  <TextField
                    label="Composant"
                    value={form.component}
                    onChange={(event) => setForm({ ...form, component: event.target.value })}
                    fullWidth
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6, xl: 3 }}>
                  <TextField label="Statut" value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })} fullWidth />
                </Grid>
                <Grid size={{ xs: 12, xl: 9 }}>
                  <TextField
                    label="Notes"
                    value={form.notes}
                    onChange={(event) => setForm({ ...form, notes: event.target.value })}
                    multiline
                    minRows={2}
                    fullWidth
                  />
                </Grid>
                <Grid size={12}>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    <Button type="submit" variant="contained" disabled={!canManageMachines} sx={{ borderRadius: 999 }}>
                      {editingId ? 'Mettre a jour' : 'Ajouter'}
                    </Button>
                    {editingId && (
                      <Button onClick={resetForm} variant="outlined" sx={{ borderRadius: 999 }}>
                        Annuler
                      </Button>
                    )}
                  </Stack>
                </Grid>
              </Grid>
            </Box>
          </Stack>
        </Paper>

        <Paper sx={{ p: 2.5, borderRadius: 4 }}>
          <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
            Parc machines
          </Typography>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Nom</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Hierarchie</TableCell>
                <TableCell>Statut</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedMachines.map((machine) => (
                <TableRow key={machine.id}>
                  <TableCell>{machine.id}</TableCell>
                  <TableCell>{machine.name}</TableCell>
                  <TableCell>{machine.machine_type}</TableCell>
                  <TableCell>{machine.asset_path || machine.site || '-'}</TableCell>
                  <TableCell>
                    <Chip label={machine.status} size="small" />
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={1} justifyContent="flex-end" flexWrap="wrap">
                      <Button size="small" variant="outlined" onClick={() => handleDetails(machine.id)} sx={{ borderRadius: 999 }}>
                        Detail
                      </Button>
                      <Button size="small" variant="outlined" onClick={() => handleSimulate(machine.id)} sx={{ borderRadius: 999 }}>
                        Simuler
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<PictureAsPdfRoundedIcon fontSize="small" />}
                        onClick={() => handleExportMachineReport(machine.id)}
                        sx={{ borderRadius: 999 }}
                      >
                        PDF
                      </Button>
                      {canManageMachines && (
                        <Button size="small" variant="outlined" onClick={() => handleEdit(machine)} sx={{ borderRadius: 999 }}>
                          Editer
                        </Button>
                      )}
                      {user?.role === 'admin' && (
                        <Button size="small" color="error" variant="outlined" onClick={() => handleDelete(machine.id)} sx={{ borderRadius: 999 }}>
                          Supprimer
                        </Button>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            component="div"
            count={machines.length}
            page={page}
            onPageChange={(_, nextPage) => setPage(nextPage)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(event) => {
              setRowsPerPage(Number(event.target.value))
              setPage(0)
            }}
            rowsPerPageOptions={[6, 12, 24]}
          />
        </Paper>
      </Stack>

      <Dialog open={Boolean(detail)} onClose={() => setDetail(null)} fullWidth maxWidth="lg">
        <DialogTitle>Detail machine</DialogTitle>
        <DialogContent>
          {detail && (
            <Stack spacing={3}>
              <Typography variant="h6">
                {detail.name} • {detail.machine_type} • {detail.asset_path || detail.site || 'Sans site'}
              </Typography>

              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 700 }}>
                  Hierarchie industrielle
                </Typography>
                <Typography color="text.secondary">
                  Site: {detail.site || '-'} • Zone: {detail.zone || '-'} • Ligne: {detail.line || '-'} • Composant: {detail.component || '-'}
                </Typography>
              </Paper>

              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 700 }}>
                  Historique capteurs
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell>Temperature</TableCell>
                      <TableCell>Vibrations</TableCell>
                      <TableCell>Pression</TableCell>
                      <TableCell>RPM</TableCell>
                      <TableCell>Courant</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {detail.sensor_history.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{new Date(row.timestamp).toLocaleString()}</TableCell>
                        <TableCell>{row.temperature}</TableCell>
                        <TableCell>
                          {row.vibration_x}/{row.vibration_y}/{row.vibration_z}
                        </TableCell>
                        <TableCell>{row.pressure}</TableCell>
                        <TableCell>{row.rpm}</TableCell>
                        <TableCell>{row.current}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Paper>

              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 700 }}>
                  Historique predictions
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell>Risque</TableCell>
                      <TableCell>Probabilite</TableCell>
                      <TableCell>RUL</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {detail.prediction_history.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{new Date(row.timestamp).toLocaleString()}</TableCell>
                        <TableCell>{row.alert_level}</TableCell>
                        <TableCell>{Math.round(row.failure_probability * 100)}%</TableCell>
                        <TableCell>{row.remaining_useful_life_days} jours</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Paper>

              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 700 }}>
                  Historique alertes
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell>Niveau</TableCell>
                      <TableCell>Statut</TableCell>
                      <TableCell>Message</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {detail.alert_history.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{new Date(row.created_at).toLocaleString()}</TableCell>
                        <TableCell>{row.level}</TableCell>
                        <TableCell>{row.status}</TableCell>
                        <TableCell>{row.message}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Paper>

              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 700 }}>
                  Interventions
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Ouverture</TableCell>
                      <TableCell>Statut</TableCell>
                      <TableCell>Label terrain</TableCell>
                      <TableCell>Work order</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {detail.interventions.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{new Date(row.opened_at).toLocaleString()}</TableCell>
                        <TableCell>{row.status}</TableCell>
                        <TableCell>{row.outcome_label}</TableCell>
                        <TableCell>{row.work_order || '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Paper>
            </Stack>
          )}
        </DialogContent>
      </Dialog>
    </Stack>
  )
}
