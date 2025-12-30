/**
 * Customers Page
 * Customer search and details view
 */

import { useState } from 'react';
import { Box, Typography, Paper, Divider } from '@mui/material';
import { CustomerSearch } from './components/CustomerSearch';
import type { Customer } from '../../api/endpoints/customers';

export default function CustomersPage() {
  const [searchValue, setSearchValue] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

  const handleSearchChange = (value: string) => {
    setSearchValue(value);
  };

  const handleCustomerSelect = (customer: Customer) => {
    setSelectedCustomer(customer);
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Clientes
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Buscar Cliente
        </Typography>
        <CustomerSearch
          value={searchValue}
          onChange={handleSearchChange}
          onSelect={handleCustomerSelect}
          limit={20}
          placeholder="Digite o nome ou telefone do cliente..."
        />
      </Paper>

      {selectedCustomer && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Cliente Selecionado
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Box>
            <Typography variant="body1" gutterBottom>
              <strong>ID:</strong> {selectedCustomer.id}
            </Typography>
            <Typography variant="body1" gutterBottom>
              <strong>Nome:</strong> {selectedCustomer.nome}
            </Typography>
            <Typography variant="body1" gutterBottom>
              <strong>Telefone:</strong> {selectedCustomer.telefone}
            </Typography>
            {selectedCustomer.email && (
              <Typography variant="body1" gutterBottom>
                <strong>Email:</strong> {selectedCustomer.email}
              </Typography>
            )}
          </Box>
        </Paper>
      )}
    </Box>
  );
}
