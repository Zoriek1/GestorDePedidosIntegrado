import { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Menu,
  MenuItem,
  Stack,
  Tooltip,
  CircularProgress,
  Alert,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SettingsIcon from '@mui/icons-material/Settings';
import PersonOffIcon from '@mui/icons-material/PersonOff';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import RestoreIcon from '@mui/icons-material/Restore';
import {
  useUsers,
  useCreateUser,
  useDeleteUser,
  useHardDeleteUser,
  useReactivateUser,
  useUpdateUser,
  CreateUserPayload,
  AppUser,
} from '../services/userApi';
import { UserConfigDialog } from './UserConfigDialog';
import { useToast } from '../../../components/system/useToast';
import { useConfirm } from '../../../components/system/useConfirm';
import { useAuth } from '../../auth/authStore';

function CreateUserDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const toast = useToast();
  const { mutateAsync, isPending } = useCreateUser();
  const [form, setForm] = useState<CreateUserPayload>({
    name: '',
    email: '',
    password: '',
    role: 'vendedor',
  });

  const handleSubmit = async () => {
    if (!form.name || !form.email || !form.password) {
      toast.error('Preencha todos os campos obrigatórios');
      return;
    }
    try {
      await mutateAsync(form);
      toast.success('Usuário criado com sucesso');
      onClose();
      setForm({ name: '', email: '', password: '', role: 'vendedor' });
    } catch (e) {
      toast.error(`Erro: ${(e as Error).message}`);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Novo Usuário</DialogTitle>
      <DialogContent>
        <Stack spacing={2} mt={1}>
          <TextField
            label="Nome"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            fullWidth
            required
          />
          <TextField
            label="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            fullWidth
            required
          />
          <TextField
            label="Senha"
            type="password"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            fullWidth
            required
            helperText="Mínimo 8 caracteres"
          />
          <TextField
            select
            label="Perfil"
            value={form.role}
            onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as CreateUserPayload['role'] }))}
            fullWidth
          >
            <MenuItem value="admin">Admin — acesso total</MenuItem>
            <MenuItem value="vendedor">Vendedor — vê seus recebíveis</MenuItem>
            <MenuItem value="atendente">Atendente — operação de pedidos</MenuItem>
            <MenuItem value="entregador">Entregador — pega entregas e recebe taxa</MenuItem>
            <MenuItem value="viewer">Viewer — somente visualização</MenuItem>
          </TextField>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isPending}>Cancelar</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isPending}
          startIcon={isPending ? <CircularProgress size={16} /> : undefined}
        >
          Criar
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function roleColor(role: string): 'error' | 'primary' | 'success' | 'warning' | 'default' {
  if (role === 'admin') return 'error';
  if (role === 'vendedor') return 'primary';
  if (role === 'entregador') return 'success';
  if (role === 'atendente') return 'warning';
  return 'default';
}

type RoleValue = AppUser['role'];

const ROLE_OPTIONS: { value: RoleValue; label: string; desc: string }[] = [
  { value: 'admin', label: 'Admin', desc: 'Acesso total' },
  { value: 'vendedor', label: 'Vendedor', desc: 'Vê seus recebíveis' },
  { value: 'atendente', label: 'Atendente', desc: 'Operação de pedidos' },
  { value: 'entregador', label: 'Entregador', desc: 'Pega entregas e recebe taxa' },
  { value: 'viewer', label: 'Viewer', desc: 'Somente visualização' },
];

function RoleSelectorChip({ user }: { user: AppUser }) {
  const [anchor, setAnchor] = useState<null | HTMLElement>(null);
  const toast = useToast();
  const { getUser } = useAuth();
  const me = getUser();
  const { mutateAsync, isPending } = useUpdateUser(user.id);

  // Admin não pode mudar o próprio cargo (perderia acesso). Backend também bloqueia.
  const isSelf = me?.id === user.id;
  const locked = isSelf || isPending;

  const handlePick = async (newRole: RoleValue) => {
    setAnchor(null);
    if (newRole === user.role) return;
    try {
      await mutateAsync({ role: newRole });
      toast.success(`Cargo atualizado para ${newRole}`);
    } catch (e) {
      toast.error(`Erro: ${(e as Error).message}`);
    }
  };

  if (locked) {
    return (
      <Tooltip
        title={isSelf ? 'Você não pode alterar o próprio cargo' : 'Atualizando…'}
      >
        <Chip label={user.role} size="small" color={roleColor(user.role)} />
      </Tooltip>
    );
  }

  return (
    <>
      <Tooltip title="Alterar cargo">
        <Chip
          label={user.role}
          size="small"
          color={roleColor(user.role)}
          onClick={(e) => setAnchor(e.currentTarget)}
          sx={{ cursor: 'pointer' }}
        />
      </Tooltip>
      <Menu
        anchorEl={anchor}
        open={Boolean(anchor)}
        onClose={() => setAnchor(null)}
        slotProps={{ paper: { sx: { minWidth: 220 } } }}
      >
        {ROLE_OPTIONS.map((opt) => (
          <MenuItem
            key={opt.value}
            selected={opt.value === user.role}
            onClick={() => handlePick(opt.value)}
          >
            <Box>
              <Typography variant="body2" fontWeight={600}>
                {opt.label}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {opt.desc}
              </Typography>
            </Box>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}

export default function UserListPage() {
  const toast = useToast();
  const confirm = useConfirm();
  // Sempre inclui inativos — admin precisa ver pra reativar/apagar definitivamente
  const { data: users, isLoading, error } = useUsers(true, true);
  const [createOpen, setCreateOpen] = useState(false);
  const [configUser, setConfigUser] = useState<AppUser | null>(null);

  function DeactivateBtn({ user }: { user: AppUser }) {
    const { mutateAsync, isPending } = useDeleteUser(user.id);
    const handle = async () => {
      const ok = await confirm({
        title: `Desativar "${user.name}"?`,
        description:
          'O usuário deixa de poder entrar, mas continua aparecendo aqui como Inativo. ' +
          'Você pode reativar a qualquer momento.',
        confirmText: 'Desativar',
        confirmColor: 'warning',
      });
      if (!ok) return;
      try {
        await mutateAsync();
        toast.success(`${user.name} desativado`);
      } catch (e) {
        toast.error(`Erro: ${(e as Error).message}`);
      }
    };
    return (
      <Tooltip title="Desativar (mantém histórico)">
        <IconButton size="small" onClick={handle} disabled={isPending} color="warning">
          {isPending ? <CircularProgress size={16} /> : <PersonOffIcon fontSize="small" />}
        </IconButton>
      </Tooltip>
    );
  }

  function ReactivateBtn({ user }: { user: AppUser }) {
    const { mutateAsync, isPending } = useReactivateUser(user.id);
    const handle = async () => {
      try {
        await mutateAsync();
        toast.success(`${user.name} reativado`);
      } catch (e) {
        toast.error(`Erro: ${(e as Error).message}`);
      }
    };
    return (
      <Tooltip title="Reativar usuário">
        <IconButton size="small" onClick={handle} disabled={isPending} color="success">
          {isPending ? <CircularProgress size={16} /> : <RestoreIcon fontSize="small" />}
        </IconButton>
      </Tooltip>
    );
  }

  function HardDeleteBtn({ user }: { user: AppUser }) {
    const { mutateAsync, isPending } = useHardDeleteUser(user.id);
    const handle = async () => {
      const ok = await confirm({
        title: `Apagar definitivamente "${user.name}"?`,
        description:
          `Isto LIBERA o email "${user.email}" e o nome "${user.name}" para serem ` +
          'usados em um novo cadastro. O histórico de pedidos e recebíveis dele é mantido ' +
          'como "Usuário removido". Esta ação não pode ser desfeita.',
        confirmText: 'Apagar definitivamente',
        confirmColor: 'error',
      });
      if (!ok) return;
      try {
        await mutateAsync();
        toast.success(`${user.name} apagado · email liberado`);
      } catch (e) {
        toast.error(`Erro: ${(e as Error).message}`);
      }
    };
    return (
      <Tooltip title="Apagar definitivamente (libera email e nome)">
        <IconButton size="small" onClick={handle} disabled={isPending} color="error">
          {isPending ? <CircularProgress size={16} /> : <DeleteForeverIcon fontSize="small" />}
        </IconButton>
      </Tooltip>
    );
  }

  if (error) {
    return <Alert severity="error">Erro ao carregar usuários: {(error as Error).message}</Alert>;
  }

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto', p: { xs: 2, sm: 3 } }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" fontWeight={700}>
          Usuários
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateOpen(true)}
          size="small"
        >
          Novo Usuário
        </Button>
      </Stack>

      {isLoading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : (
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Nome</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Perfil</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Ações</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(users ?? []).map((user) => (
              <TableRow key={user.id} hover>
                <TableCell>{user.name}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>
                  <RoleSelectorChip user={user} />
                </TableCell>
                <TableCell>
                  <Chip
                    label={user.is_active ? 'Ativo' : 'Inativo'}
                    size="small"
                    color={user.is_active ? 'success' : 'default'}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="Configurar remuneração / comissão">
                    <IconButton
                      size="small"
                      onClick={() => setConfigUser(user)}
                      color="primary"
                    >
                      <SettingsIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  {user.is_active ? (
                    <DeactivateBtn user={user} />
                  ) : (
                    <>
                      <ReactivateBtn user={user} />
                      <HardDeleteBtn user={user} />
                    </>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <CreateUserDialog open={createOpen} onClose={() => setCreateOpen(false)} />

      {configUser && (
        <UserConfigDialog
          open={!!configUser}
          onClose={() => setConfigUser(null)}
          userId={configUser.id}
          userName={configUser.name}
        />
      )}
    </Box>
  );
}
