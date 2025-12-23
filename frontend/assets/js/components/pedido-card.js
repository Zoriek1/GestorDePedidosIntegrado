/**
 * Plante Uma Flor - PWA v3.0
 * Pedido Card Component - Card de pedido para o painel
 */

const PedidoCard = {
    /**
     * Cria HTML de um card de pedido
     */
    create(pedido, modoSelecao = false, selecionado = false) {
        const card = document.createElement('div');
        card.className = `pedido-card status-${pedido.status} ${selecionado ? 'selected border-2 border-primary' : ''}`;
        card.dataset.id = pedido.id;
        card.dataset.status = pedido.status;

        // Verificar se o pedido está atrasado
        const isOverdue = this.isOverdue(pedido);
        const overdueClass = isOverdue ? 'text-red-600 font-bold' : '';

        // Checkbox para seleção (apenas em modo seleção e se for Entrega)
        const checkboxHtml = modoSelecao && pedido.tipo_pedido === 'Entrega' ? `
            <div class="absolute top-3 right-3 z-10">
                <input 
                    type="checkbox" 
                    class="w-5 h-5 text-primary rounded focus:ring-primary cursor-pointer"
                    ${selecionado ? 'checked' : ''}
                    onchange="if(window.PainelManager) window.PainelManager.toggleSelecaoPedido(${pedido.id})"
                >
            </div>
        ` : '';

        // Indicador de impressão
        const impresso = pedido.impresso === true || pedido.impresso === 1;
        const indicadorImpressao = impresso
            ? '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 ml-2" title="Pedido já foi impresso"><i class="fas fa-check-circle mr-1"></i> Impresso</span>'
            : '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 ml-2" title="Pedido ainda não foi impresso"><i class="fas fa-print mr-1"></i> Não impresso</span>';

        card.innerHTML = `
            ${checkboxHtml}
            
            ${pedido.fonte_pedido ? `
            <div class="absolute -top-3 left-4 bg-white border border-gray-200 shadow-sm px-2 py-0.5 rounded-t-lg text-xs font-medium text-gray-600 z-0 flex items-center gap-1">
                <i class="fas fa-folder text-yellow-500"></i>
                ${Utils.escapeHtml(pedido.fonte_pedido)}
            </div>
            ` : ''}

            <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 mb-3 ${modoSelecao && pedido.tipo_pedido === 'Entrega' ? 'pr-8' : ''} relative z-10">
                <div class="flex-1 min-w-0">
                    <h3 class="text-lg font-bold text-gray-800 truncate flex items-center">
                        Pedido #${pedido.id}
                        ${indicadorImpressao}
                    </h3>
                    <p class="text-sm text-gray-600 break-words">
                        <i class="fas fa-calendar mr-1"></i>
                        ${Utils.formatDate(pedido.dia_entrega)} às ${pedido.horario}
                        ${isOverdue ? '<span class="text-red-600 ml-2 whitespace-nowrap"><i class="fas fa-exclamation-triangle"></i> Atrasado</span>' : ''}
                    </p>
                </div>
                <div class="flex flex-col items-end">
                    <span class="status-badge status-${pedido.status} self-start sm:self-auto">
                        ${Utils.translateStatus(pedido.status)}
                    </span>
                    ${pedido.fonte_pedido_nome ? `
                        <div class="text-xs text-gray-500 mt-1 flex items-center gap-1">
                            <i class="fas fa-folder"></i>
                            ${Utils.escapeHtml(pedido.fonte_pedido_nome)}
                        </div>
                    ` : ''}
                </div>
            </div>

            <div class="space-y-2 mb-4">
                ${pedido.cliente ? `
                    <p class="text-sm break-words">
                        <i class="fas fa-user text-gray-400 w-5 inline-block"></i>
                        <strong>De:</strong> <span class="break-words">${Utils.escapeHtml(pedido.cliente)}</span>
                    </p>
                ` : ''}
                
                <p class="text-sm break-words">
                    <i class="fas fa-gift text-gray-400 w-5 inline-block"></i>
                    <strong>Para:</strong> <span class="break-words">${Utils.escapeHtml(pedido.destinatario)}</span>
                </p>

                ${pedido.telefone_cliente ? `
                    <p class="text-sm break-words">
                        <i class="fas fa-phone text-gray-400 w-5 inline-block"></i>
                        <span class="break-words">${Utils.formatPhone(pedido.telefone_cliente)}</span>
                    </p>
                ` : ''}

                <p class="text-sm break-words">
                    <i class="fas fa-flower text-gray-400 w-5 inline-block"></i>
                    <strong>Produto:</strong> <span class="break-words">${Utils.escapeHtml(Utils.truncate(pedido.produto, 60))}</span>
                </p>

                ${pedido.tipo_pedido ? `
                    <p class="text-sm break-words">
                        <i class="fas ${pedido.tipo_pedido === 'Entrega' ? 'fa-truck' : 'fa-store'} text-gray-400 w-5 inline-block"></i>
                        <span class="break-words">${Utils.translateType(pedido.tipo_pedido)}</span>
                    </p>
                ` : ''}

                ${pedido.tipo_pedido === 'Entrega' && pedido.endereco ? `
                    <div class="entrega-section bg-gray-50 rounded-lg p-3 mt-2 border border-gray-200">
                        <!-- Endereço -->
                        <div class="entrega-item mb-2">
                            <div class="flex items-start gap-2">
                                <i class="fas fa-map-marker-alt text-gray-400 mt-0.5 flex-shrink-0"></i>
                                <span class="text-sm text-gray-700 break-words flex-1">${Utils.escapeHtml(pedido.endereco)}</span>
                            </div>
                        </div>
                        
                        <!-- Distância e Frete em grid -->
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <!-- Distância -->
                            <div class="entrega-info">
                                <div class="flex items-center justify-between gap-2">
                                    <div class="flex items-center gap-1.5">
                                        <i class="fas fa-route text-yellow-500"></i>
                                        <span class="text-sm font-semibold text-gray-700">
                                            ${pedido.distancia_km !== null && pedido.distancia_km !== undefined ? PedidoCard.formatarDistancia(pedido.distancia_km) : '-'}
                                        </span>
                                        ${pedido.aproximado ? `
                                            <i class="fas fa-exclamation-triangle text-orange-500 text-xs" 
                                               title="⚠️ Distância aproximada - ${pedido.aviso || 'Endereço fora da área de mapeamento'}"
                                               style="cursor: help;">
                                            </i>
                                        ` : ''}
                                    </div>
                                    <button 
                                        class="entrega-recalcular-btn"
                                        onclick="PedidoCard.calcularDistancia(${pedido.id}, ${pedido.distancia_km !== null && pedido.distancia_km !== undefined ? 'true' : 'false'})"
                                        title="${pedido.distancia_km !== null && pedido.distancia_km !== undefined ? 'Recalcular distância' : 'Calcular distância'}"
                                    >
                                        Recalcular
                                    </button>
                                </div>
                                ${pedido.aproximado ? `
                                    <p class="text-xs text-orange-600 italic mt-1">
                                        ⚠️ Distância não exata
                                    </p>
                                ` : ''}
                            </div>
                            
                            <!-- Frete -->
                            ${pedido.distancia_km !== null && pedido.distancia_km !== undefined ? `
                            <div class="entrega-info">
                                <div class="flex items-center justify-between gap-2">
                                    <div class="flex items-center gap-1.5">
                                        <i class="fas fa-dollar-sign text-green-500"></i>
                                        <span class="text-sm font-semibold text-gray-700">
                                            ${pedido.taxa_entrega !== null && pedido.taxa_entrega !== undefined ? `R$ ${pedido.taxa_entrega.toFixed(2)}` : '-'}
                                        </span>
                                    </div>
                                    <button 
                                        class="entrega-recalcular-btn"
                                        onclick="PedidoCard.calcularTaxa(${pedido.id}, ${pedido.taxa_entrega !== null && pedido.taxa_entrega !== undefined ? 'true' : 'false'})"
                                        title="${pedido.taxa_entrega !== null && pedido.taxa_entrega !== undefined ? 'Recalcular frete' : 'Calcular frete'}"
                                    >
                                        Recalcular
                                    </button>
                                </div>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}

                ${pedido.valor ? `
                    <p class="text-sm break-words">
                        <i class="fas fa-dollar-sign text-gray-400 w-5 inline-block"></i>
                        <span class="break-words">${Utils.escapeHtml(pedido.valor)}</span>
                    </p>
                ` : ''}
            </div>

            <div class="flex flex-col sm:flex-row gap-2 pt-3 border-t border-gray-200">
                <select 
                    class="w-full sm:flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-primary"
                    onchange="PainelManager.changeStatus(${pedido.id}, this.value)"
                >
                    <option value="">Alterar Status</option>
                    <option value="agendado" ${pedido.status === 'agendado' ? 'selected' : ''}>Agendado</option>
                    <option value="em_producao" ${pedido.status === 'em_producao' ? 'selected' : ''}>Em Produção</option>
                    <option value="pronto_entrega" ${pedido.status === 'pronto_entrega' ? 'selected' : ''}>Pronto para Entrega</option>
                    <option value="em_rota" ${pedido.status === 'em_rota' ? 'selected' : ''}>Em Rota</option>
                    <option value="pronto_retirada" ${pedido.status === 'pronto_retirada' ? 'selected' : ''}>Pronto para Retirada</option>
                    <option value="concluido" ${pedido.status === 'concluido' ? 'selected' : ''}>Concluído</option>
                </select>

                <div class="flex flex-wrap gap-2 w-full sm:w-auto">
                    <button 
                        class="flex-1 sm:flex-none px-3 py-2 bg-primary text-white rounded hover:bg-secondary transition text-sm"
                        onclick="PedidoCard.printPedido(${pedido.id})"
                        title="Imprimir Pedido"
                    >
                        <i class="fas fa-print"></i>
                        <span class="hidden sm:inline ml-1">Imprimir</span>
                    </button>

                    <button 
                        class="flex-1 sm:flex-none px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition text-sm"
                        onclick="PedidoCard.showDetails(${pedido.id})"
                        title="Ver detalhes"
                    >
                        <i class="fas fa-eye"></i>
                        <span class="hidden sm:inline ml-1">Ver</span>
                    </button>

                    <button 
                        class="flex-1 sm:flex-none px-3 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition text-sm"
                        onclick="PedidoCard.editPedido(${pedido.id})"
                        title="Editar pedido"
                    >
                        <i class="fas fa-edit"></i>
                        <span class="hidden sm:inline ml-1">Editar</span>
                    </button>

                    <button 
                        class="flex-1 sm:flex-none px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition text-sm"
                        onclick="PainelManager.deletePedido(${pedido.id})"
                        title="Deletar pedido"
                    >
                        <i class="fas fa-trash"></i>
                        <span class="hidden sm:inline ml-1">Deletar</span>
                    </button>
                </div>
            </div>
        `;

        return card;
    },

    /**
     * Abre modal para editar pedido e salva via API
     */
    async editPedido(pedidoId) {
        try {
            Utils.showLoading();

            // Carregar dados atuais do pedido e fontes
            const [pedidoResult, fontesResult] = await Promise.all([
                API.getPedido(pedidoId),
                API.getFontesPedido()
            ]);

            if (!pedidoResult.success) {
                throw new Error(pedidoResult.error || 'Erro ao carregar pedido');
            }

            const p = pedidoResult.data.pedido;
            const fontes = fontesResult.success && fontesResult.data.success ? fontesResult.data.fontes : [];
            
            // Gerar opções de fontes
            const fontesOptions = fontes.map(fonte => 
                `<option value="${fonte.id}" ${p.fonte_pedido_id === fonte.id ? 'selected' : ''}>${Utils.escapeHtml(fonte.nome)}</option>`
            ).join('');

            // Conteúdo do modal com formulário compacto e layout fixo
            const modalHtml = `
                <div class="flex flex-col h-full max-h-[90vh] overflow-hidden">
                    <!-- Header Fixo -->
                    <div class="flex justify-between items-center p-4 border-b bg-white rounded-t-lg shrink-0">
                        <h2 class="text-xl font-bold text-gray-800 flex items-center gap-2">
                            <i class="fas fa-edit text-primary"></i>
                            Editar Pedido #${p.id}
                        </h2>
                        <button data-modal-close class="text-gray-400 hover:text-gray-600 p-2 rounded-full hover:bg-gray-100 transition">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>

                    <!-- Body Scrollable -->
                    <div class="flex-1 overflow-y-auto overflow-x-hidden p-4 bg-gray-50">
                        <form id="form-editar-pedido" class="space-y-4">
                            <!-- Seção 1: Dados Básicos -->
                            <div class="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
                                <h3 class="text-sm font-semibold text-gray-700 mb-3 border-b pb-2">Dados do Cliente</h3>
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Fonte do Pedido</label>
                                        <select id="edit-fonte" class="w-full border rounded px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none">
                                            <option value="">Selecione...</option>
                                            ${fontesOptions}
                                        </select>
                                    </div>
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Tipo</label>
                                        <select id="edit-tipo" class="w-full border rounded px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none">
                                            <option value="Entrega" ${p.tipo_pedido === 'Entrega' ? 'selected' : ''}>Entrega</option>
                                            <option value="Retirada" ${p.tipo_pedido === 'Retirada' ? 'selected' : ''}>Retirada</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">De (Remetente)</label>
                                        <input id="edit-cliente" type="text" class="w-full border rounded px-3 py-2 text-sm" value="${Utils.escapeHtml(p.cliente || '')}">
                                    </div>
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Telefone</label>
                                        <input id="edit-telefone" type="text" class="w-full border rounded px-3 py-2 text-sm" value="${Utils.escapeHtml(p.telefone_cliente || '')}">
                                    </div>
                                    <div class="md:col-span-2">
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Para (Destinatário)</label>
                                        <input id="edit-destinatario" type="text" class="w-full border rounded px-3 py-2 text-sm" value="${Utils.escapeHtml(p.destinatario || '')}">
                                    </div>
                                </div>
                            </div>

                            <!-- Seção 2: Produto -->
                            <div class="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
                                <h3 class="text-sm font-semibold text-gray-700 mb-3 border-b pb-2">Produto e Entrega</h3>
                                <div class="space-y-3">
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Produto</label>
                                        <textarea id="edit-produto" class="w-full border rounded px-3 py-2 text-sm" rows="2">${Utils.escapeHtml(p.produto || '')}</textarea>
                                    </div>
                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        <div>
                                            <label class="block text-xs font-medium text-gray-600 mb-1">Flores e Cor</label>
                                            <input id="edit-flores" type="text" class="w-full border rounded px-3 py-2 text-sm" value="${Utils.escapeHtml(p.flores_cor || '')}">
                                        </div>
                                        <div>
                                            <label class="block text-xs font-medium text-gray-600 mb-1">Valor</label>
                                            <input id="edit-valor" type="text" class="w-full border rounded px-3 py-2 text-sm" value="${Utils.escapeHtml(p.valor || '')}">
                                        </div>
                                    </div>
                                    <div class="grid grid-cols-2 gap-3">
                                        <div>
                                            <label class="block text-xs font-medium text-gray-600 mb-1">Dia</label>
                                            <input id="edit-dia" type="date" class="w-full border rounded px-3 py-2 text-sm" value="${Utils.escapeHtml(p.dia_entrega || '')}">
                                        </div>
                                        <div>
                                            <label class="block text-xs font-medium text-gray-600 mb-1">Horário</label>
                                            <div class="flex gap-2">
                                                <input id="edit-horario" type="text" class="flex-1 border rounded px-3 py-2 text-sm" value="${Utils.escapeHtml(p.horario || '')}" placeholder="14:30 ou 14:00 - 16:00">
                                                <button type="button" id="btn-modal-horario-edit"
                                                    class="px-3 py-2 bg-primary text-white rounded-lg hover:bg-secondary transition text-sm flex items-center justify-center"
                                                    title="Escolher horário">
                                                    <i class="fas fa-calendar-alt"></i>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Seção 3: Endereço -->
                            <div class="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
                                <h3 class="text-sm font-semibold text-gray-700 mb-3 border-b pb-2">Endereço de Entrega</h3>
                                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">CEP</label>
                                        <input id="edit-cep" type="text" class="w-full border rounded px-2 py-1.5 text-sm" value="${Utils.escapeHtml(p.cep || '')}">
                                    </div>
                                    <div class="col-span-2">
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Rua</label>
                                        <input id="edit-rua" type="text" class="w-full border rounded px-2 py-1.5 text-sm" value="${Utils.escapeHtml(p.rua || '')}">
                                    </div>
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Número</label>
                                        <input id="edit-numero" type="text" class="w-full border rounded px-2 py-1.5 text-sm" value="${Utils.escapeHtml(p.numero || '')}">
                                    </div>
                                </div>
                                <div class="grid grid-cols-2 gap-3 mb-3">
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Bairro</label>
                                        <input id="edit-bairro" type="text" class="w-full border rounded px-2 py-1.5 text-sm" value="${Utils.escapeHtml(p.bairro || '')}">
                                    </div>
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Cidade</label>
                                        <input id="edit-cidade" type="text" class="w-full border rounded px-2 py-1.5 text-sm" value="${Utils.escapeHtml(p.cidade || 'Goiânia')}">
                                    </div>
                                </div>
                                <div>
                                    <label class="block text-xs font-medium text-gray-600 mb-1">Endereço Completo</label>
                                    <textarea id="edit-endereco" class="w-full border rounded px-2 py-1.5 text-sm bg-gray-50" rows="2">${Utils.escapeHtml(p.endereco || '')}</textarea>
                                </div>
                                <div class="mt-3">
                                    <label class="block text-xs font-medium text-gray-600 mb-1">Como Entregar / Observações</label>
                                    <textarea id="edit-obs_entrega" class="w-full border rounded px-3 py-2 text-sm" rows="2">${Utils.escapeHtml(p.obs_entrega || '')}</textarea>
                                </div>
                            </div>

                            <!-- Seção 4: Finalização -->
                            <div class="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
                                <h3 class="text-sm font-semibold text-gray-700 mb-3 border-b pb-2">Finalização</h3>
                                <div class="space-y-3">
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Carta/Mensagem</label>
                                        <textarea id="edit-mensagem" class="w-full border rounded px-3 py-2 text-sm" rows="2">${Utils.escapeHtml(p.mensagem || '')}</textarea>
                                    </div>
                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        <div>
                                            <label class="block text-xs font-medium text-gray-600 mb-1">Forma de Pagamento</label>
                                            <select id="edit-pagamento" class="w-full border rounded px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none">
                                                <option value="">Selecione...</option>
                                                <option value="Dinheiro" ${p.pagamento === 'Dinheiro' ? 'selected' : ''}>Dinheiro</option>
                                                <option value="Cartão de Crédito" ${p.pagamento === 'Cartão de Crédito' ? 'selected' : ''}>Cartão de Crédito</option>
                                                <option value="Cartão de Débito" ${p.pagamento === 'Cartão de Débito' ? 'selected' : ''}>Cartão de Débito</option>
                                                <option value="PIX" ${p.pagamento === 'PIX' ? 'selected' : ''}>PIX</option>
                                                <option value="Transferência" ${p.pagamento === 'Transferência' ? 'selected' : ''}>Transferência</option>
                                                <option value="Boleto" ${p.pagamento === 'Boleto' ? 'selected' : ''}>Boleto</option>
                                                <option value="A Combinar" ${p.pagamento === 'A Combinar' ? 'selected' : ''}>A Combinar</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label class="block text-xs font-medium text-gray-600 mb-1">Status Pagamento</label>
                                            <select id="edit-status-pagamento" class="w-full border rounded px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none">
                                                <option value="">Selecione...</option>
                                                <option value="PAGAMENTO REALIZADO" ${p.status_pagamento === 'PAGAMENTO REALIZADO' ? 'selected' : ''}>PAGAMENTO REALIZADO</option>
                                                <option value="50% PAGO" ${p.status_pagamento === '50% PAGO' ? 'selected' : ''}>50% PAGO</option>
                                                <option value="PAGAMENTO PENDENTE" ${p.status_pagamento === 'PAGAMENTO PENDENTE' ? 'selected' : ''}>PAGAMENTO PENDENTE</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">Observações Gerais</label>
                                        <textarea id="edit-observacoes" class="w-full border rounded px-3 py-2 text-sm" rows="2">${Utils.escapeHtml(p.observacoes || '')}</textarea>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>

                    <!-- Footer Fixo -->
                    <div class="p-4 border-t bg-white rounded-b-lg shrink-0 flex justify-end gap-3">
                        <button type="button" class="btn btn-secondary" data-modal-close>Cancelar</button>
                        <button type="button" id="btn-salvar-edicao" class="btn btn-primary">
                            <i class="fas fa-save mr-2"></i>Salvar Alterações
                        </button>
                    </div>
                </div>
            `;

            const overlay = Modal.custom(modalHtml);

            // Função para salvar pedido
            const salvarPedido = async () => {
                try {
                    Utils.showLoading();

                    // Coletar dados (incluindo campos de endereço separados)
                    const fontePedidoId = overlay.querySelector('#edit-fonte').value;
                    const data = {
                        fonte_pedido_id: fontePedidoId ? parseInt(fontePedidoId) : null,
                        cliente: overlay.querySelector('#edit-cliente').value.trim(),
                        telefone_cliente: overlay.querySelector('#edit-telefone').value.trim(),
                        destinatario: overlay.querySelector('#edit-destinatario').value.trim(),
                        tipo_pedido: overlay.querySelector('#edit-tipo').value,
                        produto: overlay.querySelector('#edit-produto').value.trim(),
                        flores_cor: overlay.querySelector('#edit-flores').value.trim(),
                        valor: overlay.querySelector('#edit-valor').value.trim(),
                        dia_entrega: overlay.querySelector('#edit-dia').value, // YYYY-MM-DD
                        horario: overlay.querySelector('#edit-horario').value,
                        // Campos de endereço separados
                        cep: overlay.querySelector('#edit-cep').value.trim().replace(/\D/g, ''),
                        rua: overlay.querySelector('#edit-rua').value.trim(),
                        numero: overlay.querySelector('#edit-numero').value.trim(),
                        bairro: overlay.querySelector('#edit-bairro').value.trim(),
                        cidade: overlay.querySelector('#edit-cidade').value.trim() || 'Goiânia',
                        endereco: overlay.querySelector('#edit-endereco').value.trim(),
                        obs_entrega: overlay.querySelector('#edit-obs_entrega').value.trim(),
                        mensagem: overlay.querySelector('#edit-mensagem').value.trim(),
                        pagamento: overlay.querySelector('#edit-pagamento').value.trim(),
                        status_pagamento: overlay.querySelector('#edit-status-pagamento').value.trim(),
                        observacoes: overlay.querySelector('#edit-observacoes').value.trim()
                    };

                    console.log('[EDITAR] Enviando dados:', data);
                    const update = await API.updatePedido(pedidoId, data);
                    
                    if (!update.success) {
                        console.error('[EDITAR] Erro na resposta:', update);
                        throw new Error(update.error || update.data?.error || 'Erro ao atualizar pedido');
                    }

                    Notification.success('Pedido atualizado com sucesso!');
                    Modal.close(overlay);

                    // Recarregar lista e stats (com fallback para reload da rota)
                    if (typeof window !== 'undefined' && window.PainelManager && typeof window.PainelManager.loadPedidos === 'function') {
                        await window.PainelManager.loadPedidos(true);
                        if (typeof window.PainelManager.loadStats === 'function') {
                            await window.PainelManager.loadStats();
                        }
                    } else if (typeof window !== 'undefined' && window.Router && typeof window.Router.reload === 'function') {
                        window.Router.reload();
                    }

                } catch (err) {
                    console.error('[EDITAR] Erro ao salvar edição:', err);
                    const errorMessage = err.message || err.toString() || 'Erro desconhecido ao salvar pedido';
                    Notification.error(`Erro ao salvar: ${errorMessage}`);
                } finally {
                    Utils.hideLoading();
                }
            };

            // Listener de submit do formulário
            const form = overlay.querySelector('#form-editar-pedido');
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await salvarPedido();
            });

            // Botão de salvar - chamar função diretamente
            const btnSalvar = overlay.querySelector('#btn-salvar-edicao');
            if (btnSalvar) {
                btnSalvar.addEventListener('click', async (e) => {
                    e.preventDefault();
                    await salvarPedido();
                });
            } else {
                console.warn('[EDITAR] Botão btn-salvar-edicao não encontrado');
            }

            // Configurar modal de horário no editor
            const campoHorarioEdit = overlay.querySelector('#edit-horario');
            const btnModalHorarioEdit = overlay.querySelector('#btn-modal-horario-edit');
            const campoDataEdit = overlay.querySelector('#edit-dia');
            
            const abrirModalHorarioEdit = async () => {
                const valorAtual = campoHorarioEdit?.value || '';
                const dataEntrega = campoDataEdit?.value || '';
                
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
                    // Campo de data já vem no formato YYYY-MM-DD
                    dataFormatada = dataEntrega;
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
                horarios.push('07:30');
                for (let h = 8; h <= 18; h++) {
                    for (let m = 0; m < 60; m += 15) {
                        const hora = String(h).padStart(2, '0');
                        const minuto = String(m).padStart(2, '0');
                        horarios.push(`${hora}:${minuto}`);
                    }
                }
                horarios.push('18:30');

                // Função para verificar se um horário está ocupado
                const getContadorHorario = (horario) => {
                    if (horariosOcupados[horario]) {
                        return horariosOcupados[horario];
                    }
                    for (const [horarioKey, count] of Object.entries(horariosOcupados)) {
                        if (horarioKey.includes(' - ')) {
                            const [inicio, fim] = horarioKey.split(' - ');
                            if (horarioEstaNoIntervalo(horario, inicio, fim)) {
                                return count;
                            }
                        }
                    }
                    return 0;
                };

                // Função auxiliar para verificar se horário está no intervalo
                const horarioEstaNoIntervalo = (horario, inicio, fim) => {
                    if (!inicio || !fim) return false;
                    const [h, m] = horario.split(':').map(Number);
                    const [h1, m1] = inicio.split(':').map(Number);
                    const [h2, m2] = fim.split(':').map(Number);
                    const minutos = h * 60 + m;
                    const minutosInicio = h1 * 60 + m1;
                    const minutosFim = h2 * 60 + m2;
                    return minutos >= minutosInicio && minutos <= minutosFim;
                };

                // Gerar HTML do calendário
                const calendarioHtml = horarios.map(horario => {
                    const contador = getContadorHorario(horario);
                    const ocupado = contador > 0;
                    const selecionado = horario === horarioInicial || 
                                       (isIntervalo && horarioEstaNoIntervalo(horario, horarioInicial, horarioFinal));
                    
                    let classes = 'horario-btn relative w-12 h-12 rounded-full flex items-center justify-center text-xs font-semibold transition-all border-2';
                    
                    if (selecionado) {
                        classes += ' bg-primary border-primary text-white';
                    } else if (ocupado) {
                        classes += ' bg-amber-50 border-amber-500 text-gray-800 hover:bg-amber-100';
                    } else {
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
                                Data: ${new Date(dataEntrega + 'T00:00:00').toLocaleDateString('pt-BR')}
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
                                    <input type="radio" name="tipo_horario_edit" value="especifico" ${!isIntervalo ? 'checked' : ''} 
                                        class="mr-2 w-4 h-4 text-primary focus:ring-primary">
                                    <span class="text-gray-700">Horário Específico</span>
                                </label>
                                <label class="flex items-center cursor-pointer">
                                    <input type="radio" name="tipo_horario_edit" value="intervalo" ${isIntervalo ? 'checked' : ''}
                                        class="mr-2 w-4 h-4 text-primary focus:ring-primary">
                                    <span class="text-gray-700">Intervalo de Horário</span>
                                </label>
                            </div>

                            <!-- Calendário de Horários -->
                            <div class="border-2 border-gray-200 rounded-lg p-4 bg-gray-50 max-h-96 overflow-y-auto">
                                <div class="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-10 gap-2" id="calendario-horarios-edit">
                                    ${calendarioHtml}
                                </div>
                            </div>

                            <!-- Preview da seleção -->
                            <div id="preview-selecao-edit" class="bg-blue-50 p-3 rounded-lg hidden">
                                <p class="text-sm font-medium text-gray-700">
                                    <i class="fas fa-clock mr-1"></i>
                                    <span id="preview-texto-edit"></span>
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
                                id="btn-confirmar-horario-edit"
                                class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-secondary transition"
                            >
                                Confirmar
                            </button>
                        </div>
                    </div>
                `;

                const modalHorario = Modal.custom(modalHtml);

                // Estado da seleção
                let tipoSelecionado = isIntervalo ? 'intervalo' : 'especifico';
                let horarioSelecionado = horarioInicial;
                let horarioInicialSelecionado = horarioInicial;
                let horarioFinalSelecionado = horarioFinal;

                // Atualizar preview
                const atualizarPreview = () => {
                    const preview = modalHorario.querySelector('#preview-selecao-edit');
                    const previewTexto = modalHorario.querySelector('#preview-texto-edit');
                    
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
                    modalHorario.querySelectorAll('.horario-btn').forEach(btn => {
                        const horario = btn.dataset.horario;
                        let selecionado = false;
                        let primeiroIntervalo = false;
                        
                        if (tipoSelecionado === 'especifico') {
                            selecionado = horario === horarioSelecionado;
                        } else {
                            if (horarioInicialSelecionado && !horarioFinalSelecionado) {
                                primeiroIntervalo = horario === horarioInicialSelecionado;
                            } else if (horarioInicialSelecionado && horarioFinalSelecionado) {
                                selecionado = horarioEstaNoIntervalo(horario, horarioInicialSelecionado, horarioFinalSelecionado);
                            }
                        }
                        
                        btn.classList.remove(
                            'ring-4', 'ring-primary', 'ring-offset-2',
                            'bg-gray-700', 'bg-black', 'bg-primary', 'bg-white', 'bg-gray-50',
                            'bg-yellow-200', 'bg-yellow-50', 'bg-amber-50', 'bg-green-100', 'bg-green-50',
                            'border-gray-800', 'border-yellow-600', 'border-amber-500', 'border-black', 'border-primary', 'border-secondary',
                            'text-white', 'text-gray-800', 'text-gray-700',
                            'hover:bg-yellow-300', 'hover:bg-yellow-100', 'hover:bg-amber-100', 'hover:bg-green-200', 'hover:bg-green-50', 'hover:bg-gray-100', 
                            'hover:border-gray-900', 'hover:border-secondary'
                        );
                        
                        if (primeiroIntervalo || selecionado) {
                            btn.classList.add('bg-primary', 'border-primary', 'text-white');
                        } else {
                            const contador = getContadorHorario(horario);
                            if (contador > 0) {
                                btn.classList.add('bg-amber-50', 'border-amber-500', 'text-gray-800', 'hover:bg-amber-100');
                            } else {
                                btn.classList.add('bg-white', 'border-primary', 'text-gray-800', 'hover:bg-green-50', 'hover:border-secondary');
                            }
                        }
                    });
                };

                // Toggle entre específico e intervalo
                const radioButtons = modalHorario.querySelectorAll('input[name="tipo_horario_edit"]');
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
                modalHorario.querySelectorAll('.horario-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const horario = btn.dataset.horario;
                        
                        if (tipoSelecionado === 'especifico') {
                            horarioSelecionado = horario;
                            atualizarBotoes();
                            atualizarPreview();
                        } else {
                            if (!horarioInicialSelecionado) {
                                horarioInicialSelecionado = horario;
                                horarioFinalSelecionado = '';
                            } else if (!horarioFinalSelecionado) {
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
                                horarioInicialSelecionado = horario;
                                horarioFinalSelecionado = '';
                            }
                            atualizarBotoes();
                            atualizarPreview();
                        }
                    });
                });

                // Botão confirmar
                const btnConfirmar = modalHorario.querySelector('#btn-confirmar-horario-edit');
                btnConfirmar.addEventListener('click', () => {
                    if (tipoSelecionado === 'especifico') {
                        if (!horarioSelecionado) {
                            Notification.warning('Por favor, selecione um horário');
                            return;
                        }
                        campoHorarioEdit.value = horarioSelecionado;
                    } else {
                        if (!horarioInicialSelecionado || !horarioFinalSelecionado) {
                            Notification.warning('Por favor, selecione um intervalo completo (início e fim)');
                            return;
                        }
                        campoHorarioEdit.value = `${horarioInicialSelecionado} - ${horarioFinalSelecionado}`;
                    }

                    Modal.close(modalHorario);
                });

                // Atualizar visual inicial dos botões e preview
                atualizarBotoes();
                atualizarPreview();
            };

            // Configurar listeners
            if (btnModalHorarioEdit) {
                btnModalHorarioEdit.addEventListener('click', () => {
                    abrirModalHorarioEdit();
                });
            }

            if (campoHorarioEdit) {
                campoHorarioEdit.addEventListener('click', () => {
                    abrirModalHorarioEdit();
                });
            }

        } catch (error) {
            console.error('Erro ao abrir modal de edição:', error);
            Notification.error('Erro ao abrir editor do pedido');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * Verifica se pedido está atrasado
     */
    isOverdue(pedido) {
        if (pedido.status === 'concluido') {
            return false;
        }

        try {
            const now = new Date();
            const deliveryDate = new Date(pedido.dia_entrega + 'T' + pedido.horario);
            return now > deliveryDate;
        } catch (error) {
            return false;
        }
    },

    /**
     * Formata distância para exibição
     */
    formatarDistancia(distanciaKm) {
        if (distanciaKm === null || distanciaKm === undefined) {
            return '';
        }
        if (distanciaKm < 1) {
            return `${Math.round(distanciaKm * 1000)} m`;
        }
        return `${distanciaKm.toFixed(1)} km`;
    },

    /**
     * Retorna cor baseada na distância (para classes Tailwind)
     */
    getCorDistancia(distanciaKm) {
        if (distanciaKm === null || distanciaKm === undefined) {
            return 'gray';
        }
        if (distanciaKm <= 5) return 'green';   // Perto
        if (distanciaKm <= 15) return 'yellow'; // Médio
        return 'red';                           // Longe
    },

    /**
     * Mostra detalhes completos do pedido
     */
    async showDetails(pedidoId) {
        try {
            Utils.showLoading();

            const result = await API.getPedido(pedidoId);

            if (!result.success) {
                throw new Error(result.error || 'Erro ao carregar pedido');
            }

            const pedido = result.data.pedido;

            const modalContent = `
                <div class="max-h-[80vh] overflow-y-auto">
                    <div class="flex justify-between items-start mb-4">
                        <h2 class="text-2xl font-bold text-gray-800">
                            Pedido #${pedido.id}
                        </h2>
                        <button data-modal-close class="text-gray-400 hover:text-gray-600">
                            <i class="fas fa-times text-2xl"></i>
                        </button>
                    </div>

                    <div class="space-y-4">
                        <!-- Status -->
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <span class="status-badge status-${pedido.status}">
                                ${Utils.translateStatus(pedido.status)}
                            </span>
                        </div>

                        <!-- Cliente -->
                        ${pedido.cliente ? `
                            <div>
                                <h3 class="font-semibold text-gray-700 mb-1">De (Remetente):</h3>
                                <p class="text-gray-800">${Utils.escapeHtml(pedido.cliente)}</p>
                            </div>
                        ` : ''}

                        <!-- Telefone -->
                        ${pedido.telefone_cliente ? `
                            <div>
                                <h3 class="font-semibold text-gray-700 mb-1">Telefone:</h3>
                                <p class="text-gray-800">${Utils.formatPhone(pedido.telefone_cliente)}</p>
                            </div>
                        ` : ''}

                        <!-- Destinatário -->
                        <div>
                            <h3 class="font-semibold text-gray-700 mb-1">Para (Destinatário):</h3>
                            <p class="text-gray-800 font-bold">${Utils.escapeHtml(pedido.destinatario)}</p>
                        </div>

                        <!-- Tipo -->
                        ${pedido.tipo_pedido ? `
                            <div>
                                <h3 class="font-semibold text-gray-700 mb-1">Tipo:</h3>
                                <p class="text-gray-800">${Utils.translateType(pedido.tipo_pedido)}</p>
                            </div>
                        ` : ''}

                        <!-- Produto -->
                        <div>
                            <h3 class="font-semibold text-gray-700 mb-1">Produto:</h3>
                            <p class="text-gray-800 whitespace-pre-wrap">${Utils.escapeHtml(pedido.produto)}</p>
                        </div>

                        <!-- Flores e Cor -->
                        ${pedido.flores_cor ? `
                            <div>
                                <h3 class="font-semibold text-gray-700 mb-1">Flores e Cor:</h3>
                                <p class="text-gray-800 whitespace-pre-wrap">${Utils.escapeHtml(pedido.flores_cor)}</p>
                            </div>
                        ` : ''}

                        <!-- Valor -->
                        ${pedido.valor ? `
                            <div>
                                <h3 class="font-semibold text-gray-700 mb-1">Valor:</h3>
                                <p class="text-gray-800 text-xl font-bold text-primary">${Utils.escapeHtml(pedido.valor)}</p>
                            </div>
                        ` : ''}

                        <!-- Data e Horário -->
                        <div class="bg-blue-50 p-4 rounded-lg">
                            <h3 class="font-semibold text-gray-700 mb-2">Entrega:</h3>
                            <p class="text-gray-800">
                                <i class="fas fa-calendar mr-2"></i>
                                ${Utils.formatDate(pedido.dia_entrega)}
                            </p>
                            <p class="text-gray-800">
                                <i class="fas fa-clock mr-2"></i>
                                ${pedido.horario}
                            </p>
                        </div>

                        <!-- Endereço -->
                        ${pedido.endereco ? `
                            <div>
                                <h3 class="font-semibold text-gray-700 mb-1">Endereço:</h3>
                                <p class="text-gray-800 whitespace-pre-wrap">${Utils.escapeHtml(pedido.endereco)}</p>
                            </div>
                        ` : ''}

                        <!-- Observações de Entrega -->
                        ${pedido.obs_entrega ? `
                            <div>
                                <h3 class="font-semibold text-gray-700 mb-1">Como Entregar:</h3>
                                <p class="text-gray-800 whitespace-pre-wrap">${Utils.escapeHtml(pedido.obs_entrega)}</p>
                            </div>
                        ` : ''}

                        <!-- Mensagem -->
                        ${pedido.mensagem ? `
                            <div class="bg-pink-50 p-4 rounded-lg">
                                <h3 class="font-semibold text-gray-700 mb-1">Carta/Mensagem:</h3>
                                <p class="text-gray-800 whitespace-pre-wrap italic">${Utils.escapeHtml(pedido.mensagem)}</p>
                            </div>
                        ` : ''}

                        <!-- Pagamento -->
                        ${pedido.pagamento ? `
                            <div>
                                <h3 class="font-semibold text-gray-700 mb-1">Forma de Pagamento:</h3>
                                <p class="text-gray-800">${Utils.escapeHtml(pedido.pagamento)}</p>
                            </div>
                        ` : ''}

                        <!-- Observações -->
                        ${pedido.observacoes ? `
                            <div>
                                <h3 class="font-semibold text-gray-700 mb-1">Observações Gerais:</h3>
                                <p class="text-gray-800 whitespace-pre-wrap">${Utils.escapeHtml(pedido.observacoes)}</p>
                            </div>
                        ` : ''}

                        <!-- Informações de Sistema -->
                        <div class="text-xs text-gray-500 pt-4 border-t">
                            <p>Criado em: ${pedido.created_at}</p>
                            ${pedido.updated_at ? `<p>Atualizado em: ${pedido.updated_at}</p>` : ''}
                        </div>
                    </div>
                </div>
            `;

            Modal.custom(modalContent);

        } catch (error) {
            console.error('Erro ao carregar detalhes:', error);
            Notification.error('Erro ao carregar detalhes do pedido');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * Calcula a taxa de entrega de um pedido individual
     */
    async calcularTaxa(pedidoId, forceRecalc = false) {
        try {
            // Encontrar o card e mostrar loading
            const card = document.querySelector(`.pedido-card[data-id="${pedidoId}"]`);
            if (card) {
                const taxaIcon = card.querySelector('.fa-dollar-sign, .fa-calculator, .fa-sync-alt');
                if (taxaIcon) {
                    taxaIcon.classList.add('fa-spin');
                }
            }

            console.log(`[DEBUG] Calculando taxa do pedido ${pedidoId}`);

            // Chamar API
            const result = await API.calcularTaxaEntrega(pedidoId);

            console.log('[DEBUG] Resultado taxa:', result);

            if (result.success) {
                const taxa = result.data.taxa_entrega;
                const distancia = result.data.distancia_km;

                // Atualizar pedido no painel se existir
                if (window.Painel && window.Painel.pedidos) {
                    const pedido = window.Painel.pedidos.find(p => p.id === pedidoId);
                    if (pedido) {
                        pedido.taxa_entrega = taxa;
                        pedido.distancia_km = distancia;
                        // Re-renderizar card
                        const cardElement = document.querySelector(`.pedido-card[data-id="${pedidoId}"]`);
                        if (cardElement) {
                            cardElement.outerHTML = PedidoCard.render(pedido);
                        }
                    }
                }

                const msg = `Taxa: R$ ${taxa.toFixed(2)}${distancia ? ` (${PedidoCard.formatarDistancia(distancia)})` : ''}`;
                Notification.success(msg);
            } else {
                throw new Error(result.error || 'Erro ao calcular taxa');
            }

        } catch (error) {
            console.error('Erro ao calcular taxa:', error);
            Notification.error(`Erro ao calcular taxa: ${error.message || 'Falha na requisição'}`);
        } finally {
            // Remover loading
            const card = document.querySelector(`.pedido-card[data-id="${pedidoId}"]`);
            if (card) {
                const taxaIcon = card.querySelector('.fa-dollar-sign, .fa-calculator, .fa-sync-alt');
                if (taxaIcon) {
                    taxaIcon.classList.remove('fa-spin');
                }
            }
        }
    },

    /**
     * Calcula a distância de um pedido individual
     */
    async calcularDistancia(pedidoId, forceRecalc = false) {
        try {
            // Encontrar o card e mostrar loading
            const card = document.querySelector(`.pedido-card[data-id="${pedidoId}"]`);
            if (card) {
                const routeIcon = card.querySelector('.fa-route, .fa-calculator, .fa-sync-alt');
                if (routeIcon) {
                    routeIcon.classList.add('fa-spin');
                }
            }

            console.log(`[DEBUG] Calculando distância do pedido ${pedidoId} (forceRecalc: ${forceRecalc})`);

            // Chamar API
            const url = `/api/pedidos/${pedidoId}/distancia${forceRecalc ? '?force_recalc=true' : ''}`;
            const response = await fetch(url);
            const result = await response.json();

            console.log('[DEBUG] Resultado:', result);

            if (result.success) {
                const distancia = result.distancia_km;
                const cached = result.cached;
                const aproximado = result.aproximado || false;
                const nivelAproximacao = result.nivel_aproximacao || 'exato';
                const aviso = result.aviso || null;

                // Atualizar o pedido no PainelManager se existir
                if (window.PainelManager && window.PainelManager.pedidos) {
                    const pedido = window.PainelManager.pedidos.find(p => p.id === pedidoId);
                    if (pedido) {
                        pedido.distancia_km = distancia;
                        pedido.aproximado = aproximado;
                        pedido.nivel_aproximacao = nivelAproximacao;
                        pedido.aviso = aviso;
                    }
                }

                // Re-renderizar o card
                if (window.PainelManager && typeof window.PainelManager.renderPedidos === 'function') {
                    window.PainelManager.renderPedidos();
                }

                // Mostrar notificação
                let msg = `Distância: ${PedidoCard.formatarDistancia(distancia)}${cached ? ' (cache)' : ''}`;
                if (aproximado) {
                    msg += ` ⚠️ (aproximada - ${nivelAproximacao})`;
                }
                if (result.coords_destino) {
                    console.log(`[DEBUG] Coordenadas destino: lon=${result.coords_destino[0]}, lat=${result.coords_destino[1]}`);
                }

                // Usar aviso amarelo se for aproximado, senão sucesso verde
                if (aproximado) {
                    Notification.warning(msg);
                } else {
                    Notification.success(msg);
                }
            } else {
                console.error('[ERRO] Falha ao calcular distância:', result.error);
                Notification.error(`Erro: ${result.error || 'Falha ao calcular distância'}`);
            }

        } catch (error) {
            console.error('[ERRO] Exceção ao calcular distância:', error);
            Notification.error('Erro ao calcular distância');
        }
    },

    /**
     * Imprime pedido em formato A4
     */
    async printPedido(pedidoId) {
        console.log(`[IMPRESSAO] Iniciando impressão do pedido ${pedidoId}`);
        try {
            Utils.showLoading();

            const result = await API.getPedido(pedidoId);
            console.log(`[IMPRESSAO] Resultado do getPedido:`, result);

            if (!result.success) {
                throw new Error(result.error || 'Erro ao carregar pedido');
            }

            const pedido = result.data.pedido;
            console.log(`[IMPRESSAO] Pedido carregado:`, { id: pedido.id, cliente: pedido.cliente, destinatario: pedido.destinatario });

            // HTML para impressão em A4
            const printHTML = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Pedido #${pedido.id} - Plante Uma Flor</title>
    <style>
        @page {
            size: A4;
            margin: 1cm;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Helvetica, Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #333;
        }
        
        .container {
            max-width: 100%;
            margin: 0 auto;
            max-height: 27cm;
            overflow: hidden;
        }
        
        .header {
            text-align: center;
            border-bottom: 2px solid #047857;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        
        .header h1 {
            color: #047857;
            font-size: 22pt;
            margin-bottom: 4px;
            font-weight: bold;
        }
        
        .header p {
            color: #6b7280;
            font-size: 10pt;
        }
        
        .pedido-numero {
            background: #047857;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            display: inline-block;
            font-weight: bold;
            font-size: 12pt;
            margin: 8px 0 6px 0;
            letter-spacing: 0.5px;
        }
        
        .section {
            margin-bottom: 12px;
            page-break-inside: avoid;
            text-align: center;
        }
        
        .section-title {
            background: #f3f4f6;
            padding: 6px 12px;
            border-left: 4px solid #047857;
            font-weight: bold;
            font-size: 12pt;
            margin-bottom: 8px;
            color: #047857;
            text-align: center;
        }
        
        .field {
            margin-bottom: 7px;
            line-height: 1.4;
            text-align: center;
        }
        
        .field-label {
            font-weight: bold;
            color: #374151;
            display: inline-block;
            min-width: 140px;
            font-size: 10pt;
            text-align: center;
        }
        
        .field-value {
            color: #1f2937;
            font-size: 10pt;
            line-height: 1.5;
            text-align: center;
        }
        
        .field-value.highlight {
            color: #047857;
            font-weight: bold;
            font-size: 12pt;
        }
        
        .message-box {
            background: #fef3c7;
            border: 2px solid #f59e0b;
            padding: 8px;
            border-radius: 6px;
            margin: 6px 0;
            font-style: italic;
            font-size: 9pt;
            max-height: 80px;
            overflow: hidden;
            color: #78350f;
            line-height: 1.4;
            text-align: center;
        }
        
        .delivery-box {
            background: #dbeafe;
            border: 2px solid #3b82f6;
            padding: 8px;
            border-radius: 6px;
            margin: 6px 0;
            text-align: center;
        }
        
        .footer {
            margin-top: 10px;
            padding-top: 6px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #666;
            font-size: 8pt;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-weight: bold;
            font-size: 9pt;
        }
        
        .status-agendado { background: #e5e7eb; color: #374151; }
        .status-em_producao { background: #fef3c7; color: #92400e; }
        .status-pronto_entrega, .status-pronto_retirada { background: #d1fae5; color: #065f46; }
        .status-em_rota { background: #dbeafe; color: #1e40af; }
        .status-concluido { background: #d1fae5; color: #166534; }
        
        .status-pagamento-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 15px;
            font-weight: bold;
            font-size: 10pt;
            margin: 8px 0;
            text-align: center;
        }
        
        .status-pagamento-realizado { background: #10b981; color: white; }
        .status-pagamento-50pago { background: #f59e0b; color: white; }
        .status-pagamento-pendente { background: #ef4444; color: white; }
        
        .produto-destaque {
            background: #f0fdf4;
            border: 2px solid #047857;
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0;
            font-size: 16pt;
            font-weight: bold;
            text-align: center;
            color: #047857;
        }
        
        /* Otimizações para garantir 1 página */
        .compact .field {
            margin-bottom: 4px;
        }
        
        .compact .section {
            margin-bottom: 10px;
        }
        
        .compact textarea-content {
            max-height: 60px;
            overflow: hidden;
            font-size: 9pt;
        }
        
        @media print {
            body {
                print-color-adjust: exact;
                -webkit-print-color-adjust: exact;
            }
            
            .no-print {
                display: none !important;
            }
            
            .container {
                page-break-after: avoid;
            }
            
            .section {
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Cabeçalho -->
        <div class="header">
            <h1>🌺 Plante Uma Flor</h1>
            <p>Sistema de Gestão de Pedidos</p>
            ${pedido.status_pagamento ? `
                <div style="margin: 12px 0;">
                    <span class="status-pagamento-badge status-pagamento-${pedido.status_pagamento === 'PAGAMENTO REALIZADO' ? 'realizado' : pedido.status_pagamento === '50% PAGO' ? '50pago' : 'pendente'}">
                        ${pedido.status_pagamento}
                    </span>
                </div>
            ` : ''}
        </div>

        <!-- Número do Pedido -->
        <div style="text-align: center;">
            <div class="pedido-numero">
                PEDIDO #${pedido.id}
            </div>
            <p style="margin-top: 6px;">
                <span class="status-badge status-${pedido.status}">
                    ${Utils.translateStatus(pedido.status).toUpperCase()}
                </span>
            </p>
        </div>

        <!-- Informações do Cliente -->
        <div class="section">
            <div class="section-title">👤 Informações do Cliente</div>
            ${pedido.cliente ? `
                <div class="field">
                    <span class="field-label">De (Remetente):</span>
                    <span class="field-value">${pedido.cliente}</span>
                </div>
            ` : ''}
            <div class="field">
                <span class="field-label">Telefone:</span>
                <span class="field-value">${Utils.formatPhone(pedido.telefone_cliente)}</span>
            </div>
            <div class="field">
                <span class="field-label">Para (Destinatário):</span>
                <span class="field-value highlight">${pedido.destinatario}</span>
            </div>
            <div class="field">
                <span class="field-label">Tipo de Pedido:</span>
                <span class="field-value">${Utils.translateType(pedido.tipo_pedido)}</span>
            </div>
            ${pedido.fonte_pedido ? `
                <div class="field">
                    <span class="field-label">Fonte do Pedido:</span>
                    <span class="field-value">${pedido.fonte_pedido}</span>
                </div>
            ` : ''}
        </div>

        <!-- Produto -->
        <div class="section">
            <div class="section-title">🌸 Produto</div>
            <div class="produto-destaque">
                ${pedido.produto}
            </div>
            ${pedido.flores_cor ? `
                <div class="field" style="background: #fef3c7; padding: 6px; border-radius: 4px; border: 1px solid #f59e0b; margin-top: 4px; text-align: center;">
                    <span class="field-label" style="color: #92400e; font-size: 9pt;">Flores e Cor:</span>
                    <div class="field-value" style="margin-top: 3px; white-space: pre-wrap; color: #78350f; font-weight: 500; font-size: 9pt;">${pedido.flores_cor}</div>
                </div>
            ` : ''}
            ${pedido.valor ? `
                <div class="field">
                    <span class="field-label">Valor:</span>
                    <span class="field-value" style="font-size: 12pt; color: #059669; font-weight: bold;">${pedido.valor}</span>
                </div>
            ` : ''}
        </div>

        <!-- Data e Horário -->
        <div class="section">
            <div class="delivery-box">
                <div style="font-weight: bold; font-size: 11pt; margin-bottom: 6px; color: #1e40af;">
                    📅 Entrega Agendada
                </div>
                <div class="field">
                    <span class="field-label" style="font-size: 9pt;">Data:</span>
                    <span class="field-value highlight" style="font-size: 10pt;">${Utils.formatDate(pedido.dia_entrega)}</span>
                </div>
                <div class="field">
                    <span class="field-label" style="font-size: 9pt;">Horário:</span>
                    <span class="field-value highlight" style="font-size: 10pt;">${pedido.horario}</span>
                </div>
            </div>
        </div>

        <!-- Endereço -->
        ${pedido.endereco ? `
            <div class="section">
                <div class="section-title">📍 Endereço de Entrega</div>
                <div class="field">
                    <div class="field-value" style="white-space: pre-wrap; font-size: 9pt; font-weight: 500;">${pedido.endereco}</div>
                </div>
                ${pedido.distancia_km !== null && pedido.distancia_km !== undefined ? `
                    <div class="field" style="margin-top: 6px;">
                        <span class="field-label" style="color: #1e40af; font-weight: bold;">Distância:</span>
                        <span class="field-value" style="color: #1e40af; font-weight: bold; font-size: 9pt;">
                            ${PedidoCard.formatarDistancia(pedido.distancia_km)}
                        </span>
                        ${pedido.taxa_entrega !== null && pedido.taxa_entrega !== undefined ? `
                            <span style="margin: 0 6px; color: #059669; font-weight: bold; font-size: 9pt;">
                                | Taxa: R$ ${pedido.taxa_entrega.toFixed(2)}
                            </span>
                        ` : ''}
                    </div>
                ` : ''}
                ${pedido.obs_entrega ? `
                    <div class="field" style="margin-top: 6px;">
                        <span class="field-label">Observações:</span>
                        <div class="field-value" style="margin-top: 3px; white-space: pre-wrap; font-size: 9pt;">${pedido.obs_entrega}</div>
                    </div>
                ` : ''}
            </div>
        ` : ''}

        <!-- Mensagem -->
        ${pedido.mensagem ? `
            <div class="section">
                <div class="section-title">💌 Carta/Mensagem</div>
                <div class="message-box">
                    ${pedido.mensagem.replace(/\n/g, '<br>')}
                </div>
            </div>
        ` : ''}

        <!-- Pagamento -->
        ${pedido.pagamento ? `
            <div class="section">
                <div class="section-title">💳 Pagamento</div>
                <div class="field">
                    <span class="field-label">Forma de Pagamento:</span>
                    <span class="field-value">${pedido.pagamento}</span>
                </div>
            </div>
        ` : ''}

        <!-- Observações Gerais -->
        ${pedido.observacoes ? `
            <div class="section">
                <div class="section-title">📝 Observações Gerais</div>
                <div class="field">
                    <div class="field-value" style="white-space: pre-wrap;">${pedido.observacoes}</div>
                </div>
            </div>
        ` : ''}

        <!-- Rodapé -->
        <div class="footer">
            <p>Impresso em: ${new Date().toLocaleString('pt-BR')}</p>
            <p style="margin-top: 5px;">Plante Uma Flor - Sistema de Gestão de Pedidos v3.0</p>
        </div>

        <!-- Botão de Impressão (esconde ao imprimir) -->
        <div class="no-print" style="text-align: center; margin-top: 30px;">
            <button onclick="window.print()" style="
                background: #047857;
                color: white;
                border: none;
                padding: 15px 40px;
                font-size: 14pt;
                border-radius: 8px;
                cursor: pointer;
                font-weight: bold;
            ">
                🖨️ Imprimir Pedido
            </button>
            <button onclick="window.close()" style="
                background: #6b7280;
                color: white;
                border: none;
                padding: 15px 40px;
                font-size: 14pt;
                border-radius: 8px;
                cursor: pointer;
                margin-left: 10px;
            ">
                ✕ Fechar
            </button>
        </div>
    </div>

    <script>
        // Auto-imprimir após carregar (opcional)
        // window.onload = () => window.print();
    </script>
</body>
</html>
            `;

            // Usar Blob URL para criar página separada (compatível com mobile e desktop)
            const blob = new Blob([printHTML], { type: 'text/html;charset=utf-8' });
            const url = URL.createObjectURL(blob);

            // Tentar abrir em nova aba (funciona em desktop)
            let printWindow = null;
            try {
                printWindow = window.open(url, '_blank');
            } catch (e) {
                console.log('[IMPRESSAO] window.open bloqueado, usando iframe');
            }

            if (printWindow) {
                // Desktop: aguardar carregar e imprimir
                printWindow.onload = () => {
                    setTimeout(() => {
                        printWindow.print();
                        // Limpar URL após impressão
                        setTimeout(() => {
                            URL.revokeObjectURL(url);
                            // Fechar janela após impressão (opcional)
                            // printWindow.close();
                        }, 1000);
                    }, 250);
                };
            } else {
                // Mobile: criar iframe oculto e imprimir
                const iframe = document.createElement('iframe');
                iframe.style.cssText = 'position: fixed; width: 0; height: 0; border: none; top: -9999px; left: -9999px;';
                iframe.src = url;
                document.body.appendChild(iframe);
                
                iframe.onload = () => {
                    setTimeout(() => {
                        try {
                            iframe.contentWindow.focus();
                            iframe.contentWindow.print();
                        } catch (e) {
                            console.error('[IMPRESSAO] Erro ao imprimir iframe:', e);
                            Notification.error('Erro ao abrir impressão. Tente novamente.');
                        }
                        
                        // Limpar após impressão
                        setTimeout(() => {
                            if (iframe.parentNode) {
                                document.body.removeChild(iframe);
                            }
                            URL.revokeObjectURL(url);
                        }, 2000);
                    }, 250);
                };
            }

            // Marcar pedido como impresso
            console.log(`[IMPRESSAO] Chamando API.marcarImpresso(${pedidoId})`);
            try {
                const result = await API.marcarImpresso(pedidoId);
                console.log(`[IMPRESSAO] Resposta da API:`, result);

                if (result.success) {
                    console.log(`[IMPRESSAO] Pedido ${pedidoId} marcado como impresso com sucesso`);
                } else {
                    console.warn(`[IMPRESSAO] Falha ao marcar como impresso:`, result.error);
                }

                // Atualizar o card se estiver no painel
                if (window.PainelManager) {
                    window.PainelManager.renderPedidos(true);
                }
            } catch (error) {
                console.error(`[IMPRESSAO] Erro ao marcar como impresso:`, error);
                // Não mostrar erro ao usuário, apenas log
            }

            Notification.success('Janela de impressão aberta!');

        } catch (error) {
            console.error(`[IMPRESSAO] Erro ao imprimir pedido ${pedidoId}:`, error);
            Notification.error('Erro ao gerar impressão do pedido');
        } finally {
            Utils.hideLoading();
        }
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
    }
};

