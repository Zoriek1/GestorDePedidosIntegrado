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
  Alert,
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import { useAuth } from './authStore';
import { AppButton } from '../../components/common/AppButton';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [usernameError, setUsernameError] = useState(false);
  const [passwordError, setPasswordError] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setUsernameError(false);
    setPasswordError(false);
    setLoginError(null);

    // Ler do formulário (DOM) para não depender só do estado React: autofill e
    // alguns contextos (tunnel/HTTPS) podem preencher os campos sem atualizar o state.
    const form = e.currentTarget;
    const userInput = form.elements.namedItem('username') as HTMLInputElement | null;
    const passInput = form.elements.namedItem('password') as HTMLInputElement | null;
    const usernameValue = (userInput?.value ?? username).trim();
    const passwordValue = passInput?.value ?? password;

    let hasError = false;
    if (!usernameValue) {
      setUsernameError(true);
      hasError = true;
    }
    if (!passwordValue) {
      setPasswordError(true);
      hasError = true;
    }

    if (hasError) {
      setLoginError('Preencha e-mail (ou nome) e senha para continuar.');
      setLoading(false);
      return;
    }

    const sanitizedUsername = usernameValue.replace(/[<>'"]/g, '');
    if (sanitizedUsername !== usernameValue) {
      setUsernameError(true);
      setLoginError('Usuário contém caracteres inválidos (< > \' ").');
      setLoading(false);
      return;
    }

    try {
      const result = await login(sanitizedUsername, passwordValue, remember);

      if (result.success) {
        navigate(from, { replace: true });
      } else {
        const msg = result.error ?? '';
        if (
          msg.toLowerCase().includes('credenciais') ||
          msg.toLowerCase().includes('inválid') ||
          msg.toLowerCase().includes('senha') ||
          msg.toLowerCase().includes('unauthorized') ||
          msg.includes('401')
        ) {
          setLoginError('Usuário ou senha incorretos. Verifique e tente novamente.');
        } else if (msg.toLowerCase().includes('não encontrado') || msg.toLowerCase().includes('not found')) {
          setLoginError('Usuário não encontrado. Verifique o e-mail ou nome informado.');
        } else if (
          msg.toLowerCase().includes('servidor') ||
          msg.toLowerCase().includes('conexão') ||
          msg.toLowerCase().includes('connect')
        ) {
          setLoginError('Não foi possível conectar ao servidor. Verifique sua conexão.');
        } else if (msg) {
          setLoginError(msg);
        } else {
          setLoginError('Erro ao fazer login. Tente novamente.');
        }
      }
    } catch {
      setLoginError('Erro inesperado. Tente novamente.');
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
    if (!password) {
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
              name="username"
              label="E-mail ou nome"
              placeholder="ex: caio ou caio@email.com"
              variant="outlined"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (loginError) setLoginError(null);
                if (usernameError && e.target.value.trim()) setUsernameError(false);
              }}
              onBlur={handleUsernameBlur}
              disabled={loading}
              autoComplete="username"
              error={usernameError}
              helperText={usernameError ? 'Informe seu e-mail ou nome' : ''}
              inputProps={{ name: 'username' }}
              sx={{ mb: 2 }}
              autoFocus
            />

            <TextField
              fullWidth
              name="password"
              label="Senha"
              type={showPassword ? 'text' : 'password'}
              variant="outlined"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (loginError) setLoginError(null);
                if (passwordError && e.target.value) setPasswordError(false);
              }}
              onBlur={handlePasswordBlur}
              disabled={loading}
              autoComplete="current-password"
              error={passwordError}
              helperText={passwordError ? 'Senha é obrigatória' : ''}
              inputProps={{ name: 'password' }}
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

            {loginError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {loginError}
              </Alert>
            )}

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

