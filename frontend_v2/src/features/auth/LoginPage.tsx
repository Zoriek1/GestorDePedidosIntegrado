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
} from '@mui/material';
import { useAuth } from './authStore';
import { AppButton } from '../../components/common/AppButton';
import { useToast } from '../../components/system/useToast';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const { error: showError } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    if (!username.trim() || !password.trim()) {
      showError('Por favor, preencha usuário e senha');
      setLoading(false);
      return;
    }

    try {
      const result = await login(username.trim(), password, remember);

      if (result.success) {
        // Navigate to original route or home
        navigate(from, { replace: true });
      } else {
        showError(result.error || 'Credenciais inválidas');
      }
    } catch (err) {
      showError('Erro ao fazer login. Tente novamente.');
    } finally {
      setLoading(false);
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
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              autoComplete="username"
              sx={{ mb: 2 }}
              autoFocus
            />

            <TextField
              fullWidth
              label="Senha"
              type="password"
              variant="outlined"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              autoComplete="current-password"
              sx={{ mb: 2 }}
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

