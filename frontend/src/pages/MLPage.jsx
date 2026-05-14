import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid2 as Grid,
  LinearProgress,
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
import api from '../services/api'

function MetricCell({ benchmark }) {
  const winner = benchmark.results?.[0]
  if (!winner) {
    return <TableCell>-</TableCell>
  }
  return <TableCell>{winner[benchmark.primary_metric]}</TableCell>
}

function FeatureImportanceBars({ items }) {
  if (!items?.length) {
    return <Typography color="text.secondary">Aucune importance disponible.</Typography>
  }
  return (
    <Stack spacing={1.2} sx={{ mt: 2 }}>
      {items.slice(0, 8).map((item) => (
        <Stack key={item.feature} spacing={0.4}>
          <Stack direction="row" justifyContent="space-between">
            <Typography variant="body2">{item.feature}</Typography>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {item.normalized_importance}
            </Typography>
          </Stack>
          <LinearProgress
            variant="determinate"
            value={Math.min(100, Math.round((item.normalized_importance || 0) * 100))}
            sx={{ height: 8, borderRadius: 999 }}
          />
        </Stack>
      ))}
    </Stack>
  )
}

function CalibrationVisual({ bins }) {
  if (!bins?.length) {
    return <Typography color="text.secondary">Aucune calibration disponible.</Typography>
  }
  return (
    <Grid container spacing={1.5}>
      {bins.map((item) => {
        const confidence = Number(item.average_confidence || 0)
        const observed = Number(item.observed_frequency || 0)
        return (
          <Grid size={{ xs: 12, md: 6, xl: 3 }} key={item.bin_label}>
            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 3 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                {item.bin_label} • n={item.count}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Confiance
              </Typography>
              <LinearProgress variant="determinate" value={Math.round(confidence * 100)} sx={{ height: 8, borderRadius: 999, mb: 1 }} />
              <Typography variant="caption" color="text.secondary">
                Frequence observee
              </Typography>
              <LinearProgress color="success" variant="determinate" value={Math.round(observed * 100)} sx={{ height: 8, borderRadius: 999 }} />
            </Paper>
          </Grid>
        )
      })}
    </Grid>
  )
}

function BenchmarkCards({ benchmarks }) {
  const winners = benchmarks?.filter((item) => item.winner) || []
  if (winners.length === 0) {
    return null
  }
  return (
    <Grid container spacing={2}>
      {winners.slice(0, 4).map((benchmark) => (
        <Grid size={{ xs: 12, md: 6, xl: 3 }} key={`${benchmark.dataset_id}-${benchmark.task}-card`}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                {benchmark.display_name}
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                {benchmark.winner}
              </Typography>
              <Chip label={`${benchmark.task} • ${benchmark.primary_metric}`} size="small" sx={{ mt: 1 }} />
              <Typography variant="body2" sx={{ mt: 1.5 }}>
                Meilleure valeur: {benchmark.results?.[0]?.[benchmark.primary_metric] ?? '-'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  )
}

const initialReplayForm = {
  source_id: '',
  machine_id: '',
  steps: 5,
}

export default function MLPage() {
  const [overview, setOverview] = useState(null)
  const [diagnostics, setDiagnostics] = useState(null)
  const [machines, setMachines] = useState([])
  const [replaySources, setReplaySources] = useState([])
  const [replayForm, setReplayForm] = useState(initialReplayForm)
  const [replayResult, setReplayResult] = useState(null)
  const [explanationMachineId, setExplanationMachineId] = useState('')
  const [explanation, setExplanation] = useState(null)
  const [error, setError] = useState('')
  const [loadingOverview, setLoadingOverview] = useState(false)
  const [loadingReplay, setLoadingReplay] = useState(false)
  const [loadingExplanation, setLoadingExplanation] = useState(false)
  const [autoReplay, setAutoReplay] = useState(false)

  const loadOverview = async (refresh = false) => {
    setLoadingOverview(true)
    try {
      const response = await api.get('/api/ml/overview', { params: { refresh } })
      setOverview(response.data)
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement des resultats ML impossible')
    } finally {
      setLoadingOverview(false)
    }
  }

  const loadDiagnostics = async () => {
    try {
      const response = await api.get('/api/ml/model-diagnostics')
      setDiagnostics(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement des diagnostics modele impossible')
    }
  }

  const loadReplayContext = async () => {
    try {
      const [sourcesResponse, machinesResponse] = await Promise.all([
        api.get('/api/ml/replay/sources'),
        api.get('/api/machines/'),
      ])
      setReplaySources(sourcesResponse.data)
      setMachines(machinesResponse.data)
      if (!replayForm.source_id && sourcesResponse.data.length > 0) {
        const firstSource = sourcesResponse.data[0]
        const candidateMachine = machinesResponse.data.find((item) => item.machine_type === firstSource.machine_type)
        setReplayForm({
          source_id: firstSource.source_id,
          machine_id: candidateMachine?.id || '',
          steps: 5,
        })
      }
      if (!explanationMachineId && machinesResponse.data.length > 0) {
        setExplanationMachineId(machinesResponse.data[0].id)
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement des sources de rejeu impossible')
    }
  }

  useEffect(() => {
    loadOverview(false)
    loadDiagnostics()
    loadReplayContext()
  }, [])

  const selectedSource = replaySources.find((item) => item.source_id === replayForm.source_id) || null
  const compatibleMachines = useMemo(() => {
    if (!selectedSource) {
      return machines
    }
    return machines.filter((machine) => machine.machine_type === selectedSource.machine_type)
  }, [machines, selectedSource])

  useEffect(() => {
    if (!selectedSource) {
      return
    }
    if (!compatibleMachines.some((machine) => machine.id === Number(replayForm.machine_id))) {
      setReplayForm((current) => ({
        ...current,
        machine_id: compatibleMachines[0]?.id || '',
      }))
    }
  }, [selectedSource, compatibleMachines, replayForm.machine_id])

  const executeReplay = async (stepCount = Number(replayForm.steps), reset = false) => {
    if (!replayForm.source_id || !replayForm.machine_id) {
      return
    }
    setLoadingReplay(true)
    try {
      const response = await api.post('/api/ml/replay/step', {
        source_id: replayForm.source_id,
        machine_id: Number(replayForm.machine_id),
        steps: stepCount,
        reset,
      })
      setReplayResult(response.data)
      setError('')
      const sourcesResponse = await api.get('/api/ml/replay/sources')
      setReplaySources(sourcesResponse.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Rejeu impossible')
      setAutoReplay(false)
    } finally {
      setLoadingReplay(false)
    }
  }

  const handleResetReplay = async () => {
    if (!replayForm.source_id) {
      return
    }
    setLoadingReplay(true)
    try {
      await api.post(`/api/ml/replay/reset/${replayForm.source_id}`)
      setReplayResult(null)
      const sourcesResponse = await api.get('/api/ml/replay/sources')
      setReplaySources(sourcesResponse.data)
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Reset du rejeu impossible')
    } finally {
      setLoadingReplay(false)
    }
  }

  useEffect(() => {
    if (!autoReplay || !replayForm.source_id || !replayForm.machine_id) {
      return undefined
    }
    const interval = window.setInterval(() => {
      if (!loadingReplay) {
        executeReplay(1, false)
      }
    }, 3000)
    return () => window.clearInterval(interval)
  }, [autoReplay, replayForm.source_id, replayForm.machine_id, loadingReplay])

  const loadExplanation = async () => {
    if (!explanationMachineId) {
      return
    }
    setLoadingExplanation(true)
    try {
      const response = await api.get(`/api/ml/explain/machines/${explanationMachineId}`)
      setExplanation(response.data)
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Explication indisponible')
    } finally {
      setLoadingExplanation(false)
    }
  }

  return (
    <Stack spacing={3}>
      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} justifyContent="space-between" alignItems={{ md: 'center' }}>
          <div>
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              Espace ML & Benchmarks
            </Typography>
            <Typography color="text.secondary">
              Catalogue des datasets detectes, calibration du modele, explicabilite, metriques metier et rejeu de vraies series temporelles.
            </Typography>
          </div>
          <Button
            variant="contained"
            onClick={() => {
              loadOverview(true)
              loadDiagnostics()
            }}
            disabled={loadingOverview}
          >
            {loadingOverview ? 'Analyse...' : 'Rafraichir l analyse'}
          </Button>
        </Stack>
      </Paper>

      {error && <Alert severity="error">{error}</Alert>}

      {diagnostics && (
        <>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, lg: 4 }}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary">Modele en service</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                    {diagnostics.model_name}
                  </Typography>
                  <Chip label={diagnostics.calibration_method || 'calibration n/a'} color="primary" />
                  <Stack spacing={1.2} sx={{ mt: 2 }}>
                    <Typography variant="body2">Brier avant: {diagnostics.calibration_before?.brier ?? '-'}</Typography>
                    <Typography variant="body2">Brier apres: {diagnostics.calibration_after?.brier ?? '-'}</Typography>
                    <Typography variant="body2">ECE avant: {diagnostics.calibration_before?.ece ?? '-'}</Typography>
                    <Typography variant="body2">ECE apres: {diagnostics.calibration_after?.ece ?? '-'}</Typography>
                    <Typography variant="body2">Precision: {diagnostics.calibration_after?.precision ?? '-'}</Typography>
                    <Typography variant="body2">Recall: {diagnostics.calibration_after?.recall ?? '-'}</Typography>
                    <Typography variant="body2">F1: {diagnostics.calibration_after?.f1 ?? '-'}</Typography>
                    <Typography variant="body2">ROC AUC: {diagnostics.calibration_after?.roc_auc ?? '-'}</Typography>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, lg: 4 }}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary">Top variables globales</Typography>
                  <FeatureImportanceBars items={diagnostics.global_importance || []} />
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, lg: 4 }}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary">Metriques metier</Typography>
                  <Stack spacing={1.2} sx={{ mt: 2 }}>
                    <Typography variant="body2">Alertes totales: {diagnostics.business_metrics.total_alerts}</Typography>
                    <Typography variant="body2">Alertes actives: {diagnostics.business_metrics.active_alerts}</Typography>
                    <Typography variant="body2">Taux acquittement: {Math.round((diagnostics.business_metrics.acknowledged_rate || 0) * 100)}%</Typography>
                    <Typography variant="body2">Taux escalade: {Math.round((diagnostics.business_metrics.escalation_rate || 0) * 100)}%</Typography>
                    <Typography variant="body2">Taux fausses alertes: {Math.round((diagnostics.business_metrics.false_alert_rate || 0) * 100)}%</Typography>
                    <Typography variant="body2">Temps moyen d anticipation: {diagnostics.business_metrics.mean_lead_time_hours} h</Typography>
                    <Typography variant="body2">Downtime moyen: {diagnostics.business_metrics.mean_downtime_minutes} min</Typography>
                    <Typography variant="body2">Couverture pannes confirmees: {Math.round((diagnostics.business_metrics.failure_coverage_rate || 0) * 100)}%</Typography>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Courbe de calibration
            </Typography>
            <CalibrationVisual bins={diagnostics.calibration_bins || []} />
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Bin</TableCell>
                  <TableCell>Effectif</TableCell>
                  <TableCell>Confiance moyenne</TableCell>
                  <TableCell>Frequence observee</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(diagnostics.calibration_bins || []).map((item) => (
                  <TableRow key={item.bin_label}>
                    <TableCell>{item.bin_label}</TableCell>
                    <TableCell>{item.count}</TableCell>
                    <TableCell>{item.average_confidence}</TableCell>
                    <TableCell>{item.observed_frequency}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </>
      )}

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Expliquer la derniere prediction d une machine
        </Typography>
        <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2} alignItems={{ lg: 'flex-start' }}>
          <Stack spacing={2} sx={{ flex: 1 }}>
            <TextField
              select
              label="Machine"
              value={explanationMachineId}
              onChange={(event) => setExplanationMachineId(event.target.value)}
              fullWidth
            >
              {machines.map((machine) => (
                <MenuItem key={machine.id} value={machine.id}>
                  {machine.name} • {machine.machine_type}
                </MenuItem>
              ))}
            </TextField>
            <Button variant="contained" onClick={loadExplanation} disabled={!explanationMachineId || loadingExplanation}>
              {loadingExplanation ? 'Analyse...' : 'Expliquer la prediction'}
            </Button>
          </Stack>

          <Paper variant="outlined" sx={{ p: 2, flex: 2, minWidth: 320 }}>
            {!explanation && (
              <Typography color="text.secondary">
                Selectionnez une machine pour afficher l explication locale de sa derniere prediction.
              </Typography>
            )}
            {explanation && (
              <Stack spacing={2}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  {explanation.machine_name} • risque {explanation.alert_level} • probabilite {Math.round((explanation.failure_probability || 0) * 100)}%
                </Typography>
                <Typography color="text.secondary">
                  Regles actives: {explanation.active_rules.length ? explanation.active_rules.join(', ') : 'aucune'}
                </Typography>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>Facteurs qui augmentent le risque</Typography>
                    <Stack spacing={1}>
                      {explanation.top_positive.map((item) => (
                        <Typography key={item.feature} variant="body2">
                          {item.feature}: {item.value} vs baseline {item.baseline} • contribution {item.contribution}
                        </Typography>
                      ))}
                    </Stack>
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>Facteurs qui reduisent le risque</Typography>
                    <Stack spacing={1}>
                      {explanation.top_negative.map((item) => (
                        <Typography key={item.feature} variant="body2">
                          {item.feature}: {item.value} vs baseline {item.baseline} • contribution {item.contribution}
                        </Typography>
                      ))}
                    </Stack>
                  </Grid>
                </Grid>
              </Stack>
            )}
          </Paper>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Rejeu temps reel a partir des datasets reels
        </Typography>
        <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2} alignItems={{ lg: 'flex-start' }}>
          <Stack spacing={2} sx={{ flex: 1 }}>
            <TextField
              select
              label="Source de rejeu"
              value={replayForm.source_id}
              onChange={(event) => setReplayForm({ ...replayForm, source_id: event.target.value })}
              fullWidth
            >
              {replaySources.map((source) => (
                <MenuItem key={source.source_id} value={source.source_id}>
                  {source.display_name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Machine cible"
              value={replayForm.machine_id}
              onChange={(event) => setReplayForm({ ...replayForm, machine_id: event.target.value })}
              fullWidth
            >
              {compatibleMachines.map((machine) => (
                <MenuItem key={machine.id} value={machine.id}>
                  {machine.name} • {machine.machine_type}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Points a injecter"
              type="number"
              value={replayForm.steps}
              inputProps={{ min: 1, max: 50 }}
              onChange={(event) => setReplayForm({ ...replayForm, steps: Number(event.target.value) })}
            />

            <Stack direction={{ xs: 'column', md: 'row' }} spacing={1}>
              <Button variant="contained" onClick={() => executeReplay()} disabled={loadingReplay || !replayForm.machine_id}>
                {loadingReplay ? 'Injection...' : 'Injecter maintenant'}
              </Button>
              <Button variant={autoReplay ? 'contained' : 'outlined'} onClick={() => setAutoReplay((current) => !current)} disabled={!replayForm.machine_id}>
                {autoReplay ? 'Arreter auto-replay' : 'Lancer auto-replay'}
              </Button>
              <Button variant="outlined" onClick={handleResetReplay} disabled={loadingReplay || !replayForm.source_id}>
                Reinitialiser la source
              </Button>
            </Stack>

            {selectedSource && (
              <Typography color="text.secondary">
                {selectedSource.description} • progression {selectedSource.cursor}/{selectedSource.row_count}
              </Typography>
            )}

            {replayResult && (
              <Alert severity="success">
                {replayResult.injected_rows} points injectes dans {replayResult.machine_name}. Dernier risque: {replayResult.latest_prediction?.alert_level || '-'} • probabilite {Math.round((replayResult.latest_prediction?.failure_probability || 0) * 100)}%
              </Alert>
            )}
          </Stack>

          <Paper variant="outlined" sx={{ p: 2, flex: 1, minWidth: 320 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
              Sources disponibles
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Source</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Progression</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {replaySources.map((source) => (
                  <TableRow key={source.source_id}>
                    <TableCell>{source.display_name}</TableCell>
                    <TableCell>{source.machine_type}</TableCell>
                    <TableCell>{source.cursor}/{source.row_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </Stack>
      </Paper>

      {overview && (
        <>
          <Grid container spacing={2}>
            {[
              ['Datasets detectes', overview.summary.detected_datasets],
              ['Datasets prets', overview.summary.ready_datasets],
              ['Datasets partiels', overview.summary.partial_datasets],
              ['Benchmarks', overview.summary.benchmark_runs],
            ].map(([label, value]) => (
              <Grid size={{ xs: 12, md: 3 }} key={label}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary">{label}</Typography>
                    <Typography variant="h4" sx={{ fontWeight: 700 }}>
                      {value}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Catalogue des datasets
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Dataset</TableCell>
                  <TableCell>Machines</TableCell>
                  <TableCell>Taches</TableCell>
                  <TableCell>Statut</TableCell>
                  <TableCell>Note</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {overview.catalog.map((item) => (
                  <TableRow key={item.dataset_id}>
                    <TableCell>{item.display_name}</TableCell>
                    <TableCell>{item.machine_types.join(', ')}</TableCell>
                    <TableCell>{item.tasks.join(', ')}</TableCell>
                    <TableCell>{item.status}</TableCell>
                    <TableCell>{item.note}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Resultats benchmarks
            </Typography>
            <BenchmarkCards benchmarks={overview.benchmarks} />
            <Box sx={{ height: 16 }} />
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Dataset</TableCell>
                  <TableCell>Tache</TableCell>
                  <TableCell>Modele gagnant</TableCell>
                  <TableCell>Metrique</TableCell>
                  <TableCell>Valeur</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {overview.benchmarks.map((benchmark) => (
                  <TableRow key={`${benchmark.dataset_id}-${benchmark.task}`}>
                    <TableCell>{benchmark.display_name}</TableCell>
                    <TableCell>{benchmark.task}</TableCell>
                    <TableCell>{benchmark.winner || '-'}</TableCell>
                    <TableCell>{benchmark.primary_metric}</TableCell>
                    <MetricCell benchmark={benchmark} />
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Recommandations suivantes
            </Typography>
            <Stack spacing={1}>
              {overview.recommendations.map((item) => (
                <Typography key={item}>• {item}</Typography>
              ))}
            </Stack>
          </Paper>
        </>
      )}
    </Stack>
  )
}
