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
        console.log('📝 Inicializando formulário');

        // Carregar dados do rascunho se existir
        this.loadDraft();

        // Configurar listeners
        this.setupListeners();

        // Configurar autocomplete de clientes
        this.setupClienteAutocomplete();

        // Carregar fontes de pedido
        this.carregarFontesPedido();

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

        console.log('🔧 Configurando listeners dos botões...');
        console.log('Botão Anterior:', btnAnterior ? 'Encontrado' : 'NÃO encontrado');
        console.log('Botão Próximo:', btnProximo ? 'Encontrado' : 'NÃO encontrado');
        console.log('Botão Finalizar:', btnFinalizar ? 'Encontrado' : 'NÃO encontrado');

        if (btnAnterior) {
            btnAnterior.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('⬅️ Clicou em Anterior');
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
                console.log('✅ Clicou em Finalizar');
                this.submitForm();
            });
            console.log('✅ Listener do botão Finalizar configurado!');
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
    },

    /**
     * Carrega fontes de pedido e popula o select
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
                    
                    console.log(`[FORM] ✅ ${fontes.length} fontes carregadas`);
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
        console.log('👥 Configurando autocomplete de clientes...');

        const inputAutocomplete = document.getElementById('cliente-autocomplete');
        const resultsElement = document.getElementById('autocomplete-results');
        const btnNovoCliente = document.getElementById('btn-novo-cliente');
        const btnHistorico = document.getElementById('btn-historico-cliente');

        if (!inputAutocomplete || !resultsElement) {
            console.log('⚠️ Elementos do autocomplete não encontrados');
            return;
        }

        // Inicializar autocomplete
        this.autocomplete = new AutocompleteCliente({
            inputElement: inputAutocomplete,
            resultsElement: resultsElement,
            onSelect: (cliente) => {
                console.log('✅ Cliente selecionado:', cliente);

                // Preencher campos
                document.getElementById('cliente_id').value = cliente.id;

                const campoCliente = document.getElementById('cliente');
                const campoTelefone = document.getElementById('telefone_cliente');

                campoCliente.value = cliente.nome;
                campoTelefone.value = cliente.telefone;

                // Habilitar campos (remover disabled/readonly e mudar estilo)
                campoCliente.removeAttribute('readonly');
                campoCliente.removeAttribute('disabled');
                campoCliente.classList.remove('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
                campoCliente.classList.add('bg-white', 'text-gray-900');

                campoTelefone.removeAttribute('readonly');
                campoTelefone.removeAttribute('disabled');
                campoTelefone.classList.remove('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
                campoTelefone.classList.add('bg-white', 'text-gray-900');

                // Mostrar botão de histórico
                if (btnHistorico) {
                    btnHistorico.classList.remove('hidden');
                    btnHistorico.dataset.clienteId = cliente.id;
                }

                // Carregar endereços do cliente
                this.carregarEnderecosCliente(cliente.id);

                Notification.show(`Cliente "${cliente.nome}" selecionado - Campos podem ser editados`, 'success');
            }
        });

        // Botão "Novo Cliente" - habilita campos para entrada manual
        if (btnNovoCliente) {
            // Adicionar suporte a touch para mobile
            const handleNovoCliente = () => {
                // Limpar valores
                document.getElementById('cliente_id').value = '';
                document.getElementById('cliente').value = '';
                document.getElementById('telefone_cliente').value = '';
                inputAutocomplete.value = '';

                // Habilitar campos para edição
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

                // Focar no campo nome
                campoCliente.focus();

                // Esconder botão de histórico
                if (btnHistorico) {
                    btnHistorico.classList.add('hidden');
                }

                // Esconder resultados do autocomplete
                if (this.autocomplete) {
                    this.autocomplete.hideResults();
                }

                Notification.show('Campos habilitados - Digite os dados do novo cliente', 'info');
            };

            // Suporte a click e touchstart para mobile
            btnNovoCliente.addEventListener('click', handleNovoCliente);
            btnNovoCliente.addEventListener('touchstart', (e) => {
                e.preventDefault();
                handleNovoCliente();
            });
        }

        // Botão "Ver Histórico"
        if (btnHistorico) {
            btnHistorico.addEventListener('click', async () => {
                const clienteId = btnHistorico.dataset.clienteId;
                if (clienteId) {
                    await this.mostrarHistoricoCliente(clienteId);
                }
            });
        }

        console.log('✅ Autocomplete configurado!');
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
                console.log('🔍 Clicou em Buscar CEP');
                this.buscarCep();
            });
            console.log('✅ Listener do botão Buscar CEP configurado!');
        }

        // Buscar CEP ao pressionar Enter no campo
        const cepInput = document.getElementById('cep');
        console.log('Campo CEP:', cepInput ? 'Encontrado' : 'NÃO encontrado');

        if (cepInput) {
            cepInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    console.log('⌨️ Enter no campo CEP');
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
        console.log('Botão Gerar Endereço:', btnGerarEndereco ? 'Encontrado' : 'NÃO encontrado');

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

            console.log('✅ CEP encontrado:', data);

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

        console.log('📍 Endereço gerado:', enderecoCompleto);
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

            console.log('🚚 Modo: Entrega - Campos de endereço visíveis');
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

        console.log(`✅ Mudou para Step ${step}`);
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
        console.log(`🔍 Validando Step ${this.currentStep}...`);

        const currentStepElement = document.getElementById(`step-${this.currentStep}`);
        if (!currentStepElement) {
            console.log('⚠️ Step element não encontrado');
            return true;
        }

        const requiredFields = currentStepElement.querySelectorAll('[required]');
        console.log(`📋 Campos obrigatórios encontrados: ${requiredFields.length}`);

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
            } else {
                console.log(`   ✅ OK`);
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
        const fontePedidoId = document.getElementById('fonte_pedido_id')?.value || '';
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
        console.log('💾 Rascunho salvo');
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

                console.log('✅ Rascunho carregado');
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
        console.log('🚀 submitForm() CHAMADO!');
        console.log('Step atual:', this.currentStep);

        // Validar último step
        if (!this.validateCurrentStep()) {
            console.log('❌ Validação falhou');
            return;
        }

        console.log('✅ Validação OK! Coletando dados...');

        // Coletar dados
        const formData = this.collectFormData();
        console.log('📦 Dados coletados:', formData);

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

        // Resetar campos de cliente ao estado inicial (desabilitados)
        this.resetarCamposCliente();

        // Voltar para o primeiro step
        this.currentStep = 1;
        this.showStep(1);
        this.updateProgress();

        console.log('🔄 Formulário resetado');
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
    }
};

