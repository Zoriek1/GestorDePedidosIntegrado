/**
 * Login Page
 * MUI form for user authentication
 */

import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  TextField,
  Checkbox,
  FormControlLabel,
  Typography,
  InputAdornment,
  IconButton,
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import { useAuth } from './authStore';
import { AppButton } from '../../components/common/AppButton';
import { useToast } from '../../components/system/useToast';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [usernameError, setUsernameError] = useState(false);
  const [passwordError, setPasswordError] = useState(false);

  const { login } = useAuth();
  const { error: showError } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setUsernameError(false);
    setPasswordError(false);

    // Validação em tempo real
    let hasError = false;
    if (!username.trim()) {
      setUsernameError(true);
      hasError = true;
    }
    if (!password.trim()) {
      setPasswordError(true);
      hasError = true;
    }

    if (hasError) {
      showError('Por favor, preencha usuário e senha');
      setLoading(false);
      return;
    }

    // Prevenção básica de SQL injection (sanitização)
    const sanitizedUsername = username.trim().replace(/[<>'"]/g, '');
    if (sanitizedUsername !== username.trim()) {
      showError('Usuário contém caracteres inválidos');
      setUsernameError(true);
      setLoading(false);
      return;
    }

    try {
      const result = await login(sanitizedUsername, password, remember);

      if (result.success) {
        // Navigate to original route or home
        navigate(from, { replace: true });
      } else {
        // Mensagens de erro específicas
        if (result.error?.toLowerCase().includes('credenciais') || result.error?.toLowerCase().includes('inválid')) {
          showError('Credenciais inválidas. Verifique seu usuário e senha.');
        } else if (result.error?.toLowerCase().includes('autenticação') || result.error?.toLowerCase().includes('auth')) {
          showError('Erro de autenticação. Tente novamente.');
        } else {
          showError(result.error || 'Erro ao fazer login. Tente novamente.');
        }
        setPasswordError(true);
      }
    } catch {
      showError('Erro ao fazer login. Tente novamente.');
      setPasswordError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleUsernameBlur = () => {
    if (!username.trim()) {
      setUsernameError(true);
    } else {
      setUsernameError(false);
    }
  };

  const handlePasswordBlur = () => {
    if (!password.trim()) {
      setPasswordError(true);
    } else {
      setPasswordError(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Login
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 3 }}>
            Plante Uma Flor - Gestão de Pedidos
          </Typography>

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Usuário"
              variant="outlined"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (usernameError && e.target.value.trim()) {
                  setUsernameError(false);
                }
              }}
              onBlur={handleUsernameBlur}
              disabled={loading}
              autoComplete="username"
              error={usernameError}
              helperText={usernameError ? 'Usuário é obrigatório' : ''}
              sx={{ mb: 2 }}
              autoFocus
            />

            <TextField
              fullWidth
              label="Senha"
              type={showPassword ? 'text' : 'password'}
              variant="outlined"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (passwordError && e.target.value.trim()) {
                  setPasswordError(false);
                }
              }}
              onBlur={handlePasswordBlur}
              disabled={loading}
              autoComplete="current-password"
              error={passwordError}
              helperText={passwordError ? 'Senha é obrigatória' : ''}
              sx={{ mb: 2 }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={() => setShowPassword(!showPassword)}
                      onMouseDown={(e) => e.preventDefault()}
                      edge="end"
                      disabled={loading}
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  disabled={loading}
                />
              }
              label="Lembrar-me"
              sx={{ mb: 2 }}
            />

            <AppButton
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              loading={loading}
              sx={{ mb: 2 }}
            >
              Entrar
            </AppButton>
          </form>
        </Paper>
      </Box>
    </Container>
  );
}

