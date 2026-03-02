#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script to resolve git merge conflicts by keeping the incoming (cc8c9d5) version."""
import os
import sys

def resolve_conflicts_incoming(content):
    """Keep the incoming (after =======) version for every conflict."""
    lines = content.split('\n')
    result = []
    in_head = False
    in_incoming = False
    incoming_block = []

    for line in lines:
        if line.startswith('<<<<<<< '):
            in_head = True
            in_incoming = False
            incoming_block = []
        elif not in_incoming and in_head and line == '=======':
            in_head = False
            in_incoming = True
        elif in_incoming and line.startswith('>>>>>>> '):
            in_incoming = False
            result.extend(incoming_block)
            incoming_block = []
        elif in_head:
            pass  # discard HEAD version
        elif in_incoming:
            incoming_block.append(line)
        else:
            result.append(line)

    return '\n'.join(result)

files_incoming = [
    'backend/app/cli.py',
    'backend/app/middleware.py',
    'backend/app/models/endereco_cliente.py',
    'backend/app/routes/rotas.py',
    'backend/app/services/distancia.py',
    'backend/app/config.py',
    'backend/app/routes/api.py',
    'backend/main.py',
    '.github/workflows/ci.yml',
    'frontend_v2/src/lib/logger.ts',
    'frontend_v2/src/lib/utils/clipboard.ts',
    'frontend_v2/src/features/pedidos/useCases/timeSlotAvailability.ts',
    'frontend_v2/src/features/pedidos/utils/quickEntryParser.ts',
    'frontend_v2/src/features/pedidos/useCases/orderToForm.ts',
    'frontend_v2/src/api/endpoints/rotas.ts',
    'frontend_v2/src/features/pedidos/components/OrderList.tsx',
    'frontend_v2/src/features/pedidos/components/PedidoWizard/index.tsx',
    'frontend_v2/src/features/pedidos/components/QuickEntryModal.tsx',
    'frontend_v2/src/features/pedidos/components/OrderCard.tsx',
    'frontend_v2/src/features/pedidos/OrdersPage.tsx',
    'frontend_v2/src/features/auth/authStore.tsx',
    'frontend_v2/src/features/notifications/NotificationManager.tsx',
    'frontend_v2/src/features/pedidos/CreateOrderPage.tsx',
    'frontend_v2/src/features/pedidos/CreateOrderWizard.tsx',
    'frontend_v2/package.json',
]

base = os.path.dirname(os.path.abspath(__file__))

for rel_path in files_incoming:
    filepath = os.path.join(base, rel_path)
    try:
        with open(filepath, 'r', encoding='utf-8') as fh:
            content = fh.read()

        if '<<<<<<< HEAD' not in content:
            print(f'SKIP (clean): {rel_path}')
            continue

        resolved = resolve_conflicts_incoming(content)

        with open(filepath, 'w', encoding='utf-8') as fh:
            fh.write(resolved)

        print(f'OK: {rel_path}')
    except FileNotFoundError:
        print(f'NOT FOUND: {rel_path}')
    except Exception as e:
        print(f'ERROR {rel_path}: {e}')

print('\nAll done.')
