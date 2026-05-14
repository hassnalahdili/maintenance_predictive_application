import AdminPanelSettingsRoundedIcon from '@mui/icons-material/AdminPanelSettingsRounded'
import HistoryRoundedIcon from '@mui/icons-material/HistoryRounded'
import LockResetRoundedIcon from '@mui/icons-material/LockResetRounded'
import ManageAccountsRoundedIcon from '@mui/icons-material/ManageAccountsRounded'
import VerifiedUserRoundedIcon from '@mui/icons-material/VerifiedUserRounded'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
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
import api from '../services/api'

const initialForm = {
  full_name: '',
  email: '',
  password: '',
  role: 'viewer',
  is_active: true,
}

const roles = ['admin', 'technicien', 'expert', 'viewer']

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

export default function Users() {
  const [users, setUsers] = useState([])
  const [logs, setLogs] = useState([])
  const [form, setForm] = useState(initialForm)
  const [editingUser, setEditingUser] = useState(null)
  const [error, setError] = useState('')

  const loadUsers = async () => {
    try {
      const [usersResponse, logsResponse] = await Promise.all([api.get('/api/users/'), api.get('/api/audit-logs/')])
      setUsers(usersResponse.data)
      setLogs(logsResponse.data)
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chargement des utilisateurs impossible')
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const resetForm = () => {
    setForm(initialForm)
    setEditingUser(null)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    try {
      if (editingUser) {
        await api.put(`/api/users/${editingUser.id}`, form)
      } else {
        await api.post('/api/users/', form)
      }
      resetForm()
      loadUsers()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Enregistrement utilisateur impossible')
    }
  }

  const handleEdit = (user) => {
    setEditingUser(user)
    setForm({
      full_name: user.full_name,
      email: user.email,
      password: '',
      role: user.role,
      is_active: user.is_active,
    })
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cet utilisateur ?')) {
      return
    }
    try {
      await api.delete(`/api/users/${id}`)
      loadUsers()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Suppression impossible')
    }
  }

  const handleResetPassword = async (targetUser) => {
    const newPassword = window.prompt(`Nouveau mot de passe temporaire pour ${targetUser.full_name}`)
    if (!newPassword) {
      return
    }
    try {
      await api.post(`/api/users/${targetUser.id}/reset-password`, {
        new_password: newPassword,
        require_change_on_login: true,
      })
      loadUsers()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Reinitialisation impossible')
    }
  }

  const activeUsers = users.filter((user) => user.is_active).length
  const admins = users.filter((user) => user.role === 'admin').length
  const latestLogs = useMemo(() => logs.slice(0, 8), [logs])

  return (
    <Stack spacing={3}>
      {error && <Alert severity="error">{error}</Alert>}

      <Paper
        sx={{
          p: 3,
          borderRadius: 5,
          background: 'linear-gradient(135deg, #0f172a 0%, #4f46e5 48%, #7c3aed 100%)',
          color: '#fff',
        }}
      >
        <Stack spacing={1.2}>
          <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: '-0.04em' }}>
            Administration des utilisateurs
          </Typography>
          
        </Stack>
      </Paper>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
          <SummaryCard
            label="Utilisateurs"
            value={users.length}
            helper="Nombre total de comptes presents dans la plateforme."
            accent="#4f46e5"
            icon={<ManageAccountsRoundedIcon fontSize="small" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
          <SummaryCard
            label="Utilisateurs actifs"
            value={activeUsers}
            helper="Comptes actuellement actifs."
            accent="#059669"
            icon={<VerifiedUserRoundedIcon fontSize="small" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
          <SummaryCard
            label="Administrateurs"
            value={admins}
            helper="Comptes disposant des droits d'administration."
            accent="#c2410c"
            icon={<AdminPanelSettingsRoundedIcon fontSize="small" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}>
          <SummaryCard
            label="Logs recents"
            value={latestLogs.length}
            helper="Evenements d'audit visibles immediatement."
            accent="#0f172a"
            icon={<HistoryRoundedIcon fontSize="small" />}
          />
        </Grid>
      </Grid>

      <Stack spacing={2}>
        <Paper sx={{ p: 2.5, borderRadius: 4 }}>
          <Stack spacing={2}>
            <Stack spacing={0.8}>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                {editingUser ? "Mettre a jour l'utilisateur" : 'Creer un utilisateur'}
              </Typography>
              
            </Stack>

            <Box component="form" onSubmit={handleSubmit}>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6, xl: 3 }}>
                  <TextField
                    label="Nom"
                    value={form.full_name}
                    onChange={(event) => setForm({ ...form, full_name: event.target.value })}
                    fullWidth
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6, xl: 3 }}>
                  <TextField label="Email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} fullWidth />
                </Grid>
                <Grid size={{ xs: 12, md: 6, xl: 3 }}>
                  <TextField
                    label="Mot de passe"
                    type="password"
                    value={form.password}
                    onChange={(event) => setForm({ ...form, password: event.target.value })}
                    helperText={editingUser ? 'Laisser vide pour conserver le mot de passe actuel' : ''}
                    fullWidth
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 3, xl: 2 }}>
                  <TextField select label="Role" value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} fullWidth>
                    {roles.map((role) => (
                      <MenuItem key={role} value={role}>
                        {role}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid size={{ xs: 12, md: 3, xl: 1 }}>
                  <TextField
                    select
                    label="Actif"
                    value={String(form.is_active)}
                    onChange={(event) => setForm({ ...form, is_active: event.target.value === 'true' })}
                    fullWidth
                  >
                    <MenuItem value="true">Oui</MenuItem>
                    <MenuItem value="false">Non</MenuItem>
                  </TextField>
                </Grid>
                <Grid size={12}>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    <Button type="submit" variant="contained" sx={{ borderRadius: 999 }}>
                      {editingUser ? 'Mettre a jour' : 'Creer'}
                    </Button>
                    {editingUser && (
                      <Button variant="outlined" onClick={resetForm} sx={{ borderRadius: 999 }}>
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
            Liste des utilisateurs
          </Typography>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Nom</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Etat</TableCell>
                <TableCell align="right">Action</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>{user.id}</TableCell>
                  <TableCell>{user.full_name}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <Chip label={user.role} size="small" />
                  </TableCell>
                  <TableCell>{user.is_active ? 'Actif' : 'Inactif'}</TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button size="small" variant="outlined" onClick={() => handleEdit(user)} sx={{ borderRadius: 999 }}>
                        Editer
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<LockResetRoundedIcon fontSize="small" />}
                        onClick={() => handleResetPassword(user)}
                        sx={{ borderRadius: 999 }}
                      >
                        Reset mdp
                      </Button>
                      <Button size="small" color="error" variant="outlined" onClick={() => handleDelete(user.id)} sx={{ borderRadius: 999 }}>
                        Supprimer
                      </Button>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      </Stack>

      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
          Logs d'audit
        </Typography>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Utilisateur</TableCell>
              <TableCell>Action</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Objet</TableCell>
              <TableCell>Details</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {logs.map((log) => (
              <TableRow key={log.id}>
                <TableCell>{new Date(log.created_at).toLocaleString()}</TableCell>
                <TableCell>{log.user_name || 'Systeme'}</TableCell>
                <TableCell>{log.action}</TableCell>
                <TableCell>{log.entity_type}</TableCell>
                <TableCell>{log.entity_id || '-'}</TableCell>
                <TableCell>{log.details || '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Stack>
  )
}
