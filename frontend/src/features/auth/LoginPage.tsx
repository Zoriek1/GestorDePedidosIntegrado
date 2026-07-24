/**
 * Login Page — split layout com painel de branding
 */

import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  TextField,
  Checkbox,
  FormControlLabel,
  Typography,
  InputAdornment,
  IconButton,
  Alert,
  Divider,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  LockOutlined,
  PersonOutline,
} from '@mui/icons-material';
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

    const form = e.currentTarget;
    const userInput =
      (form.elements.namedItem('email') as HTMLInputElement | null) ??
      (form.elements.namedItem('username') as HTMLInputElement | null);
    const passInput = form.elements.namedItem('password') as HTMLInputElement | null;
    const usernameValue = (userInput?.value ?? username).trim();
    const passwordValue = passInput?.value ?? password;

    let hasError = false;
    if (!usernameValue) { setUsernameError(true); hasError = true; }
    if (!passwordValue) { setPasswordError(true); hasError = true; }

    if (hasError) {
      setLoginError('Preencha e-mail (ou nome) e senha para continuar.');
      setLoading(false);
      return;
    }

    const sanitizedUsername = usernameValue.replace(/[<>'"]/g, '');
    if (sanitizedUsername !== usernameValue) {
      setUsernameError(true);
      setLoginError('O usuário contém caracteres inválidos (< > \' ").');
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
          setLoginError('Usuário não encontrado. Confira o e-mail ou nome digitado.');
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

  return (
    <Box
      sx={{
        display: 'flex',
        minHeight: '100vh',
        bgcolor: 'background.default',
      }}
    >
      {/* ── Painel esquerdo: branding ── */}
      <Box
        sx={{
          display: { xs: 'none', md: 'flex' },
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          width: '45%',
          background: 'linear-gradient(145deg, #065f46 0%, #047857 50%, #059669 100%)',
          position: 'relative',
          overflow: 'hidden',
          px: 6,
        }}
      >
        {/* Círculos decorativos */}
        <Box sx={{
          position: 'absolute', top: -80, right: -80,
          width: 320, height: 320, borderRadius: '50%',
          background: 'rgba(255,255,255,0.06)',
        }} />
        <Box sx={{
          position: 'absolute', bottom: -60, left: -60,
          width: 240, height: 240, borderRadius: '50%',
          background: 'rgba(255,255,255,0.06)',
        }} />
        <Box sx={{
          position: 'absolute', top: '40%', left: -40,
          width: 140, height: 140, borderRadius: '50%',
          background: 'rgba(255,255,255,0.04)',
        }} />

        {/* Conteúdo */}
        <Box
          className="animate__animated animate__fadeInLeft"
          sx={{ textAlign: 'center', color: 'white', zIndex: 1 }}
        >
          {/* Logo em container branco arredondado */}
          <Box
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              bgcolor: 'white',
              borderRadius: 4,
              px: 4,
              py: 2.5,
              mb: 5,
              boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
            }}
          >
            <Box
              component="img"
              src="/logo.png"
              alt="Plante uma Flor"
              sx={{ width: 220, height: 'auto', display: 'block' }}
            />
          </Box>

          <Typography
            variant="body1"
            sx={{ color: 'rgba(255,255,255,0.75)', mb: 5, fontSize: '1.05rem' }}
          >
            Gestão de Pedidos
          </Typography>

          <Divider sx={{ borderColor: 'rgba(255,255,255,0.2)', mb: 5 }} />

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, textAlign: 'left' }}>
            {[
              'Pedidos em tempo real',
              'Controle de entregas',
              'Relatórios e vendas',
            ].map((item) => (
              <Box key={item} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Box
                  sx={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: 'rgba(255,255,255,0.6)', flexShrink: 0,
                  }}
                />
                <Typography sx={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.95rem' }}>
                  {item}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>
      </Box>

      {/* ── Painel direito: formulário ── */}
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          px: { xs: 3, sm: 6, md: 8 },
          py: 6,
        }}
      >
        {/* Logo mobile */}
        <Box
          className="animate__animated animate__fadeInDown"
          sx={{ display: { xs: 'flex', md: 'none' }, mb: 4 }}
        >
          <Box
            component="img"
            src="/logo.png"
            alt="Plante uma Flor"
            sx={{ width: 180, height: 'auto' }}
          />
        </Box>

        <Box
          className="animate__animated animate__fadeInUp"
          sx={{ width: '100%', maxWidth: 420 }}
        >
          <Typography variant="h4" sx={{ fontWeight: 800, mb: 0.5, color: 'text.primary' }}>
            Bem-vindo de volta
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mb: 4 }}>
            Entre com seu e-mail ou nome de usuário
          </Typography>

          <form onSubmit={handleSubmit} noValidate>
            <TextField
              fullWidth
              name="email"
              label="E-mail ou nome"
              type="text"
              placeholder="seu@email.com ou seu nome"
              variant="outlined"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (loginError) setLoginError(null);
                if (usernameError && e.target.value.trim()) setUsernameError(false);
              }}
              onBlur={() => { if (!username.trim()) setUsernameError(true); else setUsernameError(false); }}
              disabled={loading}
              autoComplete="username"
              error={usernameError}
              helperText={usernameError ? 'Informe seu e-mail ou nome' : ''}
              inputProps={{ name: 'email' }}
              autoFocus
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <PersonOutline sx={{ color: usernameError ? 'error.main' : 'text.disabled', fontSize: 20 }} />
                    </InputAdornment>
                  ),
                },
              }}
              sx={{ mb: 2.5 }}
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
              onBlur={() => { if (!password) setPasswordError(true); else setPasswordError(false); }}
              disabled={loading}
              autoComplete="current-password"
              error={passwordError}
              helperText={passwordError ? 'Senha é obrigatória' : ''}
              inputProps={{ name: 'password' }}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <LockOutlined sx={{ color: passwordError ? 'error.main' : 'text.disabled', fontSize: 20 }} />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={() => setShowPassword(!showPassword)}
                        onMouseDown={(e) => e.preventDefault()}
                        edge="end"
                        disabled={loading}
                        size="small"
                      >
                        {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                      </IconButton>
                    </InputAdornment>
                  ),
                },
              }}
              sx={{ mb: 1 }}
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  disabled={loading}
                  size="small"
                  sx={{ color: 'primary.main' }}
                />
              }
              label={
                <Typography variant="body2" color="text.secondary">
                  Lembrar-me
                </Typography>
              }
              sx={{ mb: 2.5 }}
            />

            {loginError && (
              <Alert
                severity="error"
                sx={{ mb: 2.5, borderRadius: 2 }}
                className="animate__animated animate__shakeX"
              >
                {loginError}
              </Alert>
            )}

            <AppButton
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              loading={loading}
              sx={{
                py: 1.5,
                fontSize: '1rem',
                fontWeight: 700,
                borderRadius: 2,
                boxShadow: '0 4px 14px rgba(4,120,87,0.35)',
                '&:hover': {
                  boxShadow: '0 6px 20px rgba(4,120,87,0.45)',
                  transform: 'translateY(-1px)',
                },
                transition: 'all 0.2s ease',
              }}
            >
              {loading ? 'Entrando…' : 'Entrar'}
            </AppButton>
          </form>
        </Box>

        <Typography
          variant="caption"
          sx={{ mt: 6, color: 'text.disabled', textAlign: 'center' }}
        >
          © {new Date().getFullYear()} Plante Uma Flor · Gestão de Pedidos
        </Typography>
      </Box>
    </Box>
  );
}
