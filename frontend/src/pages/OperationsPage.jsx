import AccountTreeRoundedIcon from '@mui/icons-material/AccountTreeRounded'
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded'
import BuildCircleRoundedIcon from '@mui/icons-material/BuildCircleRounded'
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded'
import EditRoundedIcon from '@mui/icons-material/EditRounded'
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded'
import PsychologyAltRoundedIcon from '@mui/icons-material/PsychologyAltRounded'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded'
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControlLabel,
  Grid2 as Grid,
  MenuItem,
  Paper,
  Stack,
  Switch,
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

const initialInterventionForm = {
  machine_id: '',
  technician_id: '',
  work_order: '',
  category: 'inspection',
  priority: 'medium',
  status: 'open',
  outcome_label: 'under_analysis',
  downtime_minutes: 0,
  planned_at: '',
  parts_used: '',
  estimated_cost: 0,
  root_cause: '',
  action_taken: '',
}

const initialJobForm = {
  machine_id: '',
  mode: 'simulator',
  source_id: '',
  interval_seconds: 5,
  replay_steps: 1,
  drift: false,
  auto_restart: true,
}

const initialRetrainForm = {
  horizon_hours: 72,
  minimum_samples: 30,
}

const initialAssetForm = {
  name: '',
  node_type: 'site',
  parent_id: '',
}

const sectionOptions = [
  { key: 'overview', label: 'Vue rapide', icon: <InsightsRoundedIcon fontSize="small" /> },
  { key: 'hierarchy', label: 'Hierarchie', icon: <AccountTreeRoundedIcon fontSize="small" /> },
  { key: 'interventions', label: 'Interventions', icon: <BuildCircleRoundedIcon fontSize="small" /> },
  { key: 'ingestion', label: 'Ingestion', icon: <AutorenewRoundedIcon fontSize="small" /> },
  { key: 'ml', label: 'ML terrain', icon: <PsychologyAltRoundedIcon fontSize="small" /> },
]

function renderAssetTree(nodes, depth = 0) {
  return nodes.map((node) => (
    <Stack key={node.id} spacing={1} sx={{ pl: depth * 2 }}>
      <Typography variant="body2" sx={{ fontWeight: depth === 0 ? 800 : 500 }}>
        {node.node_type} • {node.name}
      </Typography>
      {node.children?.length > 0 && renderAssetTree(node.children, depth + 1)}
    </Stack>
  ))
}

function countAssetNodes(nodes) {
  return nodes.reduce((total, node) => total + 1 + countAssetNodes(node.children || []), 0)
}

function SectionSelector({ activeSection, onChange }) {
  return (
    <Paper sx={{ p: 1, borderRadius: 4 }}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} flexWrap="wrap">
        {sectionOptions.map((section) => {
          const selected = section.key === activeSection
          return (
            <Button
              key={section.key}
              onClick={() => onChange(section.key)}
              startIcon={section.icon}
              variant={selected ? 'contained' : 'text'}
              sx={{
                justifyContent: 'flex-start',
                borderRadius: 999,
                px: 2,
                background: selected ? 'linear-gradient(135deg, #0f766e 0%, #0f172a 100%)' : 'transparent',
                color: selected ? '#fff' : '#0f172a',
              }}
            >
              {section.label}
            </Button>
          )
        })}
      </Stack>
    </Paper>
  )
}

function SummaryCard({ label, value, helper, actionLabel, onAction, accent }) {
  return (
    <Card
      sx={{
        height: '100%',
        borderRadius: 4,
        background: 'rgba(255,255,255,0.96)',
        border: '1px solid rgba(148, 163, 184, 0.14)',
      }}
    >
      <CardContent>
        <Stack spacing={1.2}>
          <Typography color="text.secondary">{label}</Typography>
          <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: '-0.04em', color: accent }}>
            {value}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {helper}
          </Typography>
          {actionLabel && onAction && (
            <Button variant="outlined" onClick={onAction} sx={{ alignSelf: 'flex-start', borderRadius: 999, mt: 0.5 }}>
              {actionLabel}
            </Button>
          )}
        </Stack>
      </CardContent>
    </Card>
  )
}

function QuickOverview({ assets, assetNodes, interventions, jobs, driftReport, feedbackSummary, setActiveSection }) {
  const activeJobs = jobs.filter((job) => job.is_active).length
  const labelledInterventions = Object.values(feedbackSummary?.labels_breakdown || {}).reduce((total, value) => total + value, 0)

  return (
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
        <SummaryCard
          label="Hierarchie"
          value={assetNodes.length}
          helper="Nombre total de noeuds configurables."
          actionLabel="Gerer la hierarchie"
          onAction={() => setActiveSection('hierarchy')}
          accent="#0f766e"
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
        <SummaryCard
          label="Interventions"
          value={interventions.length}
          helper="Interventions terrain enregistrees. Utiles pour la tracabilite et les labels ML."
          actionLabel="Nouvelle intervention"
          onAction={() => setActiveSection('interventions')}
          accent="#1d4ed8"
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
        <SummaryCard
          label="Jobs d'ingestion actifs"
          value={activeJobs}
          helper={`${jobs.length} jobs definis au total pour simulateur ou rejeu de donnees reelles.`}
          actionLabel="Gerer l'ingestion"
          onAction={() => setActiveSection('ingestion')}
          accent="#ea580c"
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
        <SummaryCard
          label="ML terrain"
          value={labelledInterventions}
          helper={`Drift actuel: ${driftReport?.status || 'n/a'}. Labels exploitables pour le retraining.`}
          actionLabel="Ouvrir ML terrain"
          onAction={() => setActiveSection('ml')}
          accent="#7c3aed"
        />
      </Grid>

      <Grid size={{ xs: 12, lg: 7 }}>
        <Paper sx={{ p: 2.5, borderRadius: 4, height: '100%' }}>
          <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
            Interventions recentes
          </Typography>
          
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Machine</TableCell>
                <TableCell>Work order</TableCell>
                <TableCell>Statut</TableCell>
                <TableCell>Label terrain</TableCell>
                <TableCell>Ouverture</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {interventions.slice(0, 6).map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.machine_name}</TableCell>
                  <TableCell>{item.work_order || '-'}</TableCell>
                  <TableCell>{item.status}</TableCell>
                  <TableCell>{item.outcome_label}</TableCell>
                  <TableCell>{new Date(item.opened_at).toLocaleString()}</TableCell>
                </TableRow>
              ))}
              {interventions.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5}>
                    <Typography color="text.secondary">Aucune intervention pour le moment.</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Paper>
      </Grid>

      <Grid size={{ xs: 12, lg: 5 }}>
        <Paper sx={{ p: 2.5, borderRadius: 4, height: '100%' }}>
          <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
            Synthese exploitation
          </Typography>
         
          <Stack spacing={1.4}>
            <Chip label={`Drift des donnees: ${driftReport?.status || 'n/a'}`} sx={{ alignSelf: 'flex-start' }} />
            <Chip label={`Labels terrain: ${labelledInterventions}`} sx={{ alignSelf: 'flex-start' }} />
            <Chip label={`Interventions ouvertes: ${interventions.filter((item) => item.status === 'open').length}`} sx={{ alignSelf: 'flex-start' }} />
            <Chip label={`Jobs en erreur: ${jobs.filter((item) => item.last_error).length}`} sx={{ alignSelf: 'flex-start' }} />
            <Chip label={`Noeuds racine: ${assets.length}`} sx={{ alignSelf: 'flex-start' }} />
          </Stack>
        </Paper>
      </Grid>
    </Grid>
  )
}

function HierarchySection({
  assets,
  assetNodes,
  assetForm,
  setAssetForm,
  editingAssetId,
  setEditingAssetId,
  handleSubmitAsset,
  handleEditAsset,
  handleDeleteAsset,
}) {
  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Stack spacing={2}>
          <Stack spacing={0.8}>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              Gestion de la hierarchie
            </Typography>
            
          </Stack>

          <Stack component="form" spacing={2} onSubmit={handleSubmitAsset}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField
                  label="Nom du noeud"
                  value={assetForm.name}
                  onChange={(event) => setAssetForm({ ...assetForm, name: event.target.value })}
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField
                  label="Type de noeud"
                  value={assetForm.node_type}
                  onChange={(event) => setAssetForm({ ...assetForm, node_type: event.target.value })}
                  helperText="Exemples: site, atelier, batiment, ligne, cellule, zone, composant"
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField
                  select
                  label="Parent"
                  value={assetForm.parent_id}
                  onChange={(event) => setAssetForm({ ...assetForm, parent_id: event.target.value })}
                  fullWidth
                >
                  <MenuItem value="">Aucun parent</MenuItem>
                  {assetNodes
                    .filter((node) => node.id !== editingAssetId)
                    .map((node) => (
                      <MenuItem key={node.id} value={node.id}>
                        {node.path || node.name}
                      </MenuItem>
                    ))}
                </TextField>
              </Grid>
              <Grid size={12}>
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  <Button type="submit" variant="contained" sx={{ borderRadius: 999 }}>
                    {editingAssetId ? 'Mettre a jour' : 'Ajouter le noeud'}
                  </Button>
                  {editingAssetId && (
                    <Button
                      variant="outlined"
                      onClick={() => {
                        setEditingAssetId(null)
                        setAssetForm(initialAssetForm)
                      }}
                      sx={{ borderRadius: 999 }}
                    >
                      Annuler
                    </Button>
                  )}
                </Stack>
              </Grid>
            </Grid>
          </Stack>

          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label="1. Creez d'abord les noeuds racine de l'entreprise." />
            <Chip label="2. Ajoutez ensuite les niveaux enfants selon votre organisation." />
            <Chip label="3. Rattachez ensuite les machines a un noeud depuis la page Machines." />
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
          Arborescence actuelle
        </Typography>
        <Stack spacing={1.5}>
          {assets.length === 0 ? <Typography color="text.secondary">Aucun noeud d'actif pour le moment.</Typography> : renderAssetTree(assets)}
        </Stack>
      </Paper>

      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
          Liste des noeuds
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Nom</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Chemin</TableCell>
              <TableCell>Enfants</TableCell>
              <TableCell>Machines</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {assetNodes.map((node) => (
              <TableRow key={node.id}>
                <TableCell>{node.name}</TableCell>
                <TableCell>{node.node_type}</TableCell>
                <TableCell>{node.path || '-'}</TableCell>
                <TableCell>{node.child_count}</TableCell>
                <TableCell>{node.machine_count}</TableCell>
                <TableCell align="right">
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<EditRoundedIcon fontSize="small" />}
                      onClick={() => handleEditAsset(node)}
                      sx={{ borderRadius: 999 }}
                    >
                      Editer
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      variant="outlined"
                      startIcon={<DeleteOutlineRoundedIcon fontSize="small" />}
                      onClick={() => handleDeleteAsset(node)}
                      sx={{ borderRadius: 999 }}
                    >
                      Supprimer
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
            {assetNodes.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography color="text.secondary">Aucun noeud disponible.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>
    </Stack>
  )
}

function InterventionsSection({
  machines,
  technicians,
  interventions,
  interventionForm,
  setInterventionForm,
  handleCreateIntervention,
  loadPage,
  loading,
}) {
  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
          Nouvelle intervention terrain
        </Typography>
        <Stack component="form" spacing={2} onSubmit={handleCreateIntervention}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                select
                label="Machine"
                value={interventionForm.machine_id}
                onChange={(event) => setInterventionForm({ ...interventionForm, machine_id: event.target.value })}
                fullWidth
              >
                {machines.map((machine) => (
                  <MenuItem key={machine.id} value={machine.id}>
                    {machine.name} • {machine.asset_path || machine.site || 'Sans chemin'}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                select
                label="Technicien"
                value={interventionForm.technician_id}
                onChange={(event) => setInterventionForm({ ...interventionForm, technician_id: event.target.value })}
                fullWidth
              >
                <MenuItem value="">Non assigne</MenuItem>
                {technicians.map((technician) => (
                  <MenuItem key={technician.id} value={technician.id}>
                    {technician.full_name} • {technician.role}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                label="Work order"
                value={interventionForm.work_order}
                onChange={(event) => setInterventionForm({ ...interventionForm, work_order: event.target.value })}
                fullWidth
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                select
                label="Categorie"
                value={interventionForm.category}
                onChange={(event) => setInterventionForm({ ...interventionForm, category: event.target.value })}
                fullWidth
              >
                {['inspection', 'corrective', 'preventive', 'calibration'].map((item) => (
                  <MenuItem key={item} value={item}>
                    {item}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                select
                label="Priorite"
                value={interventionForm.priority}
                onChange={(event) => setInterventionForm({ ...interventionForm, priority: event.target.value })}
                fullWidth
              >
                {['low', 'medium', 'high', 'critical'].map((item) => (
                  <MenuItem key={item} value={item}>
                    {item}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                select
                label="Statut"
                value={interventionForm.status}
                onChange={(event) => setInterventionForm({ ...interventionForm, status: event.target.value })}
                fullWidth
              >
                {['open', 'in_progress', 'resolved', 'cancelled'].map((item) => (
                  <MenuItem key={item} value={item}>
                    {item}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                select
                label="Label terrain"
                value={interventionForm.outcome_label}
                onChange={(event) => setInterventionForm({ ...interventionForm, outcome_label: event.target.value })}
                fullWidth
              >
                {['under_analysis', 'confirmed_failure', 'false_alarm', 'preventive_maintenance', 'sensor_fault'].map((item) => (
                  <MenuItem key={item} value={item}>
                    {item}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                label="Downtime (min)"
                type="number"
                value={interventionForm.downtime_minutes}
                onChange={(event) => setInterventionForm({ ...interventionForm, downtime_minutes: event.target.value })}
                fullWidth
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                label="Date prevue"
                type="datetime-local"
                value={interventionForm.planned_at}
                onChange={(event) => setInterventionForm({ ...interventionForm, planned_at: event.target.value })}
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                label="Cout estime"
                type="number"
                value={interventionForm.estimated_cost}
                onChange={(event) => setInterventionForm({ ...interventionForm, estimated_cost: event.target.value })}
                fullWidth
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                label="Pieces utilisees"
                value={interventionForm.parts_used}
                onChange={(event) => setInterventionForm({ ...interventionForm, parts_used: event.target.value })}
                fullWidth
              />
            </Grid>
            <Grid size={12}>
              <TextField
                label="Cause racine"
                value={interventionForm.root_cause}
                onChange={(event) => setInterventionForm({ ...interventionForm, root_cause: event.target.value })}
                fullWidth
              />
            </Grid>
            <Grid size={12}>
              <TextField
                label="Action realisee"
                value={interventionForm.action_taken}
                onChange={(event) => setInterventionForm({ ...interventionForm, action_taken: event.target.value })}
                fullWidth
                multiline
                minRows={2}
              />
            </Grid>
          </Grid>
          <Stack direction="row" spacing={2}>
            <Button type="submit" variant="contained" sx={{ borderRadius: 999 }}>
              Enregistrer intervention
            </Button>
            <Button
              variant="outlined"
              startIcon={<DownloadRoundedIcon />}
              onClick={() => downloadBlob('/api/exports/interventions.csv', 'interventions.csv')}
              sx={{ borderRadius: 999 }}
            >
              Export CSV
            </Button>
            <Button variant="outlined" onClick={loadPage} disabled={loading} sx={{ borderRadius: 999 }}>
              Rafraichir
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
          Interventions recentes
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Machine</TableCell>
              <TableCell>Work order</TableCell>
              <TableCell>Priorite</TableCell>
              <TableCell>Technicien</TableCell>
              <TableCell>Statut</TableCell>
              <TableCell>Label terrain</TableCell>
              <TableCell>Cout</TableCell>
              <TableCell>Downtime</TableCell>
              <TableCell>Ouverture</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {interventions.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.machine_name}</TableCell>
                <TableCell>{item.work_order || '-'}</TableCell>
                <TableCell>{item.priority}</TableCell>
                <TableCell>{item.technician_name || '-'}</TableCell>
                <TableCell>{item.status}</TableCell>
                <TableCell>{item.outcome_label}</TableCell>
                <TableCell>{item.estimated_cost || 0}</TableCell>
                <TableCell>{item.downtime_minutes} min</TableCell>
                <TableCell>{new Date(item.opened_at).toLocaleString()}</TableCell>
              </TableRow>
            ))}
            {interventions.length === 0 && (
              <TableRow>
                <TableCell colSpan={9}>
                  <Typography color="text.secondary">Aucune intervention enregistree.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>
    </Stack>
  )
}

function IngestionSection({
  machines,
  replaySources,
  selectedMachine,
  compatibleReplaySources,
  jobs,
  jobForm,
  setJobForm,
  handleCreateJob,
  handleJobAction,
  jobLogs,
  handleLoadJobLogs,
}) {
  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
          Jobs d'ingestion continue
        </Typography>
        <Stack component="form" spacing={2} onSubmit={handleCreateJob}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                select
                label="Machine"
                value={jobForm.machine_id}
                onChange={(event) => setJobForm({ ...jobForm, machine_id: event.target.value, source_id: '' })}
                fullWidth
              >
                {machines.map((machine) => (
                  <MenuItem key={machine.id} value={machine.id}>
                    {machine.name} • {machine.machine_type}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                select
                label="Mode"
                value={jobForm.mode}
                onChange={(event) => setJobForm({ ...jobForm, mode: event.target.value, source_id: '' })}
                fullWidth
              >
                <MenuItem value="simulator">simulator</MenuItem>
                <MenuItem value="replay">replay</MenuItem>
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 5 }}>
              <TextField
                select
                label="Source replay"
                value={jobForm.source_id}
                onChange={(event) => setJobForm({ ...jobForm, source_id: event.target.value })}
                fullWidth
                disabled={jobForm.mode !== 'replay'}
                helperText={selectedMachine && jobForm.mode === 'replay' ? `Sources compatibles avec ${selectedMachine.machine_type}` : ''}
              >
                {compatibleReplaySources.map((source) => (
                  <MenuItem key={source.source_id} value={source.source_id}>
                    {source.display_name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                label="Intervalle (s)"
                type="number"
                value={jobForm.interval_seconds}
                onChange={(event) => setJobForm({ ...jobForm, interval_seconds: event.target.value })}
                fullWidth
              />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                label="Pas replay"
                type="number"
                value={jobForm.replay_steps}
                onChange={(event) => setJobForm({ ...jobForm, replay_steps: event.target.value })}
                fullWidth
              />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Stack direction="row" spacing={2}>
                <FormControlLabel
                  control={<Switch checked={jobForm.drift} onChange={(event) => setJobForm({ ...jobForm, drift: event.target.checked })} />}
                  label="Drift"
                />
                <FormControlLabel
                  control={<Switch checked={jobForm.auto_restart} onChange={(event) => setJobForm({ ...jobForm, auto_restart: event.target.checked })} />}
                  label="Auto restart"
                />
              </Stack>
            </Grid>
          </Grid>
          <Stack direction="row" spacing={2}>
            <Button type="submit" variant="contained" sx={{ borderRadius: 999 }}>
              Creer job
            </Button>
            <Chip label={`${replaySources.length} sources de rejeu detectees`} />
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
          Jobs existants
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Machine</TableCell>
              <TableCell>Mode</TableCell>
              <TableCell>Etat</TableCell>
              <TableCell>Derniere execution</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.id}>
                <TableCell>{job.machine_name}</TableCell>
                <TableCell>{job.mode}</TableCell>
                <TableCell>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Chip size="small" color={job.is_active ? 'success' : 'default'} label={job.is_active ? 'actif' : 'arrete'} />
                    {job.last_error && <Chip size="small" color="error" label="erreur" />}
                  </Stack>
                </TableCell>
                <TableCell>{job.last_run_at ? new Date(job.last_run_at).toLocaleString() : '-'}</TableCell>
                <TableCell align="right">
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button size="small" variant="outlined" onClick={() => handleJobAction(job.id, 'start')} sx={{ borderRadius: 999 }}>
                      Start
                    </Button>
                    <Button size="small" variant="outlined" onClick={() => handleJobAction(job.id, 'stop')} sx={{ borderRadius: 999 }}>
                      Stop
                    </Button>
                    <Button size="small" variant="outlined" onClick={() => handleLoadJobLogs(job.id)} sx={{ borderRadius: 999 }}>
                      Logs
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
            {jobs.length === 0 && (
              <TableRow>
                <TableCell colSpan={5}>
                  <Typography color="text.secondary">Aucun job d'ingestion configure.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>

      {jobLogs.length > 0 && (
        <Paper sx={{ p: 2.5, borderRadius: 4 }}>
          <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
            Logs du job selectionne
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Niveau</TableCell>
                <TableCell>Evenement</TableCell>
                <TableCell>Message</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobLogs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell>{new Date(log.created_at).toLocaleString()}</TableCell>
                  <TableCell>{log.level}</TableCell>
                  <TableCell>{log.event_type}</TableCell>
                  <TableCell>{log.message}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Stack>
  )
}

function MlSection({ feedbackSummary, driftReport, refreshDrift, retrainForm, setRetrainForm, handleRetrain }) {
  return (
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, lg: 4 }}>
        <Card variant="outlined" sx={{ borderRadius: 4, height: '100%' }}>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1 }}>
              Labels terrain
            </Typography>
            <Typography>Total interventions: {feedbackSummary?.total_interventions || 0}</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1 }}>
              {Object.entries(feedbackSummary?.labels_breakdown || {}).map(([label, count]) => (
                <Chip key={label} label={`${label}: ${count}`} />
              ))}
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, lg: 4 }}>
        <Card variant="outlined" sx={{ borderRadius: 4, height: '100%' }}>
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                Drift des donnees
              </Typography>
              <Button variant="outlined" onClick={refreshDrift} sx={{ borderRadius: 999 }}>
                Actualiser
              </Button>
            </Stack>
            <Typography sx={{ mb: 1 }}>
              Statut global: <strong>{driftReport?.status || 'n/a'}</strong>
            </Typography>
            <Stack spacing={1}>
              {(driftReport?.metrics || []).slice(0, 6).map((metric) => (
                <Typography key={metric.feature} variant="body2">
                  {metric.feature}: baseline {metric.baseline_mean} • recent {metric.recent_mean} • ratio {metric.drift_ratio}
                </Typography>
              ))}
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, lg: 4 }}>
        <Card variant="outlined" sx={{ borderRadius: 4, height: '100%' }}>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 2 }}>
              Retraining base sur les interventions
            </Typography>
            <Grid container spacing={2}>
              <Grid size={12}>
                <TextField
                  label="Horizon (heures)"
                  type="number"
                  value={retrainForm.horizon_hours}
                  onChange={(event) => setRetrainForm({ ...retrainForm, horizon_hours: Number(event.target.value) })}
                  fullWidth
                />
              </Grid>
              <Grid size={12}>
                <TextField
                  label="Minimum d'echantillons"
                  type="number"
                  value={retrainForm.minimum_samples}
                  onChange={(event) => setRetrainForm({ ...retrainForm, minimum_samples: Number(event.target.value) })}
                  fullWidth
                />
              </Grid>
            </Grid>
            <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
              <Button variant="contained" onClick={handleRetrain} sx={{ borderRadius: 999 }}>
                Lancer retraining
              </Button>
            </Stack>
            {feedbackSummary?.latest_report && (
              <Typography variant="body2" sx={{ mt: 2, color: 'text.secondary' }}>
                Dernier rapport: {feedbackSummary.latest_report.best_model} • {feedbackSummary.latest_report.primary_metric} ={' '}
                {feedbackSummary.latest_report.metrics?.[feedbackSummary.latest_report.primary_metric]}
              </Typography>
            )}
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  )
}

export default function OperationsPage() {
  const { user } = useAuth()
  const [activeSection, setActiveSection] = useState('overview')
  const [assets, setAssets] = useState([])
  const [assetNodes, setAssetNodes] = useState([])
  const [machines, setMachines] = useState([])
  const [technicians, setTechnicians] = useState([])
  const [interventions, setInterventions] = useState([])
  const [jobs, setJobs] = useState([])
  const [jobLogs, setJobLogs] = useState([])
  const [replaySources, setReplaySources] = useState([])
  const [feedbackSummary, setFeedbackSummary] = useState(null)
  const [driftReport, setDriftReport] = useState(null)
  const [assetForm, setAssetForm] = useState(initialAssetForm)
  const [editingAssetId, setEditingAssetId] = useState(null)
  const [interventionForm, setInterventionForm] = useState({
    ...initialInterventionForm,
    technician_id: user?.id || '',
  })
  const [jobForm, setJobForm] = useState(initialJobForm)
  const [retrainForm, setRetrainForm] = useState(initialRetrainForm)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const loadPage = async () => {
    setLoading(true)
    try {
      const [
        assetsResponse,
        assetNodesResponse,
        machinesResponse,
        techniciansResponse,
        interventionsResponse,
        jobsResponse,
        sourcesResponse,
        feedbackResponse,
        driftResponse,
      ] = await Promise.all([
        api.get('/api/assets/tree'),
        api.get('/api/assets/nodes'),
        api.get('/api/machines/'),
        api.get('/api/users/technicians'),
        api.get('/api/interventions/'),
        api.get('/api/ingestion-jobs/'),
        api.get('/api/ml/replay/sources'),
        api.get('/api/ml/feedback-summary'),
        api.get('/api/ml/drift-report'),
      ])
      setAssets(assetsResponse.data)
      setAssetNodes(assetNodesResponse.data)
      setMachines(machinesResponse.data)
      setTechnicians(techniciansResponse.data)
      setInterventions(interventionsResponse.data)
      setJobs(jobsResponse.data)
      setReplaySources(sourcesResponse.data)
      setFeedbackSummary(feedbackResponse.data)
      setDriftReport(driftResponse.data)
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement des operations impossible')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPage()
  }, [])

  useEffect(() => {
    setInterventionForm((current) => ({ ...current, technician_id: current.technician_id || user?.id || '' }))
  }, [user?.id])

  const selectedMachine = useMemo(
    () => machines.find((machine) => machine.id === Number(jobForm.machine_id)) || null,
    [machines, jobForm.machine_id],
  )

  const compatibleReplaySources = useMemo(() => {
    if (!selectedMachine) {
      return replaySources
    }
    return replaySources.filter((source) => source.machine_type === selectedMachine.machine_type)
  }, [replaySources, selectedMachine])

  const handleSubmitAsset = async (event) => {
    event.preventDefault()
    try {
      const payload = {
        name: assetForm.name,
        node_type: assetForm.node_type,
        parent_id: assetForm.parent_id ? Number(assetForm.parent_id) : null,
      }
      if (editingAssetId) {
        await api.put(`/api/assets/nodes/${editingAssetId}`, payload)
        setSuccess('Noeud de hierarchie mis a jour.')
      } else {
        await api.post('/api/assets/nodes', payload)
        setSuccess('Noeud de hierarchie ajoute.')
      }
      setAssetForm(initialAssetForm)
      setEditingAssetId(null)
      loadPage()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Enregistrement du noeud impossible')
    }
  }

  const handleEditAsset = (node) => {
    setEditingAssetId(node.id)
    setAssetForm({
      name: node.name,
      node_type: node.node_type,
      parent_id: node.parent_id || '',
    })
  }

  const handleDeleteAsset = async (node) => {
    if (!window.confirm(`Supprimer le noeud "${node.name}" ?`)) {
      return
    }
    try {
      await api.delete(`/api/assets/nodes/${node.id}`)
      setSuccess('Noeud de hierarchie supprime.')
      if (editingAssetId === node.id) {
        setEditingAssetId(null)
        setAssetForm(initialAssetForm)
      }
      loadPage()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Suppression du noeud impossible')
    }
  }

  const handleCreateIntervention = async (event) => {
    event.preventDefault()
    try {
      await api.post('/api/interventions/', {
        ...interventionForm,
        machine_id: Number(interventionForm.machine_id),
        technician_id: interventionForm.technician_id ? Number(interventionForm.technician_id) : null,
        downtime_minutes: Number(interventionForm.downtime_minutes),
        estimated_cost: Number(interventionForm.estimated_cost),
        planned_at: interventionForm.planned_at || null,
      })
      setSuccess('Intervention enregistree.')
      setInterventionForm({ ...initialInterventionForm, technician_id: user?.id || '' })
      loadPage()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Creation intervention impossible')
    }
  }

  const handleCreateJob = async (event) => {
    event.preventDefault()
    try {
      await api.post('/api/ingestion-jobs/', {
        ...jobForm,
        machine_id: Number(jobForm.machine_id),
        interval_seconds: Number(jobForm.interval_seconds),
        replay_steps: Number(jobForm.replay_steps),
        source_id: jobForm.mode === 'replay' ? jobForm.source_id : null,
      })
      setSuccess("Job d'ingestion cree.")
      setJobForm(initialJobForm)
      loadPage()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Creation du job impossible')
    }
  }

  const handleJobAction = async (jobId, action) => {
    try {
      await api.post(`/api/ingestion-jobs/${jobId}/${action}`)
      setSuccess(action === 'start' ? 'Job demarre.' : 'Job arrete.')
      loadPage()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Action sur le job impossible')
    }
  }

  const handleLoadJobLogs = async (jobId) => {
    try {
      const response = await api.get(`/api/ingestion-jobs/${jobId}/logs`)
      setJobLogs(response.data)
      setSuccess(`Logs du job #${jobId} charges.`)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement des logs impossible')
    }
  }

  const handleRetrain = async () => {
    try {
      const response = await api.post('/api/ml/retrain-from-feedback', retrainForm)
      setSuccess(`Retraining termine. Meilleur modele: ${response.data.best_model}`)
      loadPage()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Retraining impossible')
    }
  }

  const refreshDrift = async () => {
    try {
      const response = await api.get('/api/ml/drift-report')
      setDriftReport(response.data)
      setSuccess('Rapport de drift mis a jour.')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Calcul du drift impossible')
    }
  }

  return (
    <Stack spacing={3}>
      {(error || success) && (
        <Stack spacing={1}>
          {error && <Alert severity="error">{error}</Alert>}
          {success && <Alert severity="success">{success}</Alert>}
        </Stack>
      )}

      <Paper
        sx={{
          p: 3,
          borderRadius: 5,
          background: 'linear-gradient(135deg, #0f172a 0%, #0f766e 55%, #38bdf8 100%)',
          color: '#fff',
        }}
      >
        <Stack direction={{ xs: 'column', lg: 'row' }} justifyContent="space-between" spacing={2}>
          <Stack spacing={1}>
            <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: '-0.04em' }}>
              Centre d'operations
            </Typography>
           
          </Stack>
          <Button
            variant="contained"
            startIcon={<RefreshRoundedIcon />}
            onClick={loadPage}
            disabled={loading}
            sx={{ alignSelf: 'flex-start', borderRadius: 999, bgcolor: '#fff', color: '#0f172a' }}
          >
            {loading ? 'Chargement...' : 'Rafraichir'}
          </Button>
        </Stack>
      </Paper>

      <SectionSelector activeSection={activeSection} onChange={setActiveSection} />

      {activeSection === 'overview' && (
        <QuickOverview
          assets={assets}
          assetNodes={assetNodes}
          interventions={interventions}
          jobs={jobs}
          driftReport={driftReport}
          feedbackSummary={feedbackSummary}
          setActiveSection={setActiveSection}
        />
      )}

      {activeSection === 'hierarchy' && (
        <HierarchySection
          assets={assets}
          assetNodes={assetNodes}
          assetForm={assetForm}
          setAssetForm={setAssetForm}
          editingAssetId={editingAssetId}
          setEditingAssetId={setEditingAssetId}
          handleSubmitAsset={handleSubmitAsset}
          handleEditAsset={handleEditAsset}
          handleDeleteAsset={handleDeleteAsset}
        />
      )}

      {activeSection === 'interventions' && (
        <InterventionsSection
          machines={machines}
          technicians={technicians}
          interventions={interventions}
          interventionForm={interventionForm}
          setInterventionForm={setInterventionForm}
          handleCreateIntervention={handleCreateIntervention}
          loadPage={loadPage}
          loading={loading}
        />
      )}

      {activeSection === 'ingestion' && (
        <IngestionSection
          machines={machines}
          replaySources={replaySources}
          selectedMachine={selectedMachine}
          compatibleReplaySources={compatibleReplaySources}
          jobs={jobs}
          jobForm={jobForm}
          setJobForm={setJobForm}
          handleCreateJob={handleCreateJob}
          handleJobAction={handleJobAction}
          jobLogs={jobLogs}
          handleLoadJobLogs={handleLoadJobLogs}
        />
      )}

      {activeSection === 'ml' && (
        <MlSection
          feedbackSummary={feedbackSummary}
          driftReport={driftReport}
          refreshDrift={refreshDrift}
          retrainForm={retrainForm}
          setRetrainForm={setRetrainForm}
          handleRetrain={handleRetrain}
        />
      )}

      <Divider />
      
    </Stack>
  )
}
