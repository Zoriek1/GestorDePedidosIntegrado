/**
 * Plante Uma Flor - PWA v3.0
 * Pedido Card Component - Card de pedido para o painel
 */

const PedidoCard = {
    /**
     * Cria HTML de um card de pedido
     */
    create(pedido) {
        const card = document.createElement('div');
        card.className = `pedido-card status-${pedido.status}`;
        card.dataset.id = pedido.id;
        card.dataset.status = pedido.status;

        // Verificar se o pedido está atrasado
        const isOverdue = this.isOverdue(pedido);
        const overdueClass = isOverdue ? 'text-red-600 font-bold' : '';

        card.innerHTML = `
            <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 mb-3">
                <div class="flex-1 min-w-0">
                    <h3 class="text-lg font-bold text-gray-800 truncate">
                        Pedido #${pedido.id}
                    </h3>
                    <p class="text-sm text-gray-600 break-words">
                        <i class="fas fa-calendar mr-1"></i>
                        ${Utils.formatDate(pedido.dia_entrega)} às ${pedido.horario}
                        ${isOverdue ? '<span class="text-red-600 ml-2 whitespace-nowrap"><i class="fas fa-exclamation-triangle"></i> Atrasado</span>' : ''}
                    </p>
                </div>
                <span class="status-badge status-${pedido.status} self-start sm:self-auto">
                    ${Utils.translateStatus(pedido.status)}
                </span>
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
                    <span class="break-words">${Utils.escapeHtml(Utils.truncate(pedido.produto, 60))}</span>
                </p>

                ${pedido.tipo_pedido ? `
                    <p class="text-sm break-words">
                        <i class="fas ${pedido.tipo_pedido === 'Entrega' ? 'fa-truck' : 'fa-store'} text-gray-400 w-5 inline-block"></i>
                        <span class="break-words">${Utils.translateType(pedido.tipo_pedido)}</span>
                    </p>
                ` : ''}

                ${pedido.endereco && pedido.tipo_pedido === 'Entrega' ? `
                    <p class="text-sm break-words">
                        <i class="fas fa-map-marker-alt text-gray-400 w-5 inline-block"></i>
                        <span class="break-words">${Utils.escapeHtml(Utils.truncate(pedido.endereco, 60))}</span>
                    </p>
                ` : ''}

                ${pedido.distancia_km !== null && pedido.distancia_km !== undefined ? `
                    <p class="text-sm">
                        <i class="fas fa-route text-${PedidoCard.getCorDistancia(pedido.distancia_km)}-500 w-5 inline-block"></i>
                        <span class="font-medium text-${PedidoCard.getCorDistancia(pedido.distancia_km)}-600">
                            ${PedidoCard.formatarDistancia(pedido.distancia_km)}
                        </span>
                        <span class="text-gray-400 text-xs ml-1">da floricultura</span>
                        <button 
                            class="ml-2 text-blue-500 hover:text-blue-700 text-xs"
                            onclick="PedidoCard.calcularDistancia(${pedido.id}, true)"
                            title="Recalcular distância"
                        >
                            <i class="fas fa-sync-alt"></i>
                        </button>
                    </p>
                ` : (pedido.tipo_pedido === 'Entrega' && pedido.endereco ? `
                    <p class="text-sm">
                        <i class="fas fa-route text-gray-400 w-5 inline-block"></i>
                        <button 
                            class="text-blue-500 hover:text-blue-700 text-xs font-medium"
                            onclick="PedidoCard.calcularDistancia(${pedido.id})"
                            title="Calcular distância"
                        >
                            <i class="fas fa-calculator mr-1"></i>Calcular distância
                        </button>
                    </p>
                ` : '')}

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
                        class="flex-1 sm:flex-none px-3 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition text-sm"
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

            // Carregar dados atuais do pedido
            const result = await API.getPedido(pedidoId);
            if (!result.success) {
                throw new Error(result.error || 'Erro ao carregar pedido');
            }

            const p = result.data.pedido;

            // Conteúdo do modal com formulário compacto
            const modalHtml = `
                <div class="max-h-[80vh] overflow-y-auto">
                    <div class="flex justify-between items-start mb-4">
                        <h2 class="text-2xl font-bold text-gray-800">
                            Editar Pedido #${p.id}
                        </h2>
                        <button data-modal-close class="text-gray-400 hover:text-gray-600">
                            <i class="fas fa-times text-2xl"></i>
                        </button>
                    </div>

                    <form id="form-editar-pedido" class="space-y-4">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">De (Remetente)</label>
                                <input id="edit-cliente" type="text" class="w-full border rounded px-3 py-2" value="${Utils.escapeHtml(p.cliente || '')}">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Telefone</label>
                                <input id="edit-telefone" type="text" class="w-full border rounded px-3 py-2" value="${Utils.escapeHtml(p.telefone_cliente || '')}">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Para (Destinatário)</label>
                                <input id="edit-destinatario" type="text" class="w-full border rounded px-3 py-2" value="${Utils.escapeHtml(p.destinatario || '')}">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                                <select id="edit-tipo" class="w-full border rounded px-3 py-2">
                                    <option value="Entrega" ${p.tipo_pedido === 'Entrega' ? 'selected' : ''}>Entrega</option>
                                    <option value="Retirada" ${p.tipo_pedido === 'Retirada' ? 'selected' : ''}>Retirada</option>
                                </select>
                            </div>
                        </div>

                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Produto</label>
                            <textarea id="edit-produto" class="w-full border rounded px-3 py-2" rows="3">${Utils.escapeHtml(p.produto || '')}</textarea>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Flores e Cor</label>
                                <input id="edit-flores" type="text" class="w-full border rounded px-3 py-2" value="${Utils.escapeHtml(p.flores_cor || '')}">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Valor</label>
                                <input id="edit-valor" type="text" class="w-full border rounded px-3 py-2" value="${Utils.escapeHtml(p.valor || '')}">
                            </div>
                            <div class="grid grid-cols-2 gap-3">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Dia</label>
                                    <input id="edit-dia" type="date" class="w-full border rounded px-3 py-2" value="${Utils.escapeHtml(p.dia_entrega || '')}">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Horário</label>
                                    <input id="edit-horario" type="time" class="w-full border rounded px-3 py-2" value="${Utils.escapeHtml(p.horario || '')}">
                                </div>
                            </div>
                        </div>

                        <!-- Campos de Endereço Separados -->
                        <div class="border rounded-lg p-3 bg-gray-50">
                            <h3 class="text-sm font-semibold text-gray-700 mb-3">📍 Endereço de Entrega</h3>
                            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                                <div>
                                    <label class="block text-xs font-medium text-gray-600 mb-1">CEP</label>
                                    <input id="edit-cep" type="text" class="w-full border rounded px-2 py-1.5 text-sm" value="${Utils.escapeHtml(p.cep || '')}" placeholder="00000-000">
                                </div>
                                <div class="col-span-2">
                                    <label class="block text-xs font-medium text-gray-600 mb-1">Rua</label>
                                    <input id="edit-rua" type="text" class="w-full border rounded px-2 py-1.5 text-sm" value="${Utils.escapeHtml(p.rua || '')}" placeholder="Nome da rua">
                                </div>
                                <div>
                                    <label class="block text-xs font-medium text-gray-600 mb-1">Número</label>
                                    <input id="edit-numero" type="text" class="w-full border rounded px-2 py-1.5 text-sm" value="${Utils.escapeHtml(p.numero || '')}" placeholder="123">
                                </div>
                            </div>
                            <div class="grid grid-cols-2 gap-3 mb-3">
                                <div>
                                    <label class="block text-xs font-medium text-gray-600 mb-1">Bairro</label>
                                    <input id="edit-bairro" type="text" class="w-full border rounded px-2 py-1.5 text-sm" value="${Utils.escapeHtml(p.bairro || '')}" placeholder="Bairro">
                                </div>
                                <div>
                                    <label class="block text-xs font-medium text-gray-600 mb-1">Cidade</label>
                                    <input id="edit-cidade" type="text" class="w-full border rounded px-2 py-1.5 text-sm" value="${Utils.escapeHtml(p.cidade || 'Goiânia')}" placeholder="Cidade">
                                </div>
                            </div>
                            <div>
                                <label class="block text-xs font-medium text-gray-600 mb-1">Endereço Completo (gerado automaticamente)</label>
                                <textarea id="edit-endereco" class="w-full border rounded px-2 py-1.5 text-sm bg-white" rows="2" placeholder="Será preenchido automaticamente ou edite manualmente">${Utils.escapeHtml(p.endereco || '')}</textarea>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Como Entregar / Observações</label>
                                <textarea id="edit-obs_entrega" class="w-full border rounded px-3 py-2" rows="2">${Utils.escapeHtml(p.obs_entrega || '')}</textarea>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Carta/Mensagem</label>
                                <textarea id="edit-mensagem" class="w-full border rounded px-3 py-2" rows="2">${Utils.escapeHtml(p.mensagem || '')}</textarea>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Pagamento</label>
                                <input id="edit-pagamento" type="text" class="w-full border rounded px-3 py-2" value="${Utils.escapeHtml(p.pagamento || '')}">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Observações Gerais</label>
                                <textarea id="edit-observacoes" class="w-full border rounded px-3 py-2" rows="2">${Utils.escapeHtml(p.observacoes || '')}</textarea>
                            </div>
                        </div>

                        <div class="flex justify-end gap-3 pt-4 border-t">
                            <button type="button" class="btn btn-secondary" data-modal-close>Cancelar</button>
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-save mr-2"></i>Salvar
                            </button>
                        </div>
                    </form>
                </div>
            `;

            const overlay = Modal.custom(modalHtml);

            // Listener de submit
            const form = overlay.querySelector('#form-editar-pedido');
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                try {
                    Utils.showLoading();

                    // Coletar dados (incluindo campos de endereço separados)
                    const data = {
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
                        observacoes: overlay.querySelector('#edit-observacoes').value.trim()
                    };

                    const update = await API.updatePedido(pedidoId, data);
                    if (!update.success) {
                        throw new Error(update.error || 'Erro ao atualizar pedido');
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
                    console.error('Erro ao salvar edição:', err);
                    Notification.error(`Erro ao salvar: ${err.message}`);
                } finally {
                    Utils.hideLoading();
                }
            });

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
                                <p class="text-gray-800 text-xl font-bold text-green-600">${Utils.escapeHtml(pedido.valor)}</p>
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
                
                // Atualizar o pedido no PainelManager se existir
                if (window.PainelManager && window.PainelManager.pedidos) {
                    const pedido = window.PainelManager.pedidos.find(p => p.id === pedidoId);
                    if (pedido) {
                        pedido.distancia_km = distancia;
                    }
                }
                
                // Re-renderizar o card
                if (window.PainelManager && typeof window.PainelManager.renderPedidos === 'function') {
                    window.PainelManager.renderPedidos();
                }
                
                // Mostrar notificação
                const msg = `Distância: ${PedidoCard.formatarDistancia(distancia)}${cached ? ' (cache)' : ''}`;
                if (result.coords_destino) {
                    console.log(`[DEBUG] Coordenadas destino: lon=${result.coords_destino[0]}, lat=${result.coords_destino[1]}`);
                }
                Notification.success(msg);
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
        try {
            Utils.showLoading();
            
            const result = await API.getPedido(pedidoId);
            
            if (!result.success) {
                throw new Error(result.error || 'Erro ao carregar pedido');
            }

            const pedido = result.data.pedido;

            // Criar janela de impressão
            const printWindow = window.open('', '_blank', 'width=800,height=600');
            
            if (!printWindow) {
                Notification.error('Popup bloqueado! Permita popups para imprimir.');
                return;
            }

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
            margin: 1.5cm;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, sans-serif;
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
            border-bottom: 2px solid #9333ea;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        
        .header h1 {
            color: #9333ea;
            font-size: 20pt;
            margin-bottom: 3px;
        }
        
        .header p {
            color: #666;
            font-size: 9pt;
        }
        
        .pedido-numero {
            background: #9333ea;
            color: white;
            padding: 6px 15px;
            border-radius: 6px;
            display: inline-block;
            font-weight: bold;
            font-size: 13pt;
            margin: 10px 0 8px 0;
        }
        
        .section {
            margin-bottom: 12px;
            page-break-inside: avoid;
        }
        
        .section-title {
            background: #f3f4f6;
            padding: 5px 10px;
            border-left: 3px solid #9333ea;
            font-weight: bold;
            font-size: 11pt;
            margin-bottom: 6px;
        }
        
        .field {
            margin-bottom: 6px;
            padding-left: 8px;
            line-height: 1.3;
        }
        
        .field-label {
            font-weight: bold;
            color: #555;
            display: inline-block;
            min-width: 130px;
            font-size: 9.5pt;
        }
        
        .field-value {
            color: #333;
            font-size: 9.5pt;
        }
        
        .field-value.highlight {
            color: #9333ea;
            font-weight: bold;
            font-size: 11pt;
        }
        
        .message-box {
            background: #fef3c7;
            border: 1.5px solid #f59e0b;
            padding: 10px;
            border-radius: 6px;
            margin: 8px 0;
            font-style: italic;
            font-size: 9pt;
            max-height: 80px;
            overflow: hidden;
        }
        
        .delivery-box {
            background: #dbeafe;
            border: 1.5px solid #3b82f6;
            padding: 10px;
            border-radius: 6px;
            margin: 8px 0;
        }
        
        .footer {
            margin-top: 15px;
            padding-top: 10px;
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
        </div>

        <!-- Número do Pedido -->
        <div style="text-align: center;">
            <div class="pedido-numero">
                PEDIDO #${pedido.id}
            </div>
            <p style="margin-top: 10px;">
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
        </div>

        <!-- Produto -->
        <div class="section">
            <div class="section-title">🌸 Produto</div>
            <div class="field">
                <span class="field-label">Produto:</span>
                <div class="field-value" style="margin-top: 5px; white-space: pre-wrap;">${pedido.produto}</div>
            </div>
            ${pedido.flores_cor ? `
                <div class="field">
                    <span class="field-label">Flores e Cor:</span>
                    <div class="field-value" style="margin-top: 5px; white-space: pre-wrap;">${pedido.flores_cor}</div>
                </div>
            ` : ''}
            ${pedido.valor ? `
                <div class="field">
                    <span class="field-label">Valor:</span>
                    <span class="field-value" style="font-size: 16pt; color: #059669; font-weight: bold;">${pedido.valor}</span>
                </div>
            ` : ''}
        </div>

        <!-- Data e Horário -->
        <div class="section">
            <div class="delivery-box">
                <div style="font-weight: bold; font-size: 14pt; margin-bottom: 10px;">
                    📅 Entrega Agendada
                </div>
                <div class="field">
                    <span class="field-label">Data:</span>
                    <span class="field-value highlight">${Utils.formatDate(pedido.dia_entrega)}</span>
                </div>
                <div class="field">
                    <span class="field-label">Horário:</span>
                    <span class="field-value highlight">${pedido.horario}</span>
                </div>
            </div>
        </div>

        <!-- Endereço -->
        ${pedido.endereco ? `
            <div class="section">
                <div class="section-title">📍 Endereço de Entrega</div>
                <div class="field">
                    <div class="field-value" style="white-space: pre-wrap;">${pedido.endereco}</div>
                </div>
                ${pedido.obs_entrega ? `
                    <div class="field" style="margin-top: 10px;">
                        <span class="field-label">Observações:</span>
                        <div class="field-value" style="margin-top: 5px; white-space: pre-wrap;">${pedido.obs_entrega}</div>
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
                background: #9333ea;
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

            printWindow.document.write(printHTML);
            printWindow.document.close();

            Notification.success('Janela de impressão aberta!');

        } catch (error) {
            console.error('Erro ao imprimir pedido:', error);
            Notification.error('Erro ao gerar impressão do pedido');
        } finally {
            Utils.hideLoading();
        }
    }
};

