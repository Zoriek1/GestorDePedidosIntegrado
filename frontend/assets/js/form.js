/**
 * Plante Uma Flor - PWA v3.0
 * Form Manager - Gerenciador do formulário multi-step
 */

const FormManager = {
    currentStep: 1,
    totalSteps: 4,
    formData: {},
    buscandoCep: false,

    /**
     * Inicializa o formulário
     */
    init() {

        // Carregar dados do rascunho se existir
        this.loadDraft();

        // Configurar listeners
        this.setupListeners();

        // Configurar autocomplete de clientes
        this.setupClienteAutocomplete();

        // Carregar fontes de pedido
        this.carregarFontesPedido().then(() => {
            // Após carregar fontes, verificar se há fonte pré-selecionada
            if (typeof sessionStorage !== 'undefined') {
                const fonteSelecionada = sessionStorage.getItem('fonte_pedido_selecionada');
                if (fonteSelecionada) {
                    const selectFonte = document.getElementById('fonte_pedido_id');
                    if (selectFonte) {
                        selectFonte.value = fonteSelecionada;
                        
                        // Desabilitar o campo de fonte após seleção (similar aos campos de cliente)
                        // Nota: disabled impede envio do valor, então usamos uma abordagem diferente
                        // Vamos criar um input hidden para manter o valor e desabilitar visualmente o select
                        selectFonte.setAttribute('disabled', 'disabled');
                        selectFonte.classList.remove('bg-white', 'text-gray-900', 'border-gray-300');
                        selectFonte.classList.add('bg-gray-100', 'text-gray-500', 'cursor-not-allowed', 'border-gray-200');
                        
                        // Criar input hidden para garantir que o valor seja enviado mesmo com disabled
                        const hiddenInput = document.createElement('input');
                        hiddenInput.type = 'hidden';
                        hiddenInput.id = 'fonte_pedido_id_hidden';
                        hiddenInput.name = 'fonte_pedido_id';
                        hiddenInput.value = fonteSelecionada;
                        selectFonte.parentElement.appendChild(hiddenInput);
                        
                        // Adicionar mensagem informativa
                        const infoMsg = document.createElement('p');
                        infoMsg.className = 'mt-1 text-xs text-gray-500';
                        infoMsg.innerHTML = '<i class="fas fa-info-circle"></i> Fonte selecionada no modal - não pode ser alterada';
                        selectFonte.parentElement.appendChild(infoMsg);
                        
                        // Limpar do sessionStorage após usar
                        sessionStorage.removeItem('fonte_pedido_selecionada');
                    }
                }
            }
        });

        // Garantir que campos de cliente começam desabilitados
        setTimeout(() => {
            this.resetarCamposCliente();
        }, 200);

        // Configurar listeners de endereço (CEP e geração automática)
        // Usar setTimeout para garantir que o DOM esteja completamente renderizado
        setTimeout(() => {
            this.setupEnderecoListeners();
        }, 100);

        // Mostrar primeiro step
        this.showStep(1);

        // Atualizar progress bar
        this.updateProgress();
    },

    /**
     * Configura event listeners
     */
    setupListeners() {
        // Botões de navegação
        const btnAnterior = document.getElementById('btn-anterior');
        const btnProximo = document.getElementById('btn-proximo');
        const btnFinalizar = document.getElementById('btn-finalizar');


        if (btnAnterior) {
            btnAnterior.addEventListener('click', (e) => {
                e.preventDefault();
                this.previousStep();
            });
        }

        if (btnProximo) {
            btnProximo.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('➡️ Clicou em Próximo');
                this.nextStep();
            });
        }

        if (btnFinalizar) {
            btnFinalizar.addEventListener('click', (e) => {
                e.preventDefault();
                this.submitForm();
            });
        } else {
            console.warn('⚠️ Botão Finalizar NÃO encontrado ao configurar listeners');
        }

        // Listener para tipo de pedido (Entrega/Retirada)
        document.querySelectorAll('input[name="tipo_pedido"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.toggleEnderecoFields(e.target.value);
            });
        });

        // Verificar tipo inicial ao carregar
        const tipoInicial = document.querySelector('input[name="tipo_pedido"]:checked');
        if (tipoInicial) {
            this.toggleEnderecoFields(tipoInicial.value);
        }

        // Salvar rascunho automaticamente
        document.querySelectorAll('input, textarea, select').forEach(field => {
            field.addEventListener('change', () => this.saveDraft());
        });

        // Auto-aplicar máscaras
        Masks.applyAll();

        // Botão modal de horário
        const btnModalHorario = document.getElementById('btn-modal-horario');
        if (btnModalHorario) {
            btnModalHorario.addEventListener('click', () => {
                this.abrirModalHorario();
            });
        }

        // Tornar campo de horário clicável para abrir modal
        const campoHorario = document.getElementById('horario');
        if (campoHorario) {
            campoHorario.addEventListener('click', () => {
                this.abrirModalHorario();
            });
        }
    },

    /**
     * Carrega fontes de pedido e popula o select
     * @returns {Promise<void>}
     */
    async carregarFontesPedido() {
        try {
            console.log('[FORM] Carregando fontes de pedido...');
            const response = await API.getFontesPedido();
            console.log('[FORM] Resposta de fontes:', response);
            
            // Verificar estrutura da resposta
            if (!response.success) {
                console.warn('[FORM] ⚠️ Erro na requisição:', response.error);
                return;
            }
            
            if (!response.data) {
                console.warn('[FORM] ⚠️ Resposta sem dados');
                return;
            }
            
            // Simplificar verificação - response.data já contém o objeto retornado pela API
            const fontes = response.data.fontes || [];
            
            if (Array.isArray(fontes) && fontes.length > 0) {
                const select = document.getElementById('fonte_pedido_id');
                
                if (select) {
                    // Limpar opções existentes (exceto a primeira "Selecione...")
                    select.innerHTML = '<option value="">Selecione a fonte...</option>';
                    
                    // Adicionar opções
                    fontes.forEach(fonte => {
                        const option = document.createElement('option');
                        option.value = fonte.id;
                        option.textContent = fonte.nome;
                        select.appendChild(option);
                    });
                    
                } else {
                    console.warn('[FORM] ⚠️ Select fonte_pedido_id não encontrado');
                }
            } else {
                console.warn('[FORM] ⚠️ Nenhuma fonte encontrada ou estrutura inválida. Fontes:', fontes);
            }
        } catch (error) {
            console.error('[FORM] Erro ao carregar fontes de pedido:', error);
        }
    },

    /**
     * Configura autocomplete de clientes
     */
    setupClienteAutocomplete() {
        console.log('👥 Configurando autocomplete de clientes (datalist nativo)...');

        const inputAutocomplete = document.getElementById('cliente-autocomplete');
        const btnNovoCliente = document.getElementById('btn-novo-cliente');
        const btnHistorico = document.getElementById('btn-historico-cliente');
        const datalist = document.getElementById('clientesDatalist');

        if (!inputAutocomplete || !datalist) return;

        // GUARD: Evitar múltiplas inicializações (SPA navigation)
        if (inputAutocomplete.dataset.datalistInitialized === 'true') {
            return;
        }
        inputAutocomplete.dataset.datalistInitialized = 'true';

        // Map para mapear value string -> objeto cliente completo
        const clientesMap = new Map();

        // Função para criar value único: "NOME — TELEFONE (#ID)"
        const criarValueUnico = (cliente) => {
            const nome = String(cliente.nome || '');
            const telefone = String(cliente.telefone || '');
            const id = cliente.id ? String(cliente.id) : '';
            
            let telefoneFormatado = telefone;
            try {
                telefoneFormatado = Utils.formatPhone ? Utils.formatPhone(telefone) : telefone;
            } catch (e) {
                // Se formatPhone falhar, usar telefone original
            }
            
            // Formato: "NOME — TELEFONE (#ID)" ou "NOME (#ID)" se não tiver telefone
            if (telefoneFormatado && telefoneFormatado.trim()) {
                return `${nome} — ${telefoneFormatado}${id ? ' (#' + id + ')' : ''}`;
            }
            return `${nome}${id ? ' (#' + id + ')' : ''}`;
        };

        // Buscar clientes quando usuário digita
        let debounceTimeout;
        inputAutocomplete.addEventListener('input', (e) => {
            const query = String(e.target.value || '').trim();
            
            clearTimeout(debounceTimeout);
            
            if (query.length >= 2) {
                debounceTimeout = setTimeout(async () => {
                    try {
                        const response = await API.get(`/api/clientes/search?q=${encodeURIComponent(query)}&limit=10`);
                        
                        if (response.success && response.data.success) {
                            const clientes = response.data.clientes || [];
                            
                            // Limpar map e datalist anteriores
                            clientesMap.clear();
                            datalist.innerHTML = '';
                            
                            // Adicionar opções ao datalist e popular o map
                            clientes.forEach(cliente => {
                                const valueUnico = criarValueUnico(cliente);
                                
                                // Adicionar ao map
                                clientesMap.set(valueUnico, cliente);
                                
                                // Criar option no datalist
                                const option = document.createElement('option');
                                option.value = valueUnico;
                                datalist.appendChild(option);
                            });
                        } else {
                            // Limpar se não houver resultados
                            clientesMap.clear();
                            datalist.innerHTML = '';
                        }
                    } catch (error) {
                        console.error('Erro ao buscar clientes:', error);
                        clientesMap.clear();
                        datalist.innerHTML = '';
                    }
                }, 250); // Debounce 250ms
            } else {
                // Limpar se query muito curta
                clientesMap.clear();
                datalist.innerHTML = '';
            }
        });

        // Seleção de cliente - evento "change" quando usuário seleciona do datalist
        inputAutocomplete.addEventListener('change', (e) => {
            const selectedValue = String(e.target.value || '').trim();
            
            if (!selectedValue) return;
            
            // Buscar cliente no map
            const cliente = clientesMap.get(selectedValue);
            
            if (cliente) {
                // Cliente encontrado, preencher formulário
                this.onClienteSelect(cliente);
            } else {
                // Se não encontrou no map, pode ser que o usuário digitou manualmente
                // Nesse caso, não fazer nada (deixar usuário continuar digitando)
                console.log('Cliente não encontrado no map, usuário pode estar digitando manualmente');
            }
        });

        if (btnNovoCliente) {
            const handleNovoCliente = () => {
                document.getElementById('cliente_id').value = '';
                document.getElementById('cliente').value = '';
                document.getElementById('telefone_cliente').value = '';
                inputAutocomplete.value = '';

                const campoCliente = document.getElementById('cliente');
                const campoTelefone = document.getElementById('telefone_cliente');

                campoCliente.removeAttribute('readonly');
                campoCliente.removeAttribute('disabled');
                campoCliente.classList.remove('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
                campoCliente.classList.add('bg-white', 'text-gray-900');
                campoCliente.placeholder = 'Digite o nome do cliente';

                campoTelefone.removeAttribute('readonly');
                campoTelefone.removeAttribute('disabled');
                campoTelefone.classList.remove('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
                campoTelefone.classList.add('bg-white', 'text-gray-900');
                campoTelefone.placeholder = '(62) 99999-9999';

                if (btnHistorico) {
                    btnHistorico.classList.add('hidden');
                    btnHistorico.dataset.clienteId = '';
                }

                Notification.show('Campos habilitados - Digite os dados do novo cliente', 'info');
            };

            btnNovoCliente.addEventListener('click', handleNovoCliente);
            btnNovoCliente.addEventListener('touchstart', (e) => {
                e.preventDefault();
                handleNovoCliente();
            });
        }

        if (btnHistorico) {
            btnHistorico.addEventListener('click', async () => {
                const clienteId = btnHistorico.dataset.clienteId;
                if (clienteId) {
                    await this.mostrarHistoricoCliente(clienteId);
                }
            });
        }

    },

    onClienteSelect(cliente) {
        document.getElementById('cliente_id').value = cliente.id;

        const campoCliente = document.getElementById('cliente');
        const campoTelefone = document.getElementById('telefone_cliente');

        campoCliente.value = cliente.nome;
        campoTelefone.value = cliente.telefone;

        campoCliente.removeAttribute('readonly');
        campoCliente.removeAttribute('disabled');
        campoCliente.classList.remove('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
        campoCliente.classList.add('bg-white', 'text-gray-900');

        campoTelefone.removeAttribute('readonly');
        campoTelefone.removeAttribute('disabled');
        campoTelefone.classList.remove('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
        campoTelefone.classList.add('bg-white', 'text-gray-900');

        const btnHistorico = document.getElementById('btn-historico-cliente');
        if (btnHistorico) {
            btnHistorico.classList.remove('hidden');
            btnHistorico.dataset.clienteId = cliente.id;
        }

        this.carregarEnderecosCliente(cliente.id);
        Notification.show(`Cliente "${cliente.nome}" selecionado - Campos podem ser editados`, 'success');
    },

    /**
     * Reseta campos de cliente ao estado inicial (desabilitados)
     */
    resetarCamposCliente() {
        const campoCliente = document.getElementById('cliente');
        const campoTelefone = document.getElementById('telefone_cliente');
        const inputAutocomplete = document.getElementById('cliente-autocomplete');
        const btnHistorico = document.getElementById('btn-historico-cliente');

        if (campoCliente) {
            campoCliente.value = '';
            campoCliente.setAttribute('readonly', 'readonly');
            campoCliente.setAttribute('disabled', 'disabled');
            campoCliente.classList.remove('bg-white', 'text-gray-900');
            campoCliente.classList.add('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
            campoCliente.placeholder = "Busque um cliente acima ou clique em 'Cadastrar Novo Cliente'";
        }

        if (campoTelefone) {
            campoTelefone.value = '';
            campoTelefone.setAttribute('readonly', 'readonly');
            campoTelefone.setAttribute('disabled', 'disabled');
            campoTelefone.classList.remove('bg-white', 'text-gray-900');
            campoTelefone.classList.add('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
            campoTelefone.placeholder = "Busque um cliente acima ou clique em 'Cadastrar Novo Cliente'";
        }

        if (inputAutocomplete) {
            inputAutocomplete.value = '';
        }

        if (btnHistorico) {
            btnHistorico.classList.add('hidden');
        }

        document.getElementById('cliente_id').value = '';
    },

    /**
     * Carrega endereços salvos do cliente
     */
    async carregarEnderecosCliente(clienteId) {
        try {
            const response = await API.get(`/api/clientes/${clienteId}/enderecos`);

            if (response.success && response.data.success) {
                const enderecos = response.data.enderecos;

                if (enderecos.length > 0) {
                    // Buscar endereço principal ou o primeiro
                    const enderecoPrincipal = enderecos.find(e => e.principal) || enderecos[0];

                    // Preencher campos de endereço
                    if (enderecoPrincipal.cep) document.getElementById('cep').value = enderecoPrincipal.cep;
                    if (enderecoPrincipal.rua) document.getElementById('rua').value = enderecoPrincipal.rua;
                    if (enderecoPrincipal.numero) document.getElementById('numero').value = enderecoPrincipal.numero;
                    if (enderecoPrincipal.bairro) document.getElementById('bairro').value = enderecoPrincipal.bairro;
                    if (enderecoPrincipal.cidade) document.getElementById('cidade').value = enderecoPrincipal.cidade;

                    Notification.show(`Endereço ${enderecoPrincipal.apelido || 'principal'} carregado!`, 'success');
                }
            }
        } catch (error) {
            console.error('Erro ao carregar endereços:', error);
        }
    },

    /**
     * Mostra modal com histórico do cliente
     */
    async mostrarHistoricoCliente(clienteId) {
        try {
            const response = await API.get(`/api/clientes/${clienteId}/pedidos?limit=20`);

            if (response.success && response.data.success) {
                const cliente = response.data;

                // Criar conteúdo do modal
                const historicoHTML = `
                    <div class="space-y-4">
                        <div class="bg-blue-50 p-4 rounded-lg">
                            <h3 class="font-bold text-lg">${cliente.nome}</h3>
                            <p class="text-sm text-gray-600">Total de pedidos: ${cliente.total_pedidos}</p>
                        </div>
                        
                        <div class="max-h-96 overflow-y-auto space-y-2">
                            ${cliente.pedidos.map(pedido => `
                                <div class="border rounded-lg p-3 hover:bg-gray-50">
                                    <div class="flex justify-between items-start">
                                        <div>
                                            <p class="font-medium">${pedido.produto}</p>
                                            <p class="text-sm text-gray-600">Para: ${pedido.destinatario}</p>
                                            <p class="text-xs text-gray-500">
                                                ${new Date(pedido.dia_entrega).toLocaleDateString('pt-BR')} - ${pedido.horario}
                                            </p>
                                        </div>
                                        <div class="text-right">
                                            <span class="badge badge-sm">${pedido.status}</span>
                                            ${pedido.valor ? `<p class="text-sm font-medium mt-1">${pedido.valor}</p>` : ''}
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;

                Modal.show(`Histórico - ${cliente.nome}`, historicoHTML);
            }
        } catch (error) {
            console.error('Erro ao carregar histórico:', error);
            Notification.show('Erro ao carregar histórico do cliente', 'error');
        }
    },

    /**
     * Configura listeners para campos de endereço (CEP e geração automática)
     */
    setupEnderecoListeners() {
        console.log('🏠 Configurando listeners de endereço...');

        // Botão de buscar CEP
        const btnBuscarCep = document.getElementById('btn-buscar-cep');
        console.log('Botão Buscar CEP:', btnBuscarCep ? 'Encontrado' : 'NÃO encontrado');

        if (btnBuscarCep) {
            // Remover listeners antigos clonando o elemento
            const newBtnCep = btnBuscarCep.cloneNode(true);
            btnBuscarCep.parentNode.replaceChild(newBtnCep, btnBuscarCep);

            newBtnCep.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.buscarCep();
            });
        }

        // Buscar CEP ao pressionar Enter no campo
        const cepInput = document.getElementById('cep');
        console.log('Campo CEP:', cepInput ? 'Encontrado' : 'NÃO encontrado');

        if (cepInput) {
            cepInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.buscarCep();
                }
            });

            // Buscar automaticamente quando completar 9 caracteres (XXXXX-XXX)
            cepInput.addEventListener('input', (e) => {
                if (e.target.value.length === 9) {
                    console.log('📝 CEP completo, buscando automaticamente...');
                    this.buscarCep();
                }
            });
        }

        // Botão de gerar endereço completo
        const btnGerarEndereco = document.getElementById('btn-gerar-endereco');

        if (btnGerarEndereco) {
            // Remover listeners antigos clonando o elemento
            const newBtnEndereco = btnGerarEndereco.cloneNode(true);
            btnGerarEndereco.parentNode.replaceChild(newBtnEndereco, btnGerarEndereco);

            newBtnEndereco.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('✨ Clicou em Gerar Endereço');
                this.gerarEnderecoCompleto();
            });
            console.log('✅ Listener do botão Gerar Endereço configurado!');
        }
    },

    /**
     * Busca endereço pelo CEP usando a API ViaCEP
     */
    async buscarCep() {
        if (this.buscandoCep) return;

        const cepInput = document.getElementById('cep');
        const cepStatus = document.getElementById('cep-status');

        if (!cepInput) return;

        const cep = Masks.unmaskCep(cepInput.value);

        if (cep.length !== 8) {
            this.showCepStatus('Digite um CEP válido com 8 dígitos', 'error');
            return;
        }

        this.buscandoCep = true;
        this.showCepStatus('Buscando...', 'loading');

        try {
            const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
            const data = await response.json();

            if (data.erro) {
                this.showCepStatus('CEP não encontrado', 'error');
                return;
            }

            // Preencher campos com os dados retornados
            const ruaInput = document.getElementById('rua');
            const bairroInput = document.getElementById('bairro');
            const cidadeInput = document.getElementById('cidade');

            if (ruaInput && data.logradouro) {
                ruaInput.value = data.logradouro;
            }
            if (bairroInput && data.bairro) {
                bairroInput.value = data.bairro;
            }
            if (cidadeInput && data.localidade) {
                cidadeInput.value = data.localidade;
            }

            this.showCepStatus('Endereço encontrado!', 'success');

            // Focar no campo número
            const numeroInput = document.getElementById('numero');
            if (numeroInput) {
                numeroInput.focus();
            }


        } catch (error) {
            console.error('Erro ao buscar CEP:', error);
            this.showCepStatus('Erro ao buscar CEP. Tente novamente.', 'error');
        } finally {
            this.buscandoCep = false;
        }
    },

    /**
     * Mostra status da busca de CEP
     */
    showCepStatus(message, type) {
        const cepStatus = document.getElementById('cep-status');
        if (!cepStatus) return;

        cepStatus.textContent = message;
        cepStatus.classList.remove('hidden', 'text-red-600', 'text-primary', 'text-blue-600');

        switch (type) {
            case 'error':
                cepStatus.classList.add('text-red-600');
                break;
            case 'success':
                cepStatus.classList.add('text-primary');
                // Esconder após 3 segundos
                setTimeout(() => {
                    cepStatus.classList.add('hidden');
                }, 3000);
                break;
            case 'loading':
                cepStatus.classList.add('text-blue-600');
                break;
        }
    },

    /**
     * Gera o endereço completo automaticamente a partir dos campos
     */
    gerarEnderecoCompleto() {
        const rua = document.getElementById('rua')?.value?.trim() || '';
        const numero = document.getElementById('numero')?.value?.trim() || '';
        const bairro = document.getElementById('bairro')?.value?.trim() || '';
        const cidade = document.getElementById('cidade')?.value?.trim() || '';
        const cep = document.getElementById('cep')?.value?.trim() || '';

        // Montar endereço completo
        const partes = [];

        if (rua) {
            // Ignorar número "0" ou "S/N" (sem número)
            if (numero && numero !== '0' && numero.toUpperCase() !== 'S/N' && numero.toUpperCase() !== 'SN') {
                partes.push(`${rua}, ${numero}`);
            } else {
                partes.push(rua);
            }
        }

        if (bairro) {
            partes.push(bairro);
        }

        if (cidade) {
            partes.push(cidade);
        }

        if (cep) {
            partes.push(`CEP: ${cep}`);
        }

        // Usar vírgula como separador (padrão brasileiro)
        const enderecoCompleto = partes.join(', ');

        const enderecoInput = document.getElementById('endereco');
        if (enderecoInput) {
            enderecoInput.value = enderecoCompleto;

            if (enderecoCompleto) {
                Notification.success('Endereço gerado com sucesso!');
            } else {
                Notification.warning('Preencha pelo menos a rua para gerar o endereço');
            }
        }

    },

    /**
     * Mostra/oculta campos de endereço baseado no tipo de pedido
     */
    toggleEnderecoFields(tipoPedido) {
        // Selecionar todos os containers de campos de endereço
        const cepContainer = document.getElementById('cep')?.closest('div')?.parentElement;
        const ruaNumeroGrid = document.getElementById('rua')?.closest('.grid');
        const bairroCidadeGrid = document.getElementById('bairro')?.closest('.grid');
        const enderecoContainer = document.getElementById('endereco')?.closest('div');
        const obsEntregaContainer = document.getElementById('obs_entrega')?.closest('div');
        const step3Title = document.querySelector('#step-3 h2');

        const camposEndereco = [cepContainer, ruaNumeroGrid, bairroCidadeGrid, enderecoContainer];

        if (tipoPedido === 'Retirada') {
            // Esconder campos de endereço
            camposEndereco.forEach(container => {
                if (container) {
                    container.style.display = 'none';
                }
            });

            // Limpar campos de endereço
            ['cep', 'rua', 'numero', 'bairro', 'cidade', 'endereco'].forEach(fieldId => {
                const field = document.getElementById(fieldId);
                if (field) {
                    field.removeAttribute('required');
                    field.value = '';
                }
            });

            // Mudar título do step 3
            if (step3Title) {
                step3Title.innerHTML = `
                    <i class="fas fa-store text-primary"></i>
                    Observações de Retirada
                `;
            }

            // Manter observações visíveis e ajustar label
            if (obsEntregaContainer) {
                const label = obsEntregaContainer.querySelector('label');
                if (label) {
                    label.innerHTML = `
                        Como Retirar / Observações de Retirada
                    `;
                }
            }

            console.log('🏪 Modo: Retirada - Campos de endereço ocultados');
        } else {
            // Mostrar campos de endereço
            camposEndereco.forEach(container => {
                if (container) {
                    container.style.display = '';
                }
            });

            // Restaurar título do step 3
            if (step3Title) {
                step3Title.innerHTML = `
                    <i class="fas fa-map-marker-alt text-primary"></i>
                    Logística de Entrega
                `;
            }

            // Restaurar label de observações
            if (obsEntregaContainer) {
                const label = obsEntregaContainer.querySelector('label');
                if (label) {
                    label.innerHTML = `
                        Como Entregar / Observações de Entrega
                    `;
                }
            }

        }
    },

    /**
     * Mostra step específico
     */
    showStep(step) {
        // Esconder todos os steps
        document.querySelectorAll('.form-step').forEach(s => {
            s.classList.remove('active');
        });

        // Mostrar step atual
        const currentStepElement = document.getElementById(`step-${step}`);
        if (currentStepElement) {
            currentStepElement.classList.add('active');
        }

        // IMPORTANTE: Atualizar currentStep ANTES de chamar updateButtons
        this.currentStep = step;

        // Atualizar botões (agora com currentStep correto)
        this.updateButtons();

        // Atualizar número do step
        const stepNumber = document.getElementById('step-number');
        if (stepNumber) {
            stepNumber.textContent = step;
        }

        // Se está indo para o step 3, garantir que campos de endereço estejam corretos
        if (step === 3) {
            const tipoSelecionado = document.querySelector('input[name="tipo_pedido"]:checked');
            if (tipoSelecionado) {
                this.toggleEnderecoFields(tipoSelecionado.value);
            }
            // Reconfigurar listeners de endereço quando entrar no step 3
            this.setupEnderecoListeners();
        }

        // Scroll para o topo
        window.scrollTo(0, 0);
    },

    /**
     * Atualiza botões de navegação
     */
    updateButtons() {
        const btnAnterior = document.getElementById('btn-anterior');
        const btnProximo = document.getElementById('btn-proximo');
        const btnFinalizar = document.getElementById('btn-finalizar');

        console.log(`🔄 Atualizando botões - Step ${this.currentStep}/${this.totalSteps}`);

        // Botão Anterior
        if (btnAnterior) {
            if (this.currentStep === 1) {
                btnAnterior.classList.add('hidden');
            } else {
                btnAnterior.classList.remove('hidden');
            }
        }

        // Botão Próximo
        if (btnProximo) {
            if (this.currentStep === this.totalSteps) {
                btnProximo.classList.add('hidden');
            } else {
                btnProximo.classList.remove('hidden');
            }
        }

        // Botão Finalizar
        if (btnFinalizar) {
            if (this.currentStep === this.totalSteps) {
                btnFinalizar.classList.remove('hidden');

                // Reconfigurar listener para garantir
                const newBtn = btnFinalizar.cloneNode(true);
                btnFinalizar.parentNode.replaceChild(newBtn, btnFinalizar);
                newBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.submitForm();
                });
            } else {
                btnFinalizar.classList.add('hidden');
            }
        } else {
            console.warn('⚠️ Botão Finalizar NÃO encontrado em updateButtons()');
        }
    },

    /**
     * Atualiza barra de progresso
     */
    updateProgress() {
        const progress = (this.currentStep / this.totalSteps) * 100;
        const progressBar = document.getElementById('progress-bar');

        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }

        // Atualizar indicadores
        for (let i = 1; i <= this.totalSteps; i++) {
            const indicator = document.getElementById(`progress-${i}`);
            if (indicator) {
                if (i < this.currentStep) {
                    indicator.classList.add('completed');
                    indicator.classList.remove('active');
                } else if (i === this.currentStep) {
                    indicator.classList.add('active');
                    indicator.classList.remove('completed');
                } else {
                    indicator.classList.remove('active', 'completed');
                }
            }
        }
    },

    /**
     * Valida step atual
     */
    validateCurrentStep() {
        const currentStepElement = document.getElementById(`step-${this.currentStep}`);
        if (!currentStepElement) {
            return true;
        }

        const requiredFields = currentStepElement.querySelectorAll('[required]');

        let isValid = true;
        const errors = [];

        requiredFields.forEach(field => {
            const fieldName = field.getAttribute('data-field-name') || field.name || 'Campo';
            const validationType = field.getAttribute('data-validation') || 'required';

            console.log(`   - Validando campo: ${fieldName} (${field.id}) = "${field.value}"`);

            const result = Validators.validateField(field, validationType, fieldName);

            if (!result.valid) {
                isValid = false;
                errors.push(result.message);
                console.log(`   ❌ ${result.message}`);

                // Scroll para o primeiro erro
                if (errors.length === 1) {
                    Utils.scrollToElement(field);
                }
            }
        });

        if (!isValid) {
            console.log(`❌ Validação FALHOU. Erros:`, errors);
            Notification.warning('Por favor, preencha todos os campos obrigatórios');
        } else {
            console.log(`✅ Validação PASSOU!`);
        }

        return isValid;
    },

    /**
     * Próximo step
     */
    nextStep() {
        if (this.validateCurrentStep()) {
            this.saveDraft();

            if (this.currentStep < this.totalSteps) {
                this.showStep(this.currentStep + 1);
                this.updateProgress();
            }
        }
    },

    /**
     * Step anterior
     */
    previousStep() {
        this.saveDraft();

        if (this.currentStep > 1) {
            this.showStep(this.currentStep - 1);
            this.updateProgress();
        }
    },

    /**
     * Coleta dados do formulário
     */
    collectFormData() {
        const formData = {};

        // Step 1 - Dados do Cliente
        formData.cliente_id = document.getElementById('cliente_id')?.value || '';
        formData.cliente = document.getElementById('cliente')?.value || '';
        formData.telefone_cliente = Masks.unmaskPhone(document.getElementById('telefone_cliente')?.value || '');
        formData.destinatario = document.getElementById('destinatario')?.value || '';
        formData.tipo_pedido = document.querySelector('input[name="tipo_pedido"]:checked')?.value || 'Entrega';
        // Coletar fonte - verificar input hidden primeiro (quando campo está desabilitado)
        const fontePedidoHidden = document.getElementById('fonte_pedido_id_hidden')?.value || '';
        const fontePedidoId = fontePedidoHidden || document.getElementById('fonte_pedido_id')?.value || '';
        formData.fonte_pedido_id = fontePedidoId ? parseInt(fontePedidoId) : null;

        // Step 2 - Produto e Agendamento
        formData.produto = document.getElementById('produto')?.value || '';
        formData.flores_cor = document.getElementById('flores_cor')?.value || '';
        formData.valor = document.getElementById('valor')?.value || '';
        formData.dia_entrega = Masks.unmaskDate(document.getElementById('dia_entrega')?.value || '');
        formData.horario = Masks.unmaskTime(document.getElementById('horario')?.value || '');

        // Step 3 - Logística (campos de endereço)
        formData.cep = Masks.unmaskCep(document.getElementById('cep')?.value || '');
        formData.rua = document.getElementById('rua')?.value || '';
        formData.numero = document.getElementById('numero')?.value || '';
        formData.bairro = document.getElementById('bairro')?.value || '';
        formData.cidade = document.getElementById('cidade')?.value || '';
        formData.endereco = document.getElementById('endereco')?.value || '';
        formData.obs_entrega = document.getElementById('obs_entrega')?.value || '';

        // Step 4 - Finalização
        formData.mensagem = document.getElementById('mensagem')?.value || '';
        formData.pagamento = document.getElementById('pagamento')?.value || '';
        formData.observacoes = document.getElementById('observacoes')?.value || '';
        formData.status_pagamento = document.getElementById('status_pagamento')?.value || '';

        return formData;
    },

    /**
     * Salva rascunho no localStorage
     */
    saveDraft() {
        const data = this.collectFormData();
        localStorage.setItem('form-draft', JSON.stringify(data));
    },

    /**
     * Carrega rascunho do localStorage
     */
    loadDraft() {
        const draft = localStorage.getItem('form-draft');

        if (draft) {
            try {
                const data = JSON.parse(draft);

                // Preencher campos
                Object.keys(data).forEach(key => {
                    const field = document.getElementById(key);
                    if (field) {
                        if (field.type === 'radio') {
                            const radio = document.querySelector(`input[name="${key}"][value="${data[key]}"]`);
                            if (radio) radio.checked = true;
                        } else {
                            field.value = data[key];
                        }
                    }
                });

                Notification.info('Rascunho anterior carregado');
            } catch (error) {
                console.error('Erro ao carregar rascunho:', error);
            }
        }
    },

    /**
     * Limpa rascunho
     */
    clearDraft() {
        localStorage.removeItem('form-draft');
        console.log('🗑️ Rascunho limpo');
    },

    /**
     * Submete formulário
     */
    async submitForm() {
        // Validar último step
        if (!this.validateCurrentStep()) {
            return;
        }

        // Coletar dados
        const formData = this.collectFormData();

        // Validação final
        if (!formData.telefone_cliente || !formData.destinatario || !formData.produto || !formData.dia_entrega || !formData.horario) {
            Notification.error('Campos obrigatórios não preenchidos');
            return;
        }

        try {
            Utils.showLoading();

            // Se está offline, salvar no IndexedDB
            if (!Utils.isOnline()) {
                await DB.savePendingPedido(formData);

                Notification.success('Pedido salvo offline! Será sincronizado quando voltar online.');

                this.resetForm();
                Router.navigate('/painel');
                return;
            }

            // Enviar para API
            const result = await API.createPedido(formData);

            if (result.success) {
                Notification.success('Pedido criado com sucesso! 🎉');

                this.clearDraft();
                this.resetForm();

                // Navegar para o painel após 1 segundo
                setTimeout(() => {
                    Router.navigate('/painel');
                }, 1000);
            } else {
                throw new Error(result.error || 'Erro ao criar pedido');
            }

        } catch (error) {
            console.error('Erro ao enviar pedido:', error);
            Notification.error(`Erro ao criar pedido: ${error.message}`);
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * Reseta formulário
     */
    resetForm() {
        // Limpar todos os campos
        document.querySelectorAll('input, textarea, select').forEach(field => {
            if (field.type === 'radio' || field.type === 'checkbox') {
                field.checked = false;
            } else {
                field.value = '';
            }

            // Limpar validações visuais
            Validators.clearFieldError(field);
        });

        // Resetar campo de fonte ao estado inicial (habilitado)
        const selectFonte = document.getElementById('fonte_pedido_id');
        if (selectFonte) {
            selectFonte.removeAttribute('disabled');
            selectFonte.classList.remove('bg-gray-100', 'text-gray-500', 'cursor-not-allowed', 'border-gray-200');
            selectFonte.classList.add('bg-white', 'text-gray-900', 'border-gray-300');
            
            // Remover input hidden se existir
            const hiddenInput = document.getElementById('fonte_pedido_id_hidden');
            if (hiddenInput) {
                hiddenInput.remove();
            }
            
            // Remover mensagem informativa se existir
            const infoMsg = selectFonte.parentElement.querySelector('.text-xs.text-gray-500');
            if (infoMsg && infoMsg.textContent.includes('Fonte selecionada')) {
                infoMsg.remove();
            }
        }

        // Resetar campos de cliente ao estado inicial (desabilitados)
        this.resetarCamposCliente();

        // Voltar para o primeiro step
        this.currentStep = 1;
        this.showStep(1);
        this.updateProgress();
    },

    /**
     * Preview dos dados antes de enviar
     */
    showPreview() {
        const data = this.collectFormData();

        const previewHtml = `
            <h2 class="text-2xl font-bold mb-4">Resumo do Pedido</h2>
            
            <div class="space-y-3 text-left">
                ${data.cliente ? `<p><strong>De:</strong> ${Utils.escapeHtml(data.cliente)}</p>` : ''}
                <p><strong>Telefone:</strong> ${Utils.formatPhone(data.telefone_cliente)}</p>
                <p><strong>Para:</strong> ${Utils.escapeHtml(data.destinatario)}</p>
                <p><strong>Tipo:</strong> ${Utils.translateType(data.tipo_pedido)}</p>
                <p><strong>Produto:</strong> ${Utils.escapeHtml(data.produto)}</p>
                ${data.flores_cor ? `<p><strong>Flores:</strong> ${Utils.escapeHtml(data.flores_cor)}</p>` : ''}
                ${data.valor ? `<p><strong>Valor:</strong> ${Utils.escapeHtml(data.valor)}</p>` : ''}
                <p><strong>Entrega:</strong> ${Utils.formatDate(data.dia_entrega)} às ${data.horario}</p>
                ${data.endereco ? `<p><strong>Endereço:</strong> ${Utils.escapeHtml(data.endereco)}</p>` : ''}
                ${data.mensagem ? `<p><strong>Mensagem:</strong> ${Utils.escapeHtml(data.mensagem)}</p>` : ''}
            </div>
        `;

        Modal.custom(previewHtml);
    },

    /**
     * Abre modal para escolher horário específico ou intervalo com calendário visual
     */
    async abrirModalHorario() {
        const campoHorario = document.getElementById('horario');
        const valorAtual = campoHorario?.value || '';
        const campoData = document.getElementById('dia_entrega');
        const dataEntrega = campoData?.value || '';
        
        // Detectar se já é um intervalo
        const isIntervalo = valorAtual.includes(' - ');
        let horarioInicial = '';
        let horarioFinal = '';
        
        if (isIntervalo) {
            const partes = valorAtual.split(' - ');
            horarioInicial = partes[0] || '';
            horarioFinal = partes[1] || '';
        } else {
            horarioInicial = valorAtual;
        }

        // Converter data para formato YYYY-MM-DD se necessário
        let dataFormatada = '';
        if (dataEntrega) {
            if (dataEntrega.includes('/')) {
                // Formato DD/MM/YYYY -> YYYY-MM-DD
                const [dia, mes, ano] = dataEntrega.split('/');
                dataFormatada = `${ano}-${mes}-${dia}`;
            } else {
                dataFormatada = dataEntrega;
            }
        }

        // Buscar pedidos da data se houver data selecionada
        let horariosOcupados = {};
        if (dataFormatada) {
            try {
                const response = await API.getPedidosPorData(dataFormatada);
                if (response.success && response.data && response.data.horarios) {
                    horariosOcupados = response.data.horarios;
                }
            } catch (error) {
                console.warn('Erro ao buscar pedidos da data:', error);
            }
        }

        // Gerar lista de horários de 15 em 15 minutos (07:30 até 18:30)
        const horarios = [];
        // Começar em 07:30
        horarios.push('07:30');
        // Continuar de 08:00 até 18:15 de 15 em 15 minutos
        for (let h = 8; h <= 18; h++) {
            for (let m = 0; m < 60; m += 15) {
                const hora = String(h).padStart(2, '0');
                const minuto = String(m).padStart(2, '0');
                horarios.push(`${hora}:${minuto}`);
            }
        }
        // Adicionar 18:30
        horarios.push('18:30');

        // Função para verificar se um horário está ocupado
        const getContadorHorario = (horario) => {
            // Verificar horário exato
            if (horariosOcupados[horario]) {
                return horariosOcupados[horario];
            }
            // Verificar se está dentro de algum intervalo
            for (const [horarioKey, count] of Object.entries(horariosOcupados)) {
                if (horarioKey.includes(' - ')) {
                    const [inicio, fim] = horarioKey.split(' - ');
                    if (this.horarioEstaNoIntervalo(horario, inicio, fim)) {
                        return count;
                    }
                }
            }
            return 0;
        };

        // Gerar HTML do calendário
        const calendarioHtml = horarios.map(horario => {
            const contador = getContadorHorario(horario);
            const ocupado = contador > 0;
            const selecionado = horario === horarioInicial || 
                               (isIntervalo && this.horarioEstaNoIntervalo(horario, horarioInicial, horarioFinal));
            
            // Estilo base: círculo pequeno com fundo claro e borda forte
            let classes = 'horario-btn relative w-12 h-12 rounded-full flex items-center justify-center text-xs font-semibold transition-all border-2';
            
            if (selecionado) {
                // Selecionado: fundo verde primário (paleta do app)
                classes += ' bg-primary border-primary text-white';
            } else if (ocupado) {
                // Ocupado: fundo amarelo claro com borda amarela (warning da paleta)
                classes += ' bg-amber-50 border-amber-500 text-gray-800 hover:bg-amber-100';
            } else {
                // Disponível: fundo branco com borda verde primária
                classes += ' bg-white border-primary text-gray-800 hover:bg-green-50 hover:border-secondary';
            }
            
            return `
                <button 
                    type="button"
                    class="${classes}"
                    data-horario="${horario}"
                    title="${horario}${ocupado ? ` - ${contador} pedido(s)` : ''}"
                >
                    ${horario}
                    ${contador > 0 ? `
                        <span class="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold shadow-sm">
                            ${contador}
                        </span>
                    ` : ''}
                </button>
            `;
        }).join('');

        const modalHtml = `
            <div class="space-y-4">
                <h3 class="text-xl font-bold text-gray-800 mb-2">Escolher Horário</h3>
                ${dataEntrega ? `
                    <p class="text-sm text-gray-600 mb-4">
                        <i class="fas fa-calendar mr-1"></i>
                        Data: ${dataEntrega}
                    </p>
                ` : `
                    <p class="text-sm text-yellow-600 mb-4">
                        <i class="fas fa-exclamation-triangle mr-1"></i>
                        Selecione uma data de entrega primeiro para ver horários ocupados
                    </p>
                `}
                
                <div class="space-y-3">
                    <div class="flex gap-4 mb-4">
                        <label class="flex items-center cursor-pointer">
                            <input type="radio" name="tipo_horario" value="especifico" ${!isIntervalo ? 'checked' : ''} 
                                class="mr-2 w-4 h-4 text-primary focus:ring-primary">
                            <span class="text-gray-700">Horário Específico</span>
                        </label>
                        <label class="flex items-center cursor-pointer">
                            <input type="radio" name="tipo_horario" value="intervalo" ${isIntervalo ? 'checked' : ''}
                                class="mr-2 w-4 h-4 text-primary focus:ring-primary">
                            <span class="text-gray-700">Intervalo de Horário</span>
                        </label>
                    </div>

                    <!-- Calendário de Horários -->
                    <div class="border-2 border-gray-200 rounded-lg p-4 bg-gray-50 max-h-96 overflow-y-auto">
                        <div class="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-10 gap-2" id="calendario-horarios">
                            ${calendarioHtml}
                        </div>
                    </div>

                    <!-- Preview da seleção -->
                    <div id="preview-selecao" class="bg-blue-50 p-3 rounded-lg hidden">
                        <p class="text-sm font-medium text-gray-700">
                            <i class="fas fa-clock mr-1"></i>
                            <span id="preview-texto"></span>
                        </p>
                    </div>
                </div>

                <div class="flex gap-3 justify-end pt-4 border-t border-gray-200">
                    <button 
                        data-modal-close
                        class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                    >
                        Cancelar
                    </button>
                    <button 
                        id="btn-confirmar-horario"
                        class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-secondary transition"
                    >
                        Confirmar
                    </button>
                </div>
            </div>
        `;

        const modal = Modal.custom(modalHtml);

        // Estado da seleção
        let tipoSelecionado = isIntervalo ? 'intervalo' : 'especifico';
        let horarioSelecionado = horarioInicial;
        let horarioInicialSelecionado = horarioInicial;
        let horarioFinalSelecionado = horarioFinal;

        // Atualizar preview
        const atualizarPreview = () => {
            const preview = modal.querySelector('#preview-selecao');
            const previewTexto = modal.querySelector('#preview-texto');
            
            if (tipoSelecionado === 'especifico' && horarioSelecionado) {
                preview.classList.remove('hidden');
                previewTexto.textContent = `Horário: ${horarioSelecionado}`;
            } else if (tipoSelecionado === 'intervalo' && horarioInicialSelecionado && horarioFinalSelecionado) {
                preview.classList.remove('hidden');
                previewTexto.textContent = `Intervalo: ${horarioInicialSelecionado} - ${horarioFinalSelecionado}`;
            } else {
                preview.classList.add('hidden');
            }
        };

        // Atualizar visual dos botões
        const atualizarBotoes = () => {
            modal.querySelectorAll('.horario-btn').forEach(btn => {
                const horario = btn.dataset.horario;
                let selecionado = false;
                let primeiroIntervalo = false;
                
                if (tipoSelecionado === 'especifico') {
                    selecionado = horario === horarioSelecionado;
                } else {
                    // Modo intervalo
                    if (horarioInicialSelecionado && !horarioFinalSelecionado) {
                        // Primeiro horário selecionado, mas ainda não o segundo
                        primeiroIntervalo = horario === horarioInicialSelecionado;
                    } else if (horarioInicialSelecionado && horarioFinalSelecionado) {
                        // Intervalo completo selecionado
                        selecionado = this.horarioEstaNoIntervalo(horario, horarioInicialSelecionado, horarioFinalSelecionado);
                    }
                }
                
                // Remover todas as classes de seleção e estado antigas
                btn.classList.remove(
                    'ring-4', 'ring-primary', 'ring-offset-2',
                    'bg-gray-700', 'bg-black', 'bg-primary', 'bg-white', 'bg-gray-50',
                    'bg-yellow-200', 'bg-yellow-50', 'bg-amber-50', 'bg-green-100', 'bg-green-50',
                    'border-gray-800', 'border-yellow-600', 'border-amber-500', 'border-black', 'border-primary', 'border-secondary',
                    'text-white', 'text-gray-800', 'text-gray-700',
                    'hover:bg-yellow-300', 'hover:bg-yellow-100', 'hover:bg-amber-100', 'hover:bg-green-200', 'hover:bg-green-50', 'hover:bg-gray-100', 
                    'hover:border-gray-900', 'hover:border-secondary'
                );
                
                // Adicionar classes apropriadas (prioridade: primeiro intervalo > selecionado > ocupado > livre)
                if (primeiroIntervalo || selecionado) {
                    // Primeiro horário do intervalo ou horário selecionado - fundo verde primário
                    btn.classList.add('bg-primary', 'border-primary', 'text-white');
                } else {
                    // Estado normal - restaurar cor baseada em ocupado/livre
                    const contador = getContadorHorario(horario);
                    if (contador > 0) {
                        // Ocupado: fundo amarelo claro com borda amarela (warning da paleta)
                        btn.classList.add('bg-amber-50', 'border-amber-500', 'text-gray-800', 'hover:bg-amber-100');
                    } else {
                        // Disponível: fundo branco com borda verde primária
                        btn.classList.add('bg-white', 'border-primary', 'text-gray-800', 'hover:bg-green-50', 'hover:border-secondary');
                    }
                }
            });
        };

        // Toggle entre específico e intervalo
        const radioButtons = modal.querySelectorAll('input[name="tipo_horario"]');
        radioButtons.forEach(radio => {
            radio.addEventListener('change', (e) => {
                tipoSelecionado = e.target.value;
                if (tipoSelecionado === 'especifico') {
                    horarioInicialSelecionado = '';
                    horarioFinalSelecionado = '';
                }
                atualizarBotoes();
                atualizarPreview();
            });
        });

        // Event listeners nos botões de horário
        modal.querySelectorAll('.horario-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const horario = btn.dataset.horario;
                
                if (tipoSelecionado === 'especifico') {
                    horarioSelecionado = horario;
                    atualizarBotoes();
                    atualizarPreview();
                } else {
                    // Modo intervalo: primeiro clique define início, segundo define fim
                    if (!horarioInicialSelecionado) {
                        horarioInicialSelecionado = horario;
                        horarioFinalSelecionado = '';
                    } else if (!horarioFinalSelecionado) {
                        // Validar que o final é depois do inicial
                        const [h1, m1] = horarioInicialSelecionado.split(':').map(Number);
                        const [h2, m2] = horario.split(':').map(Number);
                        const minutosInicial = h1 * 60 + m1;
                        const minutosFinal = h2 * 60 + m2;
                        
                        if (minutosFinal <= minutosInicial) {
                            Notification.warning('O horário final deve ser depois do horário inicial');
                            horarioInicialSelecionado = horario;
                            horarioFinalSelecionado = '';
                        } else {
                            horarioFinalSelecionado = horario;
                        }
                    } else {
                        // Resetar seleção
                        horarioInicialSelecionado = horario;
                        horarioFinalSelecionado = '';
                    }
                    // Sempre atualizar botões após mudança no intervalo
                    atualizarBotoes();
                    atualizarPreview();
                }
            });
        });

        // Botão confirmar
        const btnConfirmar = modal.querySelector('#btn-confirmar-horario');
        btnConfirmar.addEventListener('click', () => {
            if (tipoSelecionado === 'especifico') {
                if (!horarioSelecionado) {
                    Notification.warning('Por favor, selecione um horário');
                    return;
                }
                campoHorario.value = horarioSelecionado;
            } else {
                if (!horarioInicialSelecionado || !horarioFinalSelecionado) {
                    Notification.warning('Por favor, selecione um intervalo completo (início e fim)');
                    return;
                }
                campoHorario.value = `${horarioInicialSelecionado} - ${horarioFinalSelecionado}`;
            }

            Modal.close(modal);
        });

        // Atualizar visual inicial dos botões e preview
        atualizarBotoes();
        atualizarPreview();
    },

    /**
     * Verifica se um horário está dentro de um intervalo
     */
    horarioEstaNoIntervalo(horario, inicio, fim) {
        if (!inicio || !fim) return false;
        
        const [h, m] = horario.split(':').map(Number);
        const [h1, m1] = inicio.split(':').map(Number);
        const [h2, m2] = fim.split(':').map(Number);
        
        const minutos = h * 60 + m;
        const minutosInicio = h1 * 60 + m1;
        const minutosFim = h2 * 60 + m2;
        
        return minutos >= minutosInicio && minutos <= minutosFim;
    },

    /**
     * Mostra modal de seleção de fonte do pedido
     * @returns {Promise<number|null>} ID da fonte selecionada ou null se cancelado
     */
    async mostrarModalFonte() {
        try {
            // Carregar fontes disponíveis
            const response = await API.getFontesPedido();
            if (!response.success || !response.data) {
                console.warn('[FORM] Erro ao carregar fontes de pedido');
                return null;
            }

            const fontes = response.data.fontes || [];
            
            // Mapear fontes por nome (case-insensitive) para facilitar busca
            const fontesMap = {};
            fontes.forEach(fonte => {
                const nomeLower = fonte.nome.toLowerCase().trim();
                fontesMap[nomeLower] = fonte;
            });

            // Identificar IDs das fontes principais
            // WhatsApp deve buscar especificamente por "WhatsApp (Caio)" - tentar várias variações
            let fonteWhatsApp = null;
            const whatsappVariations = [
                'whatsapp (caio)',
                'whatsapp caio',
                'whatsapp(caio)',
                'whats app (caio)',
                'whats app caio',
                'whatsapp'
            ];
            for (const variation of whatsappVariations) {
                if (fontesMap[variation]) {
                    fonteWhatsApp = fontesMap[variation];
                    break;
                }
            }
            
            // Se não encontrou, buscar por qualquer fonte que contenha "whatsapp" e "caio"
            if (!fonteWhatsApp) {
                fonteWhatsApp = fontes.find(f => {
                    const nomeLower = f.nome.toLowerCase();
                    return nomeLower.includes('whatsapp') && nomeLower.includes('caio');
                }) || null;
            }
            
            const fonteCatalogo = fontesMap['catálogo'] || fontesMap['catalogo'] || null;
            const fonteSite = fontesMap['site'] || fontesMap['website'] || null;

            // Criar HTML do modal com cards visuais
            const modalHtml = `
                <div class="space-y-6">
                    <h3 class="text-2xl font-bold text-gray-800 text-center mb-4">
                        Selecione a Fonte do Pedido
                    </h3>
                    
                    <div class="space-y-4">
                        <!-- Card WhatsApp -->
                        <button 
                            type="button"
                            class="fonte-card w-full p-6 border-2 border-gray-300 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all text-left"
                            data-fonte-id="${fonteWhatsApp ? fonteWhatsApp.id : ''}"
                            data-fonte-nome="WhatsApp"
                            style="cursor: pointer;"
                        >
                            <div class="flex items-center gap-4">
                                <div class="flex-shrink-0">
                                    <i class="fab fa-whatsapp text-5xl text-green-500"></i>
                                </div>
                                <div class="flex-1">
                                    <h4 class="text-xl font-bold text-gray-800 mb-1">WhatsApp</h4>
                                    <p class="text-sm text-gray-600">Pedido recebido via WhatsApp</p>
                                </div>
                                <div class="flex-shrink-0">
                                    <i class="fas fa-chevron-right text-gray-400"></i>
                                </div>
                            </div>
                        </button>

                        <!-- Card Catálogo -->
                        <button 
                            type="button"
                            class="fonte-card w-full p-6 border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left"
                            data-fonte-id="${fonteCatalogo ? fonteCatalogo.id : ''}"
                            data-fonte-nome="Catálogo"
                            style="cursor: pointer;"
                        >
                            <div class="flex items-center gap-4">
                                <div class="flex-shrink-0">
                                    <i class="fas fa-book text-5xl text-blue-500"></i>
                                </div>
                                <div class="flex-1">
                                    <h4 class="text-xl font-bold text-gray-800 mb-1">Catálogo</h4>
                                    <p class="text-sm text-gray-600">Pedido do catálogo físico ou digital</p>
                                </div>
                                <div class="flex-shrink-0">
                                    <i class="fas fa-chevron-right text-gray-400"></i>
                                </div>
                            </div>
                        </button>

                        <!-- Card Site -->
                        <button 
                            type="button"
                            class="fonte-card w-full p-6 border-2 border-gray-300 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition-all text-left"
                            data-fonte-id="${fonteSite ? fonteSite.id : ''}"
                            data-fonte-nome="Site"
                            style="cursor: pointer;"
                        >
                            <div class="flex items-center gap-4">
                                <div class="flex-shrink-0">
                                    <i class="fas fa-globe text-5xl text-purple-500"></i>
                                </div>
                                <div class="flex-1">
                                    <h4 class="text-xl font-bold text-gray-800 mb-1">Site</h4>
                                    <p class="text-sm text-gray-600">Pedido recebido pelo site</p>
                                </div>
                                <div class="flex-shrink-0">
                                    <i class="fas fa-chevron-right text-gray-400"></i>
                                </div>
                            </div>
                        </button>
                    </div>

                    <div class="flex justify-end pt-4 border-t border-gray-200">
                        <button 
                            data-modal-close
                            class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                        >
                            Cancelar
                        </button>
                    </div>
                </div>
            `;

            return new Promise((resolve) => {
                const modal = Modal.custom(modalHtml, () => {
                    resolve(null); // Cancelado
                });

                // Adicionar event listeners nos cards
                modal.querySelectorAll('.fonte-card').forEach(card => {
                    card.addEventListener('click', () => {
                        const fonteId = card.dataset.fonteId;
                        const fonteNome = card.dataset.fonteNome;
                        
                        if (fonteId) {
                            Modal.close(modal);
                            resolve(parseInt(fonteId));
                        } else {
                            Notification.warning(`Fonte "${fonteNome}" não encontrada no sistema. Por favor, cadastre-a primeiro.`);
                        }
                    });
                });
            });
        } catch (error) {
            console.error('[FORM] Erro ao mostrar modal de fonte:', error);
            return null;
        }
    }
};

