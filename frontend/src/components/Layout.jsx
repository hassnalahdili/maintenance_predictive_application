import DashboardRoundedIcon from '@mui/icons-material/DashboardRounded'
import EngineeringRoundedIcon from '@mui/icons-material/EngineeringRounded'
import LockResetRoundedIcon from '@mui/icons-material/LockResetRounded'
import NotificationsActiveRoundedIcon from '@mui/icons-material/NotificationsActiveRounded'
import PrecisionManufacturingRoundedIcon from '@mui/icons-material/PrecisionManufacturingRounded'
import PsychologyRoundedIcon from '@mui/icons-material/PsychologyRounded'
import RuleRoundedIcon from '@mui/icons-material/RuleRounded'
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded'
import {
  Alert,
  AppBar,
  Badge,
  Box,
  Button,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const navItems = [
  { label: 'Dashboard', to: '/', icon: <DashboardRoundedIcon fontSize="small" /> },
  { label: 'Machines', to: '/machines', icon: <PrecisionManufacturingRoundedIcon fontSize="small" /> },
  { label: 'Regles', to: '/rules', icon: <RuleRoundedIcon fontSize="small" /> },
  { label: 'Alertes', to: '/alerts', icon: <WarningAmberRoundedIcon fontSize="small" /> },
  { label: 'Operations', to: '/operations', icon: <EngineeringRoundedIcon fontSize="small" /> },
  { label: 'ML', to: '/ml', icon: <PsychologyRoundedIcon fontSize="small" /> },
]

export default function Layout({ children }) {
  const { token, user, logout } = useAuth()
  const location = useLocation()
  const [notifications, setNotifications] = useState([])
  const [notificationAnchor, setNotificationAnchor] = useState(null)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '' })
  const [passwordMessage, setPasswordMessage] = useState('')
  const previousUnread = useRef(0)

  const unreadCount = notifications.filter((item) => !item.is_read).length

  useEffect(() => {
    if (!token) {
      setNotifications([])
      return undefined
    }

    const loadNotifications = async () => {
      try {
        const response = await api.get('/api/notifications/')
        const items = response.data
        const nextUnread = items.filter((item) => !item.is_read).length
        if (
          nextUnread > previousUnread.current &&
          typeof window.Notification !== 'undefined' &&
          window.Notification.permission === 'granted'
        ) {
          const latest = items.find((item) => !item.is_read)
          if (latest) {
            new window.Notification(latest.title, { body: latest.message })
          }
        }
        previousUnread.current = nextUnread
        setNotifications(items)
      } catch {
        setNotifications([])
      }
    }

    loadNotifications()
    const interval = window.setInterval(loadNotifications, 30000)
    return () => window.clearInterval(interval)
  }, [token])

  const openNotifications = (event) => {
    setNotificationAnchor(event.currentTarget)
    if (typeof window.Notification !== 'undefined' && window.Notification.permission === 'default') {
      window.Notification.requestPermission()
    }
  }

  const markAllNotificationsRead = async () => {
    await api.post('/api/notifications/mark-all-read')
    const response = await api.get('/api/notifications/')
    previousUnread.current = 0
    setNotifications(response.data)
  }

  const changePassword = async () => {
    setPasswordMessage('')
    try {
      await api.post('/api/auth/change-password', passwordForm)
      setPasswordMessage('Mot de passe mis a jour.')
      setPasswordForm({ current_password: '', new_password: '' })
    } catch (requestError) {
      setPasswordMessage(requestError.response?.data?.detail || 'Changement impossible')
    }
  }

  return (
    <>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          background: 'rgba(248, 250, 252, 0.88)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(148, 163, 184, 0.18)',
          color: '#0f172a',
        }}
      >
        <Toolbar sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap', py: 1 }}>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ flexWrap: 'wrap' }}>
            <Stack spacing={0}>
              <Typography variant="h6" sx={{ fontWeight: 800, letterSpacing: '-0.03em' }}>
                Predictive Maintenance Control Room
              </Typography>
             
            </Stack>
            {token && (
              <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: 'wrap' }}>
                {navItems.map((item) => (
                  <Button
                    key={item.to}
                    component={Link}
                    to={item.to}
                    variant={location.pathname === item.to ? 'contained' : 'text'}
                    startIcon={item.icon}
                    sx={{
                      borderRadius: 999,
                      px: 1.75,
                      color: location.pathname === item.to ? '#fff' : '#0f172a',
                      background:
                        location.pathname === item.to
                          ? 'linear-gradient(135deg, #0f766e 0%, #0f172a 100%)'
                          : 'transparent',
                    }}
                  >
                    {item.label}
                  </Button>
                ))}
                {user?.role === 'admin' && (
                  <Button
                    component={Link}
                    to="/users"
                    variant={location.pathname === '/users' ? 'contained' : 'text'}
                    sx={{
                      borderRadius: 999,
                      px: 1.75,
                      color: location.pathname === '/users' ? '#fff' : '#0f172a',
                      background:
                        location.pathname === '/users'
                          ? 'linear-gradient(135deg, #c2410c 0%, #7c2d12 100%)'
                          : 'transparent',
                    }}
                  >
                    Utilisateurs
                  </Button>
                )}
              </Stack>
            )}
          </Stack>

          <Stack direction="row" spacing={2} alignItems="center">
            {user && (
              <>
                <IconButton onClick={openNotifications} color="inherit" aria-label="Notifications">
                  <Badge badgeContent={unreadCount} color="error">
                    <NotificationsActiveRoundedIcon />
                  </Badge>
                </IconButton>
                <Chip
                  label={`${user.full_name} • ${user.role}`}
                  sx={{
                    bgcolor: 'rgba(15, 118, 110, 0.08)',
                    color: '#115e59',
                    fontWeight: 600,
                  }}
                />
                {user.password_reset_required && <Chip color="warning" label="Mot de passe a changer" />}
                <Button
                  onClick={() => setPasswordOpen(true)}
                  variant="outlined"
                  startIcon={<LockResetRoundedIcon fontSize="small" />}
                  sx={{ borderRadius: 999 }}
                >
                  Mot de passe
                </Button>
              </>
            )}
            {!token ? (
              <Button
                component={Link}
                to="/login"
                variant="contained"
                sx={{ borderRadius: 999, background: 'linear-gradient(135deg, #0f766e 0%, #1d4ed8 100%)' }}
              >
                Connexion
              </Button>
            ) : (
              <Button onClick={logout} variant="outlined" sx={{ borderRadius: 999 }}>
                Deconnexion
              </Button>
            )}
          </Stack>
        </Toolbar>
      </AppBar>
      <Box
        sx={{
          minHeight: '100vh',
          py: 4,
          background:
            'radial-gradient(circle at top left, rgba(14, 165, 233, 0.10), transparent 30%), radial-gradient(circle at top right, rgba(15, 118, 110, 0.08), transparent 32%), linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%)',
        }}
      >
        <Container maxWidth="xl">{children}</Container>
      </Box>

      <Menu anchorEl={notificationAnchor} open={Boolean(notificationAnchor)} onClose={() => setNotificationAnchor(null)}>
        <MenuItem disabled>
          <Typography variant="subtitle2">Notifications recentes</Typography>
        </MenuItem>
        {notifications.slice(0, 8).map((item) => (
          <MenuItem key={item.id} sx={{ alignItems: 'flex-start', whiteSpace: 'normal', maxWidth: 420 }}>
            <Stack spacing={0.4}>
              <Typography variant="body2" sx={{ fontWeight: item.is_read ? 500 : 800 }}>
                {item.title}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {item.message}
              </Typography>
            </Stack>
          </MenuItem>
        ))}
        {notifications.length === 0 && <MenuItem>Aucune notification</MenuItem>}
        <MenuItem onClick={markAllNotificationsRead} disabled={unreadCount === 0}>
          Tout marquer comme lu
        </MenuItem>
      </Menu>

      <Dialog open={passwordOpen} onClose={() => setPasswordOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Changer le mot de passe</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {passwordMessage && (
              <Alert severity={passwordMessage.includes('jour') ? 'success' : 'error'}>
                {passwordMessage}
              </Alert>
            )}
            <TextField
              label="Mot de passe actuel"
              type="password"
              value={passwordForm.current_password}
              onChange={(event) => setPasswordForm({ ...passwordForm, current_password: event.target.value })}
            />
            <TextField
              label="Nouveau mot de passe"
              type="password"
              helperText="Minimum 8 caracteres avec majuscule, minuscule et chiffre."
              value={passwordForm.new_password}
              onChange={(event) => setPasswordForm({ ...passwordForm, new_password: event.target.value })}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPasswordOpen(false)}>Fermer</Button>
          <Button variant="contained" onClick={changePassword}>
            Mettre a jour
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
